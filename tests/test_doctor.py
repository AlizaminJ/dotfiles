"""Health checks must report failures without changing the test home."""

import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class DoctorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.checkout = self.home / "dotfiles"
        self.checkout.mkdir()
        for name in ["scripts", "agents", "nvim", "tmux", "shell", "wezterm", "uv"]:
            (self.checkout / name).symlink_to(REPO / name)
        self.personal = self.home / "workspace/personal"
        self.work = self.home / "workspace/work"
        values = dict(
            PUBLIC_GIT_NAME="", PUBLIC_GIT_EMAIL="",
            PERSONAL_NAME="Personal Example", PERSONAL_EMAIL="personal@example.com",
            PERSONAL_KEY_NAME="id_personal", PERSONAL_ROOT=str(self.personal),
            WORK_NAME="Work Example", WORK_EMAIL="work@example.com",
            WORK_KEY_NAME="id_work", WORK_ROOT=str(self.work),
        )
        (self.checkout / "config.local.sh").write_text(
            "".join(f"{key}={shlex.quote(value)}\n" for key, value in values.items())
        )
        self.bin = self.home / "bin"
        self.bin.mkdir()
        for tool in ["brew", "gh", "nvim", "tmux", "rg", "fd", "tree-sitter", "starship", "zoxide", "fzf", "wezterm"]:
            self.mock(tool, "exit 0\n")
        self.mock("uname", 'echo TestOS\n')
        self.mock("pnpm", '''if [ "$1" = --version ]; then echo 12.16.1; exit; fi
case "$3" in
  minimumReleaseAge) echo 10080 ;;
  minimumReleaseAgeStrict) echo true ;;
  minimumReleaseAgeIgnoreMissingTime|trustLockfile) echo false ;;
  ignoreScripts) if [ -f "$PWD/unsafe-pnpm" ]; then echo false; else echo true; fi ;;
  minimumReleaseAgeExclude) echo undefined ;;
  *) exit 1 ;;
esac
''')
        self.env = {
            key: value for key, value in os.environ.items()
            if not key.startswith("GIT_") and key != "EMAIL"
        }
        self.env.update(
            HOME=str(self.home), REPO_ROOT=str(self.checkout),
            XDG_CONFIG_HOME=str(self.home / ".config"), GIT_CONFIG_NOSYSTEM="1",
            PI_CODING_AGENT_DIR=str(self.home / ".pi/agent"),
            PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
        )
        for script in ["git-ssh.sh", "editors.sh", "agents.sh", "shell.sh", "uv.sh"]:
            self.run_command("bash", str(REPO / "scripts" / script), check=True)
        for key in ["id_personal", "id_work"]:
            (self.home / ".ssh" / key).write_text("test placeholder, not a key\n")
        for root in [self.personal, self.work]:
            self.run_command("git", "init", str(root / "sample"), check=True)
        cache = self.home / ".cache/dotfiles/plugins.zsh"
        cache.parent.mkdir(parents=True)
        cache.write_text("# test plugin cache\n")
        checksum = subprocess.check_output(["cksum"], input=(REPO / "shell/plugins.txt").read_bytes())
        cache.with_suffix(".zsh.manifest").write_bytes(checksum)

    def mock(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/bash\nset -eu\n" + body)
        path.chmod(0o755)

    def run_command(self, *args, check=False, cwd=None):
        return subprocess.run(
            args, cwd=cwd or self.home, env=self.env,
            text=True, capture_output=True, check=check,
        )

    def doctor(self, target=None):
        args = ["bash", str(REPO / "scripts/doctor.sh")]
        if target is not None:
            args.append(str(target))
        return self.run_command(*args)

    def snapshot(self):
        return {
            str(path.relative_to(self.home)): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in self.home.rglob("*") if path.is_file() and not path.is_symlink()
        }

    def test_healthy_and_repeat_runs_are_read_only(self):
        before = self.snapshot()
        for _ in range(2):
            result = self.doctor()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("All checked settings passed", result.stdout)
        self.assertEqual(before, self.snapshot())

    def test_checks_selected_directory_pnpm_overrides(self):
        project = self.work / "project"
        project.mkdir()
        (project / "unsafe-pnpm").touch()
        result = self.doctor(project)
        self.assertEqual(result.returncode, 1)
        self.assertIn("ignoreScripts must be true", result.stdout)

    def test_approved_public_checkout_identity_is_not_reported_as_wrong(self):
        config = self.checkout / 'config.local.sh'
        with config.open('a') as stream:
            stream.write(f'\nPERSONAL_ROOT={shlex.quote(str(self.checkout))}\n'
                         'PUBLIC_GIT_NAME=Example\nPUBLIC_GIT_EMAIL=123+Example@users.noreply.github.com\n')
        self.run_command('git', 'init', str(self.checkout), check=True)
        self.run_command('bash', str(REPO / 'scripts/git-ssh.sh'), check=True)
        result = self.doctor(self.checkout)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Public dotfiles identity matches', result.stdout)

    def test_checks_selected_repository_identity(self):
        project = self.work / "project"
        self.run_command("git", "init", str(project), check=True)
        self.run_command("git", "config", "user.email", "wrong@example.com", cwd=project, check=True)
        result = self.doctor(project)
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not select the expected Work identity", result.stdout)

    def test_reports_missing_link_and_key_without_reading_key_contents(self):
        (self.home / ".tmux.conf").unlink()
        (self.home / ".ssh/id_work").unlink()
        result = self.doctor()
        self.assertEqual(result.returncode, 1)
        self.assertIn("tmux config missing", result.stdout)
        self.assertIn("SSH key file is missing", result.stdout)
        self.assertNotIn("test placeholder", result.stdout + result.stderr)

    def test_missing_local_settings_does_not_hide_other_results(self):
        (self.checkout / "config.local.sh").unlink()
        result = self.doctor()
        self.assertEqual(result.returncode, 1)
        self.assertIn("config.local.sh.example", result.stderr)
        self.assertIn("Neovim config linked", result.stdout)
        self.assertFalse((self.checkout / "config.local.sh").exists())

    def test_pi_reference_and_override_are_reported(self):
        pi = self.home / '.pi/agent'
        (pi / 'AGENTS.md').unlink()
        result = self.doctor()
        self.assertEqual(result.returncode, 1)
        self.assertIn('Pi shared-instructions reference missing', result.stdout)
        (pi / 'AGENTS.md').symlink_to(self.home / '.agents/AGENTS.md')
        (pi / 'AGENTS.override.md').write_text('local override\n')
        result = self.doctor()
        self.assertEqual(result.returncode, 1)
        self.assertIn('AGENTS.override.md hides', result.stdout)

    def test_invalid_directory(self):
        result = self.doctor(self.home / "missing")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage:", result.stderr)


if __name__ == "__main__":
    unittest.main()
