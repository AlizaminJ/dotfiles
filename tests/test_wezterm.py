"""Check terminal settings and fail-closed macOS signature verification."""

import os
from pathlib import Path
import shutil
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

    @unittest.skipUnless(os.environ.get("WEZTERM_TEST_BINARY"), "Set WEZTERM_TEST_BINARY for native CLI validation")
    def test_native_cli_has_only_clipboard_shortcuts(self):
        env = dict(self.env, XDG_CONFIG_HOME=str(self.home / ".config"),
                   XDG_CACHE_HOME=str(self.home / ".cache"), XDG_DATA_HOME=str(self.home / ".local/share"))
        result = subprocess.run(
            [os.environ["WEZTERM_TEST_BINARY"], "--config-file", str(REPO / "wezterm/wezterm.lua"), "show-keys", "--lua"],
            env=env, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        main_keys = result.stdout.split("key_tables", 1)[0]
        self.assertEqual(main_keys.count("{ key ="), 2, main_keys)
        for action in ["SpawnTab", "SplitVertical", "SplitHorizontal", "ActivateTab"]:
            self.assertNotIn(action, result.stdout)
        self.assertIn("CopyTo", main_keys)
        self.assertIn("PasteFrom", main_keys)

    @unittest.skipUnless(shutil.which("luajit"), "LuaJIT unavailable")
    def test_macos_lua_config_with_local_override(self):
        runner = self.home / "check.lua"
        runner.write_text('''package.preload.wezterm = function()
  return {
    target_triple = arg[1], home_dir = arg[3],
    font = function(name) return name end,
    action = {
      CopyTo = function(target) return { copy = target } end,
      PasteFrom = function(target) return { paste = target } end,
    },
  }
end
local config = assert(loadfile(arg[2]))()
assert(config.enable_tab_bar == false)
assert(config.disable_default_key_bindings == true)
assert(#config.keys == 2)
assert(config.default_prog[1] == '/bin/zsh')
assert(config.default_prog[2] == '-l')
assert(config.keys[1].mods == 'CMD')
assert(config.font_size == tonumber(arg[4]))
''')
        for triple in ["aarch64-apple-darwin", "x86_64-apple-darwin"]:
            subprocess.run(["luajit", str(runner), triple, str(REPO / "wezterm/wezterm.lua"), str(self.home), "13"], check=True)
        (self.home / ".wezterm.local.lua").write_text("return { font_size = 15 }\n")
        subprocess.run(["luajit", str(runner), "aarch64-apple-darwin", str(REPO / "wezterm/wezterm.lua"), str(self.home), "15"], check=True)


if __name__ == "__main__":
    unittest.main()
