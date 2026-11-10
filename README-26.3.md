# Lean Fabric 26.3 port

This is an overlay for the `typedecker/OldScreenshotMessageEnhancerPort` repository. It adds a dedicated 26.3 target and a GitHub Actions build that only compiles that target.

## Install the overlay

1. Download and extract this bundle.
2. Copy its `.github` and `tools` folders into the root of your `OldScreenshotMessageEnhancerPort` repository, merging `.github` if it already exists. Copy `README-26.3.md` to the repository root too.
3. Commit and push the files.
4. Open **Actions → Build Screenshot Message Enhancer - lean Fabric 26.3**. If it did not run automatically, select **Run workflow**.
5. Once the run succeeds, download the `screenshot-message-enhancer-lean-26.3` artifact and put its jar in your Fabric 26.3 `mods` folder.

## What the action changes in its temporary runner

- Creates `versions/26.3-fabric` based on `versions/26.2-fabric` if missing.
- Registers the new Stonecutter target and makes it active for the build.
- Uses Java 25, Gradle wrapper 9.7.1 already in the repository, Loom 1.19.3, and Fabric API `0.162.0+26.3`.
- Removes OneConfig and Mod Menu from the 26.3 target/runtime metadata.
- Replaces the OneConfig GUI settings with `config/screenshotmessageenhancer.json` and embeds Kotlin stdlib.
- Invokes only `:26.3-fabric:build`; it does not compile the old 1.8.9 Forge or Ornithe targets.

The script runs in the GitHub Actions checkout, so the generated target and temporary source edits are not automatically committed back to your repository. The downloadable artifact is the build output.

## Limitations

I have not run this build against GitHub Actions from here, so the jar is not verified yet. If the build fails, inspect the first Kotlin compiler error or mixin error in the 26.3 job log; that will identify any 26.3-specific API change that still needs a source edit. The old configuration screen is intentionally removed; edit the JSON config file instead.
