"""Self-check for release_check.py: python3 -I -m unittest discover -s .github/scripts"""

import json
import tempfile
import unittest
from pathlib import Path

import release_check

CONF = "[launcher]\nversion = {conf}\n\n[id]\nversion = {conf}\n"
CHANGELOG = "# Changelog\n\n## {heading}\n\n{body}\n\n## v0.9.0 - 2026/01/01\n\n- old\n"


def tree(root: Path, conf="1.0.0", manifest="1.0.0", heading="v1.0.0 - 2026/11/10", body="- first release") -> None:
    (root / "TA-bunkerweb" / "default").mkdir(parents=True)
    (root / "TA-bunkerweb" / "default" / "app.conf").write_text(CONF.format(conf=conf))
    (root / "TA-bunkerweb" / "app.manifest").write_text(json.dumps({"info": {"id": {"version": manifest}}}))
    (root / "CHANGELOG.md").write_text(CHANGELOG.format(heading=heading, body=body))


class ReleaseCheck(unittest.TestCase):
    def run_check(self, tag="v1.0.0", **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            tree(Path(tmp), **kwargs)
            return release_check.check(Path(tmp), tag)

    def test_matching_release(self):
        self.assertEqual(self.run_check(), ("1.0.0", "- first release", False))

    def test_prerelease_tag(self):
        self.assertEqual(self.run_check("v1.0.0-rc1", conf="1.0.0-rc1", manifest="1.0.0-rc1", heading="v1.0.0-rc1 - 2026/11/10")[2], True)

    def test_rejects_disabled_splunkbase_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tree(root)
            with (root / "TA-bunkerweb" / "default" / "app.conf").open("a") as conf:
                conf.write("\n[package]\ncheck_for_updates = false\n")
            with self.assertRaisesRegex(ValueError, "check_for_updates"):
                release_check.check(root, "v1.0.0")

    def test_rejections(self):
        for kwargs in (
            {"tag": "v1.0.1"},  # tag differs from the add-on version
            {"tag": "1.0.0"},  # not a v tag
            {"manifest": "0.9.0"},  # app.manifest differs from app.conf
            {"heading": "v1.0.0 - ????/??/??"},  # unreleased placeholder date
            {"heading": "v0.9.0 - 2026/01/01"},  # top changelog section is another version
            {"body": ""},  # empty section
        ):
            with self.subTest(kwargs), self.assertRaises(ValueError):
                self.run_check(**kwargs)


if __name__ == "__main__":
    unittest.main()
