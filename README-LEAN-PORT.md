# Screenshot Message Enhancer — lean 26.2 port

This package contains a reproducible GitHub Actions workflow and transformation script for `TomekoYT/ScreenshotMessageEnhancer`.

## What it changes

The current 26.2 repository source declares OneConfig and Mod Menu. The lean port removes both from the runtime dependency graph and replaces the OneConfig-backed settings object with a small JSON config:

`<minecraft>/config/screenshotmessageenhancer.json`

The existing screenshot commands, screenshot manager, upload feature, and core mixins are otherwise left alone.

The intended external runtime dependency target is Fabric Loader + Fabric API; Kotlin stdlib is embedded in the mod JAR.

## How to use

1. Put the included files into a fork of `TomekoYT/ScreenshotMessageEnhancer`.
2. Commit and push them.
3. Open GitHub → Actions → `Build Screenshot Message Enhancer - lean Fabric 26.2`.
4. Run the workflow.
5. Download the `screenshot-message-enhancer-lean-26.2` artifact.
6. Put the resulting mod JAR into the Fabric 26.2 `mods` folder.

The workflow uses Java 25, matching the repository's 26.2 source target.

## Important limitation

I could inspect the repository and build metadata, but this runtime cannot reach GitHub/Maven to perform a clean Gradle build itself. Therefore I am not presenting an unverified JAR as tested.

For a future Minecraft release, update the Stonecutter target/version-specific Fabric API first, then rerun the same dependency-pruning process and fix only actual source/API breakages.
