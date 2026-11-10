#!/usr/bin/env python3
"""Check that a release tag, the add-on version and the changelog agree, and write the release notes.

Usage: release_check.py <tag> [--root DIR] [--notes FILE]
Prints version=, tag=, prerelease= and package= lines (appended to $GITHUB_OUTPUT by the workflow).
Exits non-zero, with the reason on stderr, when any of these differ:
  - TA-bunkerweb/default/app.conf [launcher] version and [id] version
  - TA-bunkerweb/app.manifest info.id.version
  - the tag (vX.Y.Z or vX.Y.Z-rcN)
  - the first CHANGELOG.md section: "## vX.Y.Z - YYYY/MM/DD" (not "????/??/??"), with a non-empty body
"""

import argparse
import configparser
import json
import re
import sys
from pathlib import Path

APP = "TA-bunkerweb"
TAG_RE = re.compile(r"^v\d+\.\d+\.\d+(-(?:alpha|beta|rc)\.?\d+)?$")


def app_versions(root: Path) -> dict[str, str]:
    conf = configparser.ConfigParser(interpolation=None)
    conf.read(root / APP / "default" / "app.conf", encoding="utf-8")
    manifest = json.loads((root / APP / "app.manifest").read_text(encoding="utf-8"))
    return {
        "app.conf [launcher] version": conf.get("launcher", "version"),
        "app.conf [id] version": conf.get("id", "version"),
        "app.manifest info.id.version": manifest["info"]["id"]["version"],
    }


def changelog_section(text: str, tag: str) -> str:
    """Return the body of the first changelog section, which must belong to the tag and carry a real date."""
    sections = list(re.finditer(r"^## (.+)$", text, re.MULTILINE))
    if not sections:
        raise ValueError("CHANGELOG.md has no '## ' section")
    first = sections[0]
    if not re.fullmatch(rf"{re.escape(tag)} - \d{{4}}/\d{{2}}/\d{{2}}", first.group(1)):
        raise ValueError(f"The top CHANGELOG.md section is {first.group(0)!r}, expected '## {tag} - YYYY/MM/DD'")
    end = sections[1].start() if len(sections) > 1 else len(text)
    body = text[first.end() : end].strip()
    if not body:
        raise ValueError(f"The CHANGELOG.md section for {tag} is empty")
    return body


def check(root: Path, tag: str) -> tuple[str, str, bool]:
    tag_match = TAG_RE.match(tag)
    if tag_match is None:
        raise ValueError(f"Tag {tag!r} is not a version tag (vX.Y.Z)")
    versions = app_versions(root)
    if len(set(versions.values())) != 1:
        raise ValueError(f"Version fields disagree: {versions}")
    version = next(iter(versions.values()))
    if tag != f"v{version}":
        raise ValueError(f"Tag {tag!r} does not match the add-on version {version!r}")
    body = changelog_section((root / "CHANGELOG.md").read_text(encoding="utf-8"), tag)
    return version, body, tag_match.group(1) is not None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tag")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--notes", type=Path, default=Path("release-notes.md"))
    args = parser.parse_args()
    try:
        version, body, prerelease = check(args.root, args.tag)
    except (ValueError, KeyError, configparser.Error, OSError) as exc:
        print(f"release check failed: {exc}", file=sys.stderr)
        return 1
    args.notes.write_text(f"## BunkerWeb add-on for Splunk {version}\n\n### Changes\n\n{body}\n\n", encoding="utf-8")
    print(f"version={version}\ntag={args.tag}\nprerelease={str(prerelease).lower()}\npackage={APP}-{version}.tgz")
    return 0


if __name__ == "__main__":
    sys.exit(main())
