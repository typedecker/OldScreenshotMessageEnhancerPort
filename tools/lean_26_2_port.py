#!/usr/bin/env python3
# Applies a minimal-dependency Fabric 26.2 port to the current
# TomekoYT/ScreenshotMessageEnhancer tree.
#
# It removes OneConfig and Mod Menu, removes the Mod Menu entrypoint,
# and replaces the OneConfig-backed settings object with a Gson JSON store.

from __future__ import annotations

from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]

BUILD = ROOT / "build.gradle.kts"
MOD_JSON = ROOT / "versions/26.2-fabric/src/main/resources/fabric.mod.json"
CONFIG = ROOT / "src/main/kotlin/tomeko/screenshotmessageenhancer/config/ScreenshotMessageEnhancerConfig.kt"
MODMENU = ROOT / "src/main/kotlin/tomeko/screenshotmessageenhancer/config/ModMenuIntegration.kt"
COMMAND = ROOT / "src/main/kotlin/tomeko/screenshotmessageenhancer/commands/ScreenshotMessageEnhancerCommand.kt"

required = [BUILD, MOD_JSON, CONFIG, COMMAND]
missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
if missing:
    raise SystemExit("Missing expected files: " + ", ".join(missing))

text = BUILD.read_text(encoding="utf-8")

# The source is Kotlin. Embed stdlib so removing OneConfig does not
# accidentally remove the runtime that Kotlin bytecode needs.
if 'include(implementation(kotlin("stdlib"))!!)' not in text:
    marker = 'dependencies {\n'
    text = text.replace(
        marker,
        marker + '    include(implementation(kotlin("stdlib"))!!)\n',
        1,
    )

text = re.sub(
    r'^\s*implementation\("org\.polyfrost\.oneconfig:\$minecraftVersion-fabric:\$oneconfigVersion"\)\s*\n?',
    "",
    text,
    flags=re.M,
)
text = re.sub(
    r'^\s*implementation\("com\.terraformersmc:modmenu:\$modMenuVersion"\)\s*\n?',
    "",
    text,
    flags=re.M,
)
BUILD.write_text(text, encoding="utf-8")

data = json.loads(MOD_JSON.read_text(encoding="utf-8"))
data.get("entrypoints", {}).pop("modmenu", None)
data.get("depends", {}).pop("oneconfig", None)
data.pop("suggests", None)
data.pop("custom", None)
MOD_JSON.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

command = COMMAND.read_text(encoding="utf-8")
command = re.sub(
    r'^\s*import org\.polyfrost\.oneconfig\.utils\.v1\.dsl\.openUI\s*\n?',
    "",
    command,
    flags=re.M,
)
COMMAND.write_text(command, encoding="utf-8")

if MODMENU.exists():
    MODMENU.unlink()

config_source = """package tomeko.screenshotmessageenhancer.config

import com.google.gson.GsonBuilder
import com.google.gson.JsonObject
import net.minecraft.client.Minecraft
import tomeko.screenshotmessageenhancer.utils.Constants
import java.io.File

/**
 * Dependency-free settings storage for the lean build.
 * Configuration lives in <minecraft>/config/screenshotmessageenhancer.json.
 */
object ScreenshotMessageEnhancerConfig {
    private val gson = GsonBuilder().setPrettyPrinting().create()

    private val file: File
        get() = File(
            Minecraft.getInstance().gameDirectory,
            "config/${Constants.MOD_ID}.json"
        )

    var showName: Boolean = false
    var showCopyButton: Boolean = true
    var showOpenButton: Boolean = true
    var showOpenFolderButton: Boolean = true
    var showDeleteButton: Boolean = true
    var showUploadButton: Boolean = true
    var autoCopyScreenshot: Boolean = false
    var compressScreenshots: Boolean = true
    var debugModeEnabled: Boolean = false

    fun register() {
        load()
        save()
    }

    // Kept so the existing command still compiles. Settings are edited in JSON.
    fun openUI() {
    }

    private fun load() {
        if (!file.isFile) return

        try {
            file.reader(Charsets.UTF_8).use { reader ->
                val obj = gson.fromJson(reader, JsonObject::class.java) ?: return
                showName = boolean(obj, "showName", showName)
                showCopyButton = boolean(obj, "showCopyButton", showCopyButton)
                showOpenButton = boolean(obj, "showOpenButton", showOpenButton)
                showOpenFolderButton = boolean(obj, "showOpenFolderButton", showOpenFolderButton)
                showDeleteButton = boolean(obj, "showDeleteButton", showDeleteButton)
                showUploadButton = boolean(obj, "showUploadButton", showUploadButton)
                autoCopyScreenshot = boolean(obj, "autoCopyScreenshot", autoCopyScreenshot)
                compressScreenshots = boolean(obj, "compressScreenshots", compressScreenshots)
                debugModeEnabled = boolean(obj, "debugModeEnabled", debugModeEnabled)
            }
        } catch (_: Exception) {
            // Keep defaults and repair the file below.
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

        file.writer(Charsets.UTF_8).use { writer ->
            gson.toJson(obj, writer)
        }
    }

    private fun boolean(obj: JsonObject, name: String, fallback: Boolean): Boolean {
        return try {
            if (obj.has(name) && !obj.get(name).isJsonNull) obj.get(name).asBoolean
            else fallback
        } catch (_: Exception) {
            fallback
        }
    }
}
"""
CONFIG.write_text(config_source, encoding="utf-8")

print("Applied lean Fabric 26.2 transformation.")
