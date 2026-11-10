#!/usr/bin/env python3
"""Prepare and isolate a lean Fabric target for a selected Minecraft version."""
from __future__ import annotations

import json
import os
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_VERSION = '26.2-fabric'
BASE_DIR = ROOT / 'versions' / BASE_VERSION
BUILD = ROOT / 'build.gradle.kts'
SETTINGS = ROOT / 'settings.gradle.kts'
STONECUTTER = ROOT / 'stonecutter.gradle.kts'
WRAPPER = ROOT / 'gradle/wrapper/gradle-wrapper.properties'
CONFIG = ROOT / 'src/main/kotlin/tomeko/screenshotmessageenhancer/config/ScreenshotMessageEnhancerConfig.kt'
MODMENU = ROOT / 'src/main/kotlin/tomeko/screenshotmessageenhancer/config/ModMenuIntegration.kt'
COMMAND = ROOT / 'src/main/kotlin/tomeko/screenshotmessageenhancer/commands/ScreenshotMessageEnhancerCommand.kt'
FABRIC_API_METADATA = 'https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/maven-metadata.xml'
FABRIC_LOADER_METADATA = 'https://meta.fabricmc.net/v2/versions/loader/{minecraft_version}'
USER_AGENT = 'OldScreenshotMessageEnhancerPort-version-builder/1.0'


def required_env(name: str, default: str | None = None) -> str :
    value = os.environ.get(name, default)
    if value is None or not value.strip() :
        raise SystemExit(f'Missing required environment variable: {name}')
    return value.strip()


def fetch_url(url: str) -> bytes :
    request = urllib.request.Request(url, headers = {'User-Agent': USER_AGENT})
    try :
        with urllib.request.urlopen(request, timeout = 30) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError) as error :
        raise SystemExit(f'Could not retrieve Fabric metadata from {url}: {error}') from error


def detect_fabric_loader(minecraft_version: str) -> str :
    url = FABRIC_LOADER_METADATA.format(minecraft_version = urllib.parse.quote(minecraft_version, safe = ''))
    try :
        entries = json.loads(fetch_url(url).decode('utf-8'))
    except json.JSONDecodeError as error :
        raise SystemExit(f'Fabric Loader metadata for Minecraft {minecraft_version} was not valid JSON') from error
    for entry in entries :
        loader = entry.get('loader', {})
        if loader.get('stable') is True and loader.get('version') :
            return str(loader['version'])
    raise SystemExit(
        f'Fabric Meta did not report a stable Loader for Minecraft {minecraft_version}. '
        'Enter a Fabric Loader version manually in the workflow inputs.'
    )


def detect_fabric_api(minecraft_version: str) -> str :
    try :
        metadata = ET.fromstring(fetch_url(FABRIC_API_METADATA))
    except ET.ParseError as error :
        raise SystemExit('Fabric API Maven metadata was not valid XML') from error

    versions = []
    for element in metadata.iter() :
        if element.tag.rsplit('}', 1)[-1] != 'version' or not element.text :
            continue
        candidate = element.text.strip()
        if not candidate.endswith(f'+{minecraft_version}') :
            continue
        core = candidate.split('+', 1)[0]
        pieces = core.split('.')
        if pieces and all(piece.isdigit() for piece in pieces) :
            versions.append((tuple(int(piece) for piece in pieces), candidate))

    if not versions :
        raise SystemExit(
            f'No Fabric API release matching Minecraft {minecraft_version} was found. '
            'Enter a compatible Fabric API version manually in the workflow inputs.'
        )
    return max(versions, key = lambda item: item[0])[1]


def set_property(text: str, key: str, value: str) -> str :
    pattern = rf'(?m)^{re.escape(key)}=.*$'
    replacement = f'{key}={value}'
    if re.search(pattern, text) :
        return re.sub(pattern, lambda _: replacement, text, count = 1)
    if text and not text.endswith('\n') :
        text += '\n'
    return text + replacement + '\n'


def replace_single(pattern: str, replacement, text: str, description: str) -> str :
    updated, count = re.subn(pattern, replacement, text, count = 1, flags = re.MULTILINE)
    if count != 1 :
        raise SystemExit(f'Could not update {description}; expected exactly one matching declaration')
    return updated


def isolate_stonecutter(settings_text: str, target_project: str, minecraft_version: str) -> str :
    start_marker = 'stonecutter {'
    end_marker = '\ndependencyResolutionManagement {'
    if settings_text.count(start_marker) != 1 :
        raise SystemExit('Expected exactly one Stonecutter configuration block in settings.gradle.kts')
    start = settings_text.index(start_marker)
    end = settings_text.find(end_marker, start)
    if end == -1 :
        raise SystemExit('Could not find dependencyResolutionManagement after the Stonecutter block')

    block = (
        'stonecutter {\n'
        '    create(rootProject) {\n'
        f'        version("{target_project}", "{minecraft_version}")\n'
        f'        vcsVersion = "{target_project}"\n'
        '    }\n'
        '}\n'
    )
    return settings_text[:start] + block + settings_text[end + 1:]


