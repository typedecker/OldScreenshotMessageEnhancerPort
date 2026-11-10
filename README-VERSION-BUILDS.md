# Reusable lean Fabric version builder

This adds a manually triggered GitHub Actions workflow that can prepare and build a lean Fabric version from a Minecraft version input.

## Install once

1. Extract this ZIP at the root of `OldScreenshotMessageEnhancerPort`.
2. Merge the `.github` and `tools` folders into the repository. Keep the existing `build-lean-26-3.yml` workflow; this adds a separate reusable workflow.
3. Add `README-VERSION-BUILDS.md` to the repository root.
4. Commit and push the files to the repository's default branch.

## Build a version

1. Open the repository's **Actions** tab.
2. Select **Build Screenshot Message Enhancer - lean Fabric version**.
3. Click **Run workflow**.
4. Enter the target Minecraft version, such as `26.4`, then click **Run workflow**.
5. Leave the Fabric API and Fabric Loader override fields blank for automatic lookup. Download the resulting JAR from the workflow run's Artifacts section.

The default Minecraft input is `26.3`, the known-good version from the current port. Use it once as a smoke test of the new reusable workflow before relying on it for a later release.

## What it does

- Copies the repository's `versions/26.2-fabric` template into a temporary target named `versions/<minecraft-version>-fabric`.
- Automatically selects the latest stable Fabric Loader returned by Fabric Meta for that Minecraft version.
- Automatically selects the newest Fabric API release whose Maven version is suffixed with that exact Minecraft version. You can override either selection in the workflow inputs.
- Applies the same lean-port changes used by the successful 26.3 build: removes OneConfig and Mod Menu build/runtime metadata, replaces the OneConfig settings screen with the JSON-backed settings file, and embeds Kotlin stdlib.
- Keeps Java 25, Fabric Loom 1.19.3, and Gradle 9.8.0 as the known-working defaults. These are exposed as workflow inputs so they can be overridden without editing any repository files if a future Minecraft release requires a newer toolchain.
- Temporarily rewrites Stonecutter settings so Gradle registers only the requested Fabric target. The Forge, Ornithe, and other Fabric versions remain untouched in the repository and are not configured for this job.
- Builds only `:<minecraft-version>-fabric:build` and uploads only that target's non-sources JAR.

## Important boundaries

- The workflow is manual-only. Adding it does not start a build on every push.
- The generated target and the temporary edits are made in the GitHub Actions checkout. They are not automatically committed back to the repository; the uploaded JAR is the output.
- The base template remains `versions/26.2-fabric`, because the successful 26.3 target is generated in CI rather than stored as a committed source directory.
- This automates repetitive version and build setup, not Minecraft source compatibility. If a later release changes a Minecraft method, mapping, or mixin target, the build can still need a source-code adjustment. In that case, fix the actual compiler/mixin error and rerun the same workflow.
- If the selected Loom version requires a newer Gradle, use the `Fabric Loom version` and `Gradle version` workflow inputs. The Gradle version must satisfy the selected Loom release.

## Configuration inputs

| Input | Default | Purpose |
|---|---:|---|
| Minecraft version | `26.3` | Target version and project name |
| Fabric API version | automatic | Optional exact Fabric API version override |
| Fabric Loader version | automatic | Optional exact Fabric Loader version override |
| Java version | `25` | Java toolchain and bytecode target |
| Fabric Loom version | `1.19.3` | Fabric Gradle plugin version |
| Gradle version | `9.8.0` | Gradle wrapper distribution used in CI |
