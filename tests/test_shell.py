"""Exercise shell links and startup without touching the user's shell or network."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class ShellTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.env = dict(
            os.environ, HOME=str(self.home), ZDOTDIR=str(self.home), REPO_ROOT=str(REPO),
            XDG_CONFIG_HOME=str(self.home / ".config"), XDG_CACHE_HOME=str(self.home / ".cache"),
            XDG_DATA_HOME=str(self.home / ".local/share"),
            DOTFILES_DISABLE_FZF="1", DOTFILES_DISABLE_STARSHIP="1", DOTFILES_DISABLE_ZOXIDE="1",
        )
        self.env.pop("DOTFILES_SHELL_LOADED", None)

    def setup_shell(self):
        subprocess.run(["bash", str(REPO / "scripts/shell.sh")], env=self.env, check=True, capture_output=True)

    def test_links_backups_and_repeat_run_preserve_private_settings(self):
        (self.home / ".zshrc").write_text("# old framework config\n")
        (self.home / ".zshrc.bak").write_text("# older backup\n")
        private = {name: "# keep local\n" for name in [".zprofile", ".zshenv", ".zshrc.local", ".wezterm.local.lua"]}
        (self.home / ".wezterm.lua").write_text("-- old terminal config\n")
        for name, content in private.items():
            (self.home / name).write_text(content)
        self.setup_shell()
        self.setup_shell()
        self.assertEqual((self.home / ".zshrc.bak.1").read_text(), "# old framework config\n")
        self.assertEqual((self.home / ".zshrc.bak").read_text(), "# older backup\n")
        self.assertFalse((self.home / ".zshrc.bak.2").exists())
        self.assertEqual((self.home / ".zshrc").resolve(), REPO / "shell/zshrc")
        self.assertEqual((self.home / ".wezterm.lua").resolve(), REPO / "wezterm/wezterm.lua")
        self.assertEqual((self.home / ".wezterm.lua.bak").read_text(), "-- old terminal config\n")
        self.assertFalse((self.home / ".wezterm.lua.bak.1").exists())
        for name, content in private.items():
            self.assertEqual((self.home / name).read_text(), content)

    @unittest.skipUnless(shutil.which("zsh"), "zsh unavailable")
    def test_startup_loads_local_settings_and_prepared_cache_without_framework(self):
        self.setup_shell()
        (self.home / ".zshrc.local").write_text("export TEST_LOCAL_SETTING=preserved\n")
        cache = self.home / ".cache/dotfiles/plugins.zsh"
        cache.parent.mkdir(parents=True)
        cache.write_text("typeset -g TEST_PLUGIN_LOADED=1\n")
        checksum = subprocess.check_output(["cksum"], input=(REPO / "shell/plugins.txt").read_bytes())
        cache.with_suffix(".zsh.manifest").write_bytes(checksum)
        result = subprocess.run([
            "zsh", "-d", "-i", "-c",
            '[[ "$TEST_LOCAL_SETTING" == preserved && "$TEST_PLUGIN_LOADED" == 1 && "$EDITOR" == nvim ]] && '
            '(( $+functions[compdef] )) && command -v tat >/dev/null && command -v dotfiles >/dev/null && '
            '[[ -z ${ZSH:-} && "$HISTSIZE" == 50000 && "$SAVEHIST" == 50000 ]]',
        ], env=dict(self.env, EDITOR="", ZSH=""), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("zsh"), "zsh unavailable")
    def test_stale_cache_is_not_executed_and_startup_does_not_fetch(self):
        self.setup_shell()
        cache = self.home / ".cache/dotfiles/plugins.zsh"
        cache.parent.mkdir(parents=True)
        cache.write_text('touch "$HOME/should-not-exist"\n')
        cache.with_suffix(".zsh.manifest").write_text("stale\n")
        result = subprocess.run(["zsh", "-d", "-i", "-c", "true"], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.home / "should-not-exist").exists())
        self.assertIn("pins changed", result.stderr)

    @unittest.skipUnless(shutil.which("zsh"), "zsh unavailable")
    def test_plugin_preparation_is_repeatable_and_rejects_dirty_trees(self):
        manager = self.home / "antidote.zsh"
        manager.write_text('''antidote() {
  case "$1" in
    --version) print 'antidote version 2.3.0' ;;
    bundle) cat >/dev/null; print '# prepared test plugins' ;;
    path) print -r -- "$HOME/plugins/$2" ;;
    *) return 1 ;;
  esac
}
''')
        bin_dir = self.home / "bin"
        bin_dir.mkdir()
        git = bin_dir / "git"
        git.write_text('''#!/bin/bash
case "$*" in
  *'rev-parse HEAD')
    case "$2" in
      */zsh-autosuggestions) echo 85919cd1ffa7d2d5412f6d3fe437ebdbeeec4fc5 ;;
      */zsh-syntax-highlighting) echo e6683f20e5c38d3e5447f45845d04ddda75d0f23 ;;
      *) exit 1 ;;
    esac ;;
  *'status --porcelain') if [[ -f "$HOME/dirty-plugin" ]]; then echo modified; fi ;;
  *) exit 1 ;;
esac
''')
        git.chmod(0o755)
        env = dict(self.env, ANTIDOTE_ZSH=str(manager), PATH=str(bin_dir) + os.pathsep + self.env["PATH"])
        command = ["bash", str(REPO / "scripts/shell-plugins.sh")]
        subprocess.run(command, env=env, check=True, capture_output=True)
        cache = self.home / ".cache/dotfiles/plugins.zsh"
        before = cache.read_bytes(), cache.stat().st_mtime_ns
        subprocess.run(command, env=env, check=True, capture_output=True)
        self.assertEqual(before, (cache.read_bytes(), cache.stat().st_mtime_ns))
        (self.home / "dirty-plugin").touch()
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("local modifications", result.stderr)
        self.assertEqual(before, (cache.read_bytes(), cache.stat().st_mtime_ns))

    def test_uv_links_and_preserves_previous_preferences(self):
        target = self.home / ".config/uv/uv.toml"
        target.parent.mkdir(parents=True)
        target.write_text("# previous preferences\n")
        for _ in range(2):
            subprocess.run(["bash", str(REPO / "scripts/uv.sh")], env=self.env, check=True, capture_output=True)
        self.assertEqual(target.resolve(), REPO / "uv/uv.toml")
        self.assertEqual(target.with_suffix(".toml.bak").read_text(), "# previous preferences\n")


if __name__ == "__main__":
    unittest.main()
