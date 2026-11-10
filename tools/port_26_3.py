#!/usr/bin/env python3
"""Prepare a lean Minecraft 26.3 Fabric target in the Stonecutter project.

The script runs on a clean GitHub Actions checkout, creates versions/26.3-fabric
from the existing 26.2 target when needed, updates the Stonecutter target list,
removes the OneConfig/Mod Menu build dependencies, and replaces the shared
OneConfig configuration object with a small JSON-backed settings store.

Only :26.3-fabric:build is invoked by the associated workflow. Legacy Forge and
Ornithe source trees are not compiled by that workflow.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_VERSION = ROOT / "versions/26.2-fabric"
TARGET_VERSION = ROOT / "versions/26.3-fabric"
BUILD = ROOT / "build.gradle.kts"
SETTINGS = ROOT / "settings.gradle.kts"
STONECUTTER = ROOT / "stonecutter.gradle.kts"
CONFIG = ROOT / "src/main/kotlin/tomeko/screenshotmessageenhancer/config/ScreenshotMessageEnhancerConfig.kt"
MODMENU = ROOT / "src/main/kotlin/tomeko/screenshotmessageenhancer/config/ModMenuIntegration.kt"
COMMAND = ROOT / "src/main/kotlin/tomeko/screenshotmessageenhancer/commands/ScreenshotMessageEnhancerCommand.kt"

for path in (SOURCE_VERSION, BUILD, SETTINGS, STONECUTTER, CONFIG, COMMAND):
    if not path.exists():
        raise SystemExit(f"Missing expected repository file/directory: {path.relative_to(ROOT)}")

# 1) Create the new version source/resources from the 26.2 target. If a partial
# 26.3 target already exists, copy only missing files so local target-specific
# edits are not overwritten.
if not TARGET_VERSION.exists():
    shutil.copytree(SOURCE_VERSION, TARGET_VERSION)
else:
    for src in SOURCE_VERSION.rglob("*"):
        rel = src.relative_to(SOURCE_VERSION)
        dst = TARGET_VERSION / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        elif not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

# Update values in the newly copied version properties, preserving any other
# properties and their order.
props_path = TARGET_VERSION / "gradle.properties"
if not props_path.exists():
    raise SystemExit("Expected versions/26.3-fabric/gradle.properties after copying 26.2 target")
props = props_path.read_text(encoding="utf-8")
for key, value in {
    "java_version": "25",
    "minecraft_version": "26.3",
    # Valid 26.3 version listed by Fabric's official developer page when this
    # patch was prepared. Update this line later if Fabric publishes a newer one.
    "fabric_api_version": "0.162.0+26.3",
}.items():
    pat = rf"(?m)^{re.escape(key)}=.*$"
    if re.search(pat, props):
        props = re.sub(pat, f"{key}={value}", props)
    else:
        props += f"\n{key}={value}\n"
props_path.write_text(props, encoding="utf-8")

# 2) Register the 26.3 target in Stonecutter settings.
settings_text = SETTINGS.read_text(encoding="utf-8")
if 'version("26.3-fabric", "26.3")' not in settings_text:
    marker = 'version("26.2-fabric", "26.2")'
    if marker not in settings_text:
        raise SystemExit('Could not find version("26.2-fabric", "26.2") in settings.gradle.kts')
    settings_text = settings_text.replace(marker, marker + '\n        version("26.3-fabric", "26.3")', 1)
settings_text = settings_text.replace('vcsVersion = "26.2-fabric"', 'vcsVersion = "26.3-fabric"')
SETTINGS.write_text(settings_text, encoding="utf-8")

stonecutter_text = STONECUTTER.read_text(encoding="utf-8")
stonecutter_text = re.sub(
    r'(?m)^\s*stonecutter active "26\.2-fabric"\s*$',
    'stonecutter active "26.3-fabric"',
    stonecutter_text,
)
STONECUTTER.write_text(stonecutter_text, encoding="utf-8")

# 3) Update Fabric Loom to the latest stable 1.19.3 line for this target. The
# wrapper is already Gradle 9.7.1, matching the modern Loom requirement.
build_text = BUILD.read_text(encoding="utf-8")
build_text, loom_matches = re.subn(
    r'(id\("net\.fabricmc\.fabric-loom"\)\s+version\s+")[^"]+("?)',
    r'\g<1>1.19.3\2',
    build_text,
    count=1,
)
if loom_matches != 1:
    raise SystemExit('Could not update the net.fabricmc.fabric-loom plugin version in build.gradle.kts')

# Remove OneConfig and Mod Menu from the actual runtime dependency block.
build_text = re.sub(
    r'(?m)^\s*implementation\("org\.polyfrost\.oneconfig:[^\"]+"\)\s*\n?',
    "",
    build_text,
)
build_text = re.sub(
    r'(?m)^\s*implementation\("com\.terraformersmc:modmenu:[^\"]+"\)\s*\n?',
    "",
    build_text,
)
# Kotlin source still needs Kotlin's runtime; nest it in the produced mod jar.
if 'include(implementation(kotlin("stdlib"))!!)' not in build_text:
    marker = "dependencies {\n"
    if marker not in build_text:
        raise SystemExit("Could not find dependencies block in build.gradle.kts")
    build_text = build_text.replace(
        marker,
        marker + '    include(implementation(kotlin("stdlib"))!!)\n',
        1,
    )
BUILD.write_text(build_text, encoding="utf-8")

# 4) Remove Mod Menu integration and dependency metadata from the 26.3 target.
mod_json_path = TARGET_VERSION / "src/main/resources/fabric.mod.json"
if not mod_json_path.exists():
    raise SystemExit("Missing target fabric.mod.json")
mod_json = json.loads(mod_json_path.read_text(encoding="utf-8"))
mod_json.get("entrypoints", {}).pop("modmenu", None)
mod_json.get("depends", {}).pop("oneconfig", None)
mod_json.pop("suggests", None)
custom = mod_json.get("custom")
if isinstance(custom, dict):
    custom.pop("modmenu", None)
    if not custom:
        mod_json.pop("custom", None)
mod_json_path.write_text(json.dumps(mod_json, indent=2) + "\n", encoding="utf-8")

if MODMENU.exists():
    MODMENU.unlink()

# This source import brings OneConfig back into the modern command compilation.
command_text = COMMAND.read_text(encoding="utf-8")
command_text = re.sub(
    r'(?m)^\s*import\s+org\.polyfrost\.oneconfig\.[^\n]+\n',
    "",
    command_text,
)
COMMAND.write_text(command_text, encoding="utf-8")

# The older OneConfig config is replaced by ordinary JSON storage. The settings
# used by the feature keep their current names/defaults, so the feature code
# needs no wholesale rewrite. The /config command remains harmless but no GUI
# is opened; settings are edited in config/screenshotmessageenhancer.json.
CONFIG.write_text('''package tomeko.screenshotmessageenhancer.config

import com.google.gson.GsonBuilder
import com.google.gson.JsonObject
import net.minecraft.client.Minecraft
import tomeko.screenshotmessageenhancer.utils.Constants
import java.io.File

/**
 * Small JSON-backed settings store for the lean 26.3 build.
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
''', encoding="utf-8")

print("Prepared lean 26.3 Fabric target.")
print("Target: versions/26.3-fabric")
print("Build command: ./gradlew --no-daemon :26.3-fabric:build")
