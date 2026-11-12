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

    def test_work_is_default_ssh_account_and_personal_has_its_own_host(self):
        self.setup_git()
        config = (self.home / '.ssh/config').read_text()
        for host, key in [('github.com', 'id_work'), ('github.com-personal', 'id_personal')]:
            block = config.split(f'Host {host}\n', 1)[1].split('\nHost ', 1)[0]
            self.assertIn(f'IdentityFile ~/.ssh/{key}\n', block)
            self.assertIn('IdentitiesOnly yes', block)
            self.assertIn('AddKeysToAgent yes', block)
            self.assertIn('UseKeychain yes', block)
        self.assertNotIn('Host github.com-work', config)

    def test_setup_leaves_existing_repo_identity_untouched(self):
        self.init_repo(self.checkout)
        self.run_command('git', 'config', '--local', 'user.name', 'Example', cwd=self.checkout)
        self.run_command('git', 'config', '--local', 'user.email', '123+Example@users.noreply.github.com', cwd=self.checkout)
        before = (self.checkout / '.git/config').read_bytes()
        self.setup_git()
        self.setup_git()
        self.assertEqual((self.checkout / '.git/config').read_bytes(), before)
        self.assertFalse((self.checkout / '.git/config.bak').exists())

    def test_personal_noreply_email_does_not_change_work_identity(self):
        self.write_config(PERSONAL_EMAIL='123+Example@users.noreply.github.com')
        self.setup_git()
        personal = self.init_repo(self.personal / 'project')
        work = self.init_repo(self.work / 'project')
        self.assertEqual(self.run_command('git', 'config', 'user.email', cwd=personal).stdout.strip(),
                         '123+Example@users.noreply.github.com')
        self.assertEqual(self.run_command('git', 'config', 'user.email', cwd=work).stdout.strip(),
                         'work@example.com')

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

    def test_symlinked_targets_stop_before_any_setup_writes(self):
        def snapshot(home):
            result = {}
            for path in [home, *home.rglob('*')]:
                info = path.lstat()
                data = os.readlink(path) if path.is_symlink() else path.read_bytes() if path.is_file() else None
                result[str(path.relative_to(home))] = (info.st_mode, info.st_mtime_ns, data)
            return result

        targets = ['.gitconfig', '.gitconfig-personal', '.gitconfig-work',
                   '.gitignore_global', '.ssh', '.ssh/config']
        for relative in targets:
            for dangling in [False, True]:
                with self.subTest(target=relative, dangling=dangling), tempfile.TemporaryDirectory(dir=self.home) as directory:
                    home = Path(directory)
                    victim = home / 'unrelated-target'
                    if not dangling:
                        if relative == '.ssh':
                            victim.mkdir(mode=0o755)
                            (victim / 'config').write_text('# existing SSH settings\n')
                        else:
                            victim.write_text('[user]\n  name = Fixture\n')
                    target = home / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.symlink_to(victim, target_is_directory=relative == '.ssh')
                    before = snapshot(home)
                    result = subprocess.run(
                        ['/bin/bash', str(REPO / 'scripts/git-ssh.sh')], cwd=home,
                        env={'HOME': str(home), 'REPO_ROOT': str(self.checkout),
                             'PATH': os.defpath, 'GIT_CONFIG_NOSYSTEM': '1', 'TMPDIR': str(home)},
                        capture_output=True, text=True,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertIn('symlink', result.stderr.lower())
                    self.assertEqual(snapshot(home), before)
                    self.assertFalse(self.personal.exists())
                    self.assertFalse(self.work.exists())

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

    def test_unsafe_or_colliding_key_filenames_stop_before_writes(self):
        for name in ['../outside', 'config', 'KNOWN_HOSTS', 'id_key.pub', 'id_personal', 'ID_PERSONAL']:
            with self.subTest(name=name):
                self.write_config(WORK_KEY_NAME=name)
                result = self.setup_git(check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.home / '.gitconfig').exists())
                self.assertFalse((self.home / '.ssh').exists())

    def test_trailing_slashes_are_supported(self):
        self.write_config(PERSONAL_ROOT=str(self.personal) + "/", WORK_ROOT=str(self.work) + "/")
        self.setup_git()
        repo = self.init_repo(self.work / "project")
        self.assertEqual(self.run_command("git", "config", "user.email", cwd=repo).stdout.strip(), "work@example.com")


if __name__ == "__main__":
    unittest.main()
