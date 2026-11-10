"""Exercise setup in a temporary home, never the real user's configuration."""

import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class GitProfilesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.checkout = self.home / "dotfiles"
        self.checkout.mkdir()
        (self.checkout / "scripts").symlink_to(REPO / "scripts")
        self.personal = self.home / "workspace/personal projects"
        self.work = self.home / "workspace/work projects"
        self.env = {
            key: value for key, value in os.environ.items()
            if not key.startswith("GIT_") and key != "EMAIL"
        }
        self.env.update(
            HOME=str(self.home), REPO_ROOT=str(self.checkout),
            XDG_CONFIG_HOME=str(self.home / ".config"), GIT_CONFIG_NOSYSTEM="1",
        )
        self.write_config()

    def write_config(self, **overrides):
        values = dict(
            PUBLIC_GIT_NAME="", PUBLIC_GIT_EMAIL="",
            PERSONAL_NAME='Personal "Example" #1',
            PERSONAL_EMAIL="personal@example.com", PERSONAL_KEY_NAME="id_personal",
            PERSONAL_ROOT=str(self.personal), WORK_NAME="Work Example",
            WORK_EMAIL="work@example.com", WORK_KEY_NAME="id_work",
            WORK_ROOT=str(self.work),
        )
        values.update(overrides)
        (self.checkout / "config.local.sh").write_text(
            "".join(f"{key}={shlex.quote(value)}\n" for key, value in values.items())
        )

    def run_command(self, *args, cwd=None, check=True):
        return subprocess.run(
            args, env=self.env, cwd=cwd or self.home, text=True,
            capture_output=True, check=check,
        )

    def setup_git(self, check=True):
        return self.run_command("bash", str(REPO / "scripts/git-ssh.sh"), check=check)

    def init_repo(self, path):
        path.mkdir(parents=True, exist_ok=True)
        self.run_command("git", "init", str(path))
        return path

    def test_profiles_and_explicit_identity_outside_roots(self):
        self.setup_git()
        for root, name, email in [
            (self.personal, 'Personal "Example" #1', "personal@example.com"),
            (self.work, "Work Example", "work@example.com"),
        ]:
            repo = self.init_repo(root / "nested/project")
            self.assertEqual(self.run_command("git", "config", "user.name", cwd=repo).stdout.strip(), name)
            self.assertEqual(self.run_command("git", "config", "user.email", cwd=repo).stdout.strip(), email)
            self.run_command("git", "commit", "--allow-empty", "-m", "test", cwd=repo)

        for outside in [self.home / "other", Path(str(self.work) + "-other")]:
            repo = self.init_repo(outside)
            result = self.run_command("git", "commit", "--allow-empty", "-m", "test", cwd=repo, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("identity", result.stderr.lower())
            self.run_command("git", "config", "user.name", "Explicit Name", cwd=repo)
            self.run_command("git", "config", "user.email", "explicit@example.com", cwd=repo)
            self.run_command("git", "commit", "--allow-empty", "-m", "test", cwd=repo)

    def test_public_identity_is_local_only_and_repeatable(self):
        self.init_repo(self.checkout)
        self.run_command('git', 'config', '--local', 'user.name', 'Previous Name', cwd=self.checkout)
        self.run_command('git', 'config', '--local', 'user.email', 'previous@example.com', cwd=self.checkout)
        old_config = (self.checkout / '.git/config').read_bytes()
        self.write_config(PUBLIC_GIT_NAME='Example', PUBLIC_GIT_EMAIL='123+Example@users.noreply.github.com')
        self.setup_git()
        self.assertEqual(self.run_command('git', 'whoami', cwd=self.checkout).stdout.strip(),
                         'Example <123+Example@users.noreply.github.com>')
        self.assertEqual((self.checkout / '.git/config.bak').read_bytes(), old_config)
        personal = self.init_repo(self.personal / 'other')
        self.assertEqual(self.run_command('git', 'config', 'user.email', cwd=personal).stdout.strip(), 'personal@example.com')
        self.setup_git()
        self.assertFalse((self.checkout / '.git/config.bak.1').exists())

    def test_public_identity_rejects_contact_email_before_writing_configs(self):
        self.write_config(PUBLIC_GIT_NAME='Example', PUBLIC_GIT_EMAIL='private@example.com')
        result = self.setup_git(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('noreply', result.stderr)
        self.assertFalse((self.home / '.gitconfig').exists())

    def test_whoami_reports_effective_identity_and_requires_one(self):
        self.setup_git()
        for root, expected in [
            (self.personal, 'Personal "Example" #1 <personal@example.com>'),
            (self.work, "Work Example <work@example.com>"),
        ]:
            repo = self.init_repo(root / "project")
            self.assertEqual(self.run_command("git", "whoami", cwd=repo).stdout.strip(), expected)
        repo = self.init_repo(self.home / "outside")
        self.assertNotEqual(self.run_command("git", "whoami", cwd=repo, check=False).returncode, 0)
        self.run_command("git", "config", "user.name", "Explicit Name", cwd=repo)
        self.run_command("git", "config", "user.email", "explicit@example.com", cwd=repo)
        self.assertEqual(self.run_command("git", "whoami", cwd=repo).stdout.strip(), "Explicit Name <explicit@example.com>")
        self.env.update(GIT_AUTHOR_NAME="Author Override", GIT_AUTHOR_EMAIL="override@example.com")
        self.assertEqual(self.run_command("git", "whoami", cwd=repo).stdout.strip(), "Author Override <override@example.com>")

    def test_main_default_does_not_rename_existing_branches(self):
        existing = self.personal / "existing"
        existing.mkdir(parents=True)
        self.run_command("git", "init", "--initial-branch=legacy", str(existing))
        self.setup_git()
        new = self.init_repo(self.work / "new")
        self.assertEqual(self.run_command("git", "symbolic-ref", "--short", "HEAD", cwd=new).stdout.strip(), "main")
        self.assertEqual(self.run_command("git", "symbolic-ref", "--short", "HEAD", cwd=existing).stdout.strip(), "legacy")

    def test_repeat_run_preserves_files_and_existing_backups(self):
        original = '[user]\n  email = old@example.com\n'
        (self.home / ".gitconfig").write_text(original)
        (self.home / ".gitconfig.bak").write_text("older backup\n")
        self.setup_git()
        self.assertEqual((self.home / ".gitconfig.bak.1").read_text(), original)
        self.assertEqual((self.home / ".gitconfig.bak").read_text(), "older backup\n")
        paths = [self.home / name for name in [
            ".gitconfig", ".gitconfig-personal", ".gitconfig-work", ".gitignore_global", ".ssh/config",
        ]]
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}
        self.setup_git()
        self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths})
        self.assertFalse((self.home / ".gitconfig.bak.2").exists())
        self.assertEqual((self.home / ".ssh/config").read_text().count("# --- dotfiles:git-ssh"), 1)

    def test_missing_or_incomplete_config_stops_before_changes(self):
        config = self.checkout / "config.local.sh"
        config.unlink()
        self.assertNotEqual(self.setup_git(check=False).returncode, 0)
        self.write_config(WORK_EMAIL="")
        self.assertNotEqual(self.setup_git(check=False).returncode, 0)
        self.assertFalse((self.home / ".gitconfig").exists())
        self.assertFalse(self.personal.exists())

    def test_rejects_ambiguous_roots(self):
        for root in [str(self.personal), str(self.personal / "nested"), "relative", "/", "/tmp/../work", "/tmp/work*", "/tmp/work[1]"]:
            with self.subTest(root=root):
                self.write_config(WORK_ROOT=root)
                self.assertNotEqual(self.setup_git(check=False).returncode, 0)
                self.assertFalse((self.home / ".gitconfig").exists())

    def test_trailing_slashes_are_supported(self):
        self.write_config(PERSONAL_ROOT=str(self.personal) + "/", WORK_ROOT=str(self.work) + "/")
        self.setup_git()
        repo = self.init_repo(self.work / "project")
        self.assertEqual(self.run_command("git", "config", "user.email", cwd=repo).stdout.strip(), "work@example.com")


if __name__ == "__main__":
    unittest.main()
