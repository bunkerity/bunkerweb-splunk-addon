"""Exercise the real shell wait against an API that answers before bootstrap finishes."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class SplunkReadiness(unittest.TestCase):
    def wait(self, *, never_healthy=False, api_ready=True):
        with tempfile.TemporaryDirectory() as tmp:
            return subprocess.run(
                [
                    "bash",
                    "-c",
                    """
set -euo pipefail
. tests/lib.sh
seq() { printf '1\n2\n'; }
sleep() { touch "$SPLTA_TEST_READY"; }
docker() {
  [ "$1" = inspect ] || return 2
  if [ "$SPLTA_TEST_NEVER_HEALTHY" = 0 ] && [ -f "$SPLTA_TEST_READY" ]; then
    echo healthy
  else
    echo starting
  fi
}
sp_curl() {
  [ "$SPLTA_TEST_API_READY" = 1 ] || return 7
  echo '{"version":"10.2.9"}'
}
sp_wait
# An early API reply alone must never let the caller install or restart Splunk.
if [ -f "$SPLTA_TEST_READY" ]; then echo ready; else echo early; fi
""",
                ],
                cwd=ROOT,
                env={
                    **os.environ,
                    "SPLTA_TEST_READY": str(Path(tmp) / "bootstrap-finished"),
                    "SPLTA_TEST_NEVER_HEALTHY": str(int(never_healthy)),
                    "SPLTA_TEST_API_READY": str(int(api_ready)),
                },
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

    def test_waits_for_bootstrap_even_when_api_answers(self):
        result = self.wait()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "ready\n")

    def test_rejects_api_ready_container_that_never_becomes_healthy(self):
        result = self.wait(never_healthy=True)
        self.assertNotEqual(result.returncode, 0)

    def test_requires_authenticated_api_too(self):
        result = self.wait(api_ready=False)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
