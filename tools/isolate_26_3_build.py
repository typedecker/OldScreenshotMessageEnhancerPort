#!/usr/bin/env python3
"""Limit the CI build to the 26.3 Stonecutter target and Gradle 9.8.0."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / 'settings.gradle.kts'
WRAPPER = ROOT / 'gradle/wrapper/gradle-wrapper.properties'

for path in (SETTINGS, WRAPPER) :
    if not path.is_file() :
        raise SystemExit(f'Missing expected file: {path.relative_to(ROOT)}')

# Keep only the 26.3 target registered for this temporary CI build.
settings_text = SETTINGS.read_text(encoding = 'utf-8')
start_marker = 'stonecutter {'
end_marker = '\ndependencyResolutionManagement {'
if settings_text.count(start_marker) != 1 :
    raise SystemExit('Expected exactly one Stonecutter configuration block in settings.gradle.kts')
start = settings_text.index(start_marker)
end = settings_text.find(end_marker, start)
if end == -1 :
    raise SystemExit('Could not find dependencyResolutionManagement after the Stonecutter block')

stonecutter_block = '''stonecutter {
    create(rootProject) {
        version("26.3-fabric", "26.3")
        vcsVersion = "26.3-fabric"
    }
}
'''
settings_text = settings_text[:start] + stonecutter_block + settings_text[end + 1:]
SETTINGS.write_text(settings_text, encoding = 'utf-8')

# Loom 1.19.3 requires Gradle 9.8.0. Change the wrapper only in this CI checkout;
# the repository's normal wrapper remains untouched on the user's machine.
wrapper_text = WRAPPER.read_text(encoding = 'utf-8')
wrapper_text, matches = re.subn(
    r'(?m)^distributionUrl=.*$',
    lambda _: r'distributionUrl=https\://services.gradle.org/distributions/gradle-9.8.0-bin.zip',
    wrapper_text,
)
if matches != 1 :
    raise SystemExit('Could not find exactly one distributionUrl in gradle-wrapper.properties')
WRAPPER.write_text(wrapper_text, encoding = 'utf-8')

print('Stonecutter CI target: 26.3-fabric only')
print('Gradle wrapper for this CI run: 9.8.0')
