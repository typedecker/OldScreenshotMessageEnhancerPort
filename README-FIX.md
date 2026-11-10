# Fabric 26.3 GitHub Actions workflow correction

This overlay fixes the two build-configuration problems shown by the failed 26.3 workflow.

## Apply

1. Extract this ZIP at the root of `OldScreenshotMessageEnhancerPort`.
2. Merge the `.github` and `tools` folders into the repository, replacing `.github/workflows/build-lean-26-3.yml` and adding `tools/isolate_26_3_build.py`.
3. Commit and push, or manually run **Actions → Build Screenshot Message Enhancer - lean Fabric 26.3**.

## What it changes

- Runs the existing `tools/port_26_3.py` unchanged, preserving its 26.3 source preparation, lean dependency changes, and Kotlin runtime handling.
- In the GitHub Actions checkout only, rewrites the Stonecutter project list to register **only** `26.3-fabric`. The 1.8.9 Forge, 1.8.9 Ornithe, 26.1 Fabric, and 26.2 Fabric projects remain in the repository but are not part of this CI build's Gradle project graph.
- Changes the Gradle wrapper URL to **Gradle 9.8.0** in the temporary Actions checkout, matching the minimum required by Fabric Loom 1.19.3. It does not change the wrapper committed in the repository.
- Builds `:26.3-fabric:build` and collects the JAR only from `versions/26.3-fabric/build/libs/`.

The workflow still uses Java 25 and retains Kotlin because the mod has Kotlin source files. It does not add OneConfig or Mod Menu back.

## Scope and verification

This addresses the concrete CI configuration failure: Gradle 9.7.1 is too old for Loom 1.19.3, and registering all Stonecutter versions makes Gradle configure unrelated legacy targets. It does not establish that all Minecraft 26.3 source/API or mixin changes compile; the next Actions run will test that. Any subsequent failure should be assessed from its first actual 26.3 compile or remapping error.