def copy_target(base_dir: Path, target_dir: Path) -> None :
    if not base_dir.is_dir() :
        raise SystemExit(f'Missing base Fabric target: {base_dir.relative_to(ROOT)}')
    if not target_dir.exists() :
        shutil.copytree(base_dir, target_dir)
        return
    for source in base_dir.rglob('*') :
        relative = source.relative_to(base_dir)
        destination = target_dir / relative
        if source.is_dir() :
            destination.mkdir(parents = True, exist_ok = True)
        elif not destination.exists() :
            destination.parent.mkdir(parents = True, exist_ok = True)
            shutil.copy2(source, destination)


def main() -> None :
    minecraft_version = required_env('MINECRAFT_VERSION')
    if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', minecraft_version) :
        raise SystemExit('Minecraft version must be a stable numeric version such as 26.3 or 26.4.1')

    java_version = required_env('JAVA_VERSION', '25')
    loom_version = required_env('LOOM_VERSION', '1.19.3')
    gradle_version = required_env('GRADLE_VERSION', '9.8.0')
    fabric_api_version = os.environ.get('FABRIC_API_VERSION', '').strip()
    fabric_loader_version = os.environ.get('FABRIC_LOADER_VERSION', '').strip()
    target_project = f'{minecraft_version}-fabric'
    target_dir = ROOT / 'versions' / target_project

    missing = [path for path in (BUILD, SETTINGS, STONECUTTER, WRAPPER, CONFIG, COMMAND) if not path.is_file()]
    if missing :
        relative = ', '.join(str(path.relative_to(ROOT)) for path in missing)
        raise SystemExit(f'Missing required repository files: {relative}')

    if not fabric_api_version :
        print(f'Detecting Fabric API for Minecraft {minecraft_version}...')
        fabric_api_version = detect_fabric_api(minecraft_version)
    if not fabric_loader_version :
        print(f'Detecting Fabric Loader for Minecraft {minecraft_version}...')
        fabric_loader_version = detect_fabric_loader(minecraft_version)

    print(f'Minecraft: {minecraft_version}')
    print(f'Fabric API: {fabric_api_version}')
    print(f'Fabric Loader: {fabric_loader_version}')
    print(f'Java: {java_version}')
    print(f'Fabric Loom: {loom_version}')
    print(f'Gradle: {gradle_version}')

    copy_target(BASE_DIR, target_dir)

    props_path = target_dir / 'gradle.properties'
    if not props_path.is_file() :
        raise SystemExit(f'Missing {props_path.relative_to(ROOT)} after copying the base target')
    props = props_path.read_text(encoding = 'utf-8')
    for key, value in {
        'java_version': java_version,
        'minecraft_version': minecraft_version,
        'fabric_api_version': fabric_api_version,
        'fabric_loader_version': fabric_loader_version,
    }.items() :
        props = set_property(props, key, value)
    props_path.write_text(props, encoding = 'utf-8')

    settings_text = SETTINGS.read_text(encoding = 'utf-8')
    SETTINGS.write_text(isolate_stonecutter(settings_text, target_project, minecraft_version), encoding = 'utf-8')

    stonecutter_text = STONECUTTER.read_text(encoding = 'utf-8')
    stonecutter_text = replace_single(
        r'^\s*stonecutter active "[^"]+"\s*$',
        f'stonecutter active "{target_project}"',
        stonecutter_text,
        'the active Stonecutter version',
    )
    STONECUTTER.write_text(stonecutter_text, encoding = 'utf-8')

    build_text = BUILD.read_text(encoding = 'utf-8')
    build_text = replace_single(
        r'(id\("net\.fabricmc\.fabric-loom"\)\s+version\s+")[^"]+("?)',
        lambda match: match.group(1) + loom_version + match.group(2),
        build_text,
        'the Fabric Loom plugin version',
    )
    build_text = re.sub(
        r'(?m)^\s*implementation\("org\.polyfrost\.oneconfig:[^\"]+"\)\s*\n?',
        '',
        build_text,
    )
    build_text = re.sub(
        r'(?m)^\s*implementation\("com\.terraformersmc:modmenu:[^\"]+"\)\s*\n?',
        '',
        build_text,
    )
    if 'include(implementation(kotlin("stdlib"))!!)' not in build_text :
        marker = 'dependencies {\n'
        if marker not in build_text :
            raise SystemExit('Could not find dependencies block in build.gradle.kts')
        build_text = build_text.replace(
            marker,
            marker + '    include(implementation(kotlin("stdlib"))!!)\n',
            1,
        )
    BUILD.write_text(build_text, encoding = 'utf-8')

    wrapper_text = WRAPPER.read_text(encoding = 'utf-8')
    wrapper_text = replace_single(
        r'^distributionUrl=.*$',
        lambda _: f'distributionUrl=https\\://services.gradle.org/distributions/gradle-{gradle_version}-bin.zip',
        wrapper_text,
        'the Gradle wrapper distribution URL',
    )
    WRAPPER.write_text(wrapper_text, encoding = 'utf-8')

    mod_json_path = target_dir / 'src/main/resources/fabric.mod.json'
    if not mod_json_path.is_file() :
        raise SystemExit(f'Missing {mod_json_path.relative_to(ROOT)}')
    mod_json = json.loads(mod_json_path.read_text(encoding = 'utf-8'))
    mod_json.get('entrypoints', {}).pop('modmenu', None)
    mod_json.get('depends', {}).pop('oneconfig', None)
    mod_json.pop('suggests', None)
    custom = mod_json.get('custom')
    if isinstance(custom, dict) :
        custom.pop('modmenu', None)
        if not custom :
            mod_json.pop('custom', None)
    mod_json_path.write_text(json.dumps(mod_json, indent = 2) + '\n', encoding = 'utf-8')

    if MODMENU.exists() :
        MODMENU.unlink()
    command_text = COMMAND.read_text(encoding = 'utf-8')
    command_text = re.sub(r'(?m)^\s*import\s+org\.polyfrost\.oneconfig\.[^\n]+\n', '', command_text)
    COMMAND.write_text(command_text, encoding = 'utf-8')

    CONFIG.write_text('''package tomeko.screenshotmessageenhancer.config
import com.google.gson.GsonBuilder
import com.google.gson.JsonObject
import net.minecraft.client.Minecraft
import tomeko.screenshotmessageenhancer.utils.Constants
import java.io.File

/**
 * Small JSON-backed settings store for the lean Fabric build.
 * Edit <minecraft>/config/screenshotmessageenhancer.json to change options.
 */
object ScreenshotMessageEnhancerConfig {
    private val gson = GsonBuilder().setPrettyPrinting().create()
    private val file: File
        get() = File(
            Minecraft.getInstance().gameDirectory,
            "config/${Constants.MOD_ID}.json"
        )

    var showName = false
    var showCopyButton = true
    var showOpenButton = true
    var showOpenFolderButton = true
    var showDeleteButton = true
    var showUploadButton = true
    var autoCopyScreenshot = false
    var compressScreenshots = true
    var debugModeEnabled = false

    fun register() {
        load()
        save()
    }

    // Kept for the existing command callback; the optional GUI was removed.
    fun openUI() {
    }

    private fun load() {
        if (!file.isFile) return
        try {
            file.reader(Charsets.UTF_8).use { reader ->
                val obj = gson.fromJson(reader, JsonObject::class.java) ?: return
                showName = bool(obj, "showName", showName)
                showCopyButton = bool(obj, "showCopyButton", showCopyButton)
                showOpenButton = bool(obj, "showOpenButton", showOpenButton)
                showOpenFolderButton = bool(obj, "showOpenFolderButton", showOpenFolderButton)
                showDeleteButton = bool(obj, "showDeleteButton", showDeleteButton)
                showUploadButton = bool(obj, "showUploadButton", showUploadButton)
                autoCopyScreenshot = bool(obj, "autoCopyScreenshot", autoCopyScreenshot)
                compressScreenshots = bool(obj, "compressScreenshots", compressScreenshots)
                debugModeEnabled = bool(obj, "debugModeEnabled", debugModeEnabled)
            }
        } catch (_: Exception) {
            // Keep defaults if a config file is malformed.
        }
    }

    private fun save() {
        file.parentFile?.mkdirs()
        val obj = JsonObject().apply {
            addProperty("showName", showName)
            addProperty("showCopyButton", showCopyButton)
            addProperty("showOpenButton", showOpenButton)
            addProperty("showOpenFolderButton", showOpenFolderButton)
            addProperty("showDeleteButton", showDeleteButton)
            addProperty("showUploadButton", showUploadButton)
            addProperty("autoCopyScreenshot", autoCopyScreenshot)
            addProperty("compressScreenshots", compressScreenshots)
            addProperty("debugModeEnabled", debugModeEnabled)
        }
        file.writer(Charsets.UTF_8).use { writer -> gson.toJson(obj, writer) }
    }

    private fun bool(obj: JsonObject, name: String, fallback: Boolean): Boolean {
        return try {
            if (obj.has(name) && !obj.get(name).isJsonNull) obj.get(name).asBoolean else fallback
        } catch (_: Exception) {
            fallback
        }
    }
}
''', encoding = 'utf-8')

    print(f'Prepared isolated lean Fabric target: {target_project}')
    print(f'Build command: ./gradlew --no-daemon :{target_project}:build')


if __name__ == '__main__' :
    main()
