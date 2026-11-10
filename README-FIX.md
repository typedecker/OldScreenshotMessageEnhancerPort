# Fix for the lean Fabric 26.3 workflow

Copy the `.github` directory from this overlay into the root of `OldScreenshotMessageEnhancerPort`, merging the directory and replacing:

`.github/workflows/build-lean-26-3.yml`

Then commit and push the changed workflow, or manually run **Build Screenshot Message Enhancer - lean Fabric 26.3** from the Actions tab.

What this fixes:

- Removes the failing step that searched for `org.jetbrains.kotlin.plugin.compose`. That plugin is not declared in the current root `build.gradle.kts`, so the step always failed with `matches == 0`.
- Keeps the Kotlin JVM plugin and Kotlin runtime. The mod still contains Kotlin source, and `tools/port_26_3.py` deliberately bundles Kotlin stdlib into the jar.
- Installs Java 8 and Java 25, then registers `JAVA_HOME_8_X64` with Gradle. This is needed because Gradle configures the legacy Forge subproject while configuring the requested 26.3 task, and that old project asks for a Java 8 toolchain.

This overlay changes only the GitHub Actions workflow. It does not claim the 26.3 source has compiled successfully; the next Actions run is the verification.
