"""Check terminal settings and fail-closed macOS signature verification."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class WezTermTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.app = self.home / "WezTerm.app"
        self.app.mkdir()
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.mock("uname", "echo Darwin\n")
        self.mock("codesign", '''[[ "$*" == *'P4A6FU9KZ3'* ]] || exit 2
exit "${SIGNATURE_EXIT:-0}"
''')
        self.mock("spctl", '''if [[ "${GATEKEEPER_REJECT:-0}" == 1 ]]; then exit 1; fi
if [[ "${NOTARIZED:-1}" == 1 ]]; then
  echo 'source=Notarized Developer ID' >&2
else
  echo 'source=User Override' >&2
fi
''')
        self.env = dict(os.environ, HOME=str(self.home), PATH=str(self.bin) + os.pathsep + os.environ["PATH"])

    def mock(self, name, content):
        target = self.bin / name
        target.write_text("#!/bin/bash\nset -eu\n" + content)
        target.chmod(0o755)

    def verify(self, **env):
        return subprocess.run(
            ["bash", str(REPO / "scripts/verify-wezterm.sh"), str(self.app)],
            env=dict(self.env, **env), capture_output=True, text=True,
        )

    def test_valid_signature_and_notarization_pass(self):
        for _ in range(2):
            result = self.verify()
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(self.app.iterdir()), [])

    def test_signature_gatekeeper_and_user_override_fail_closed(self):
        for env in [{"SIGNATURE_EXIT": "1"}, {"GATEKEEPER_REJECT": "1"}, {"NOTARIZED": "0"}]:
            with self.subTest(env=env):
                self.assertNotEqual(self.verify(**env).returncode, 0)


if __name__ == "__main__":
    unittest.main()
