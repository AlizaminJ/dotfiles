"""Public scans must catch staged/history leaks while keeping values out of logs."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class SecretScanTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        self.env.update(HOME=str(self.repo), XDG_CONFIG_HOME=str(self.repo / '.config'), GIT_CONFIG_NOSYSTEM='1')
        self.git('init', '-q')
        shutil.copy2(REPO / '.gitignore', self.repo / '.gitignore')
        self.token = 'ghp_' + 'A' * 36

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], env=self.env,
                              capture_output=True, text=True, check=True)

    def scan(self):
        result = subprocess.run([sys.executable, str(REPO / 'scripts/check-secrets.py'), '--repo', str(self.repo)],
                                env=self.env, capture_output=True, text=True)
        self.assertNotIn(self.token, result.stdout + result.stderr)
        return result

    def commit(self):
        self.git('-c', 'user.name=Example', '-c', 'user.email=example@example.com',
                 'commit', '--no-gpg-sign', '-q', '-m', 'Fixture')

    def test_ignored_private_files_are_not_read(self):
        (self.repo / 'config.local.sh').write_text(self.token)
        (self.repo / '.env').write_text(self.token)
        (self.repo / 'README.md').write_text('Public documentation\n')
        self.assertEqual(self.scan().returncode, 0)

    def test_working_tree_and_staged_only_tokens_are_reported_without_values(self):
        public = self.repo / 'settings.txt'
        public.write_text(self.token)
        self.assertEqual(self.scan().returncode, 1)
        self.git('add', 'settings.txt')
        public.write_text('clean working tree\n')
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertIn('index', result.stdout)

    def test_deleted_historical_token_still_fails(self):
        public = self.repo / 'settings.txt'
        public.write_text(self.token)
        self.git('add', 'settings.txt')
        self.commit()
        self.git('rm', '-q', 'settings.txt')
        self.commit()
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertIn('history', result.stdout)

    def test_force_added_private_file_is_rejected(self):
        (self.repo / '.env').write_text('local-only settings\n')
        self.git('add', '-f', '.env')
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertIn('private file', result.stdout)

    def test_outside_symlink_is_not_followed(self):
        outside = self.repo.parent / (self.repo.name + '-private')
        outside.write_text(self.token)
        self.addCleanup(outside.unlink)
        (self.repo / 'public-link').symlink_to(outside)
        self.assertEqual(self.scan().returncode, 0)

    def test_ignore_rules_cover_private_files_but_allow_templates(self):
        for name in ['config.local.sh', 'config.local.sh.bak.1', '.env.production', '.ssh/id_ed25519',
                     '.pi/agent/auth.json', '.zshrc.local', '.wezterm.local.lua', 'secret.pem', 'notes.bak']:
            result = subprocess.run(['git', '-C', str(self.repo), 'check-ignore', '-q', name], env=self.env)
            self.assertEqual(result.returncode, 0, name)
        for name in ['config.local.sh.example', '.env.example']:
            result = subprocess.run(['git', '-C', str(self.repo), 'check-ignore', '-q', name], env=self.env)
            self.assertEqual(result.returncode, 1, name)

    def test_credentials_in_filenames_are_reported_without_echoing_them(self):
        (self.repo / (self.token + '.txt')).write_text('public text\n')
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertIn('filename', result.stdout)
        self.assertIn('[redacted]', result.stdout)

    def test_force_added_archive_requires_manual_review(self):
        (self.repo / 'download.zip').write_bytes(b'not-a-real-archive')
        self.git('add', '-f', 'download.zip')
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertIn('separate review', result.stdout)

    def test_prefixed_credential_assignment_is_redacted(self):
        value = 'Q' * 40
        (self.repo / 'settings.txt').write_text('OPENAI_API_KEY = "' + value + '"')
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertIn('credential assignment', result.stdout)
        self.assertNotIn(value, result.stdout + result.stderr)

    def test_history_contact_warning_withholds_the_address(self):
        address = 'author@' + 'private.invalid'
        (self.repo / 'README.md').write_text('Public text\n')
        self.git('add', 'README.md')
        self.git('-c', 'user.name=Example', '-c', 'user.email=' + address,
                 'commit', '--no-gpg-sign', '-q', '-m', 'Fixture')
        result = self.scan()
        self.assertEqual(result.returncode, 0)
        self.assertIn('1 contact address(es)', result.stdout)
        self.assertNotIn(address, result.stdout + result.stderr)

    def test_personal_home_path_is_reported_without_echoing_it(self):
        path = '/Users/' + 'fixture-user/private-project'
        (self.repo / 'settings.txt').write_text(path)
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertIn('personal home path', result.stdout)
        self.assertNotIn(path, result.stdout + result.stderr)

    def test_shared_linuxbrew_prefix_is_not_a_personal_path(self):
        (self.repo / 'settings.txt').write_text('/home/linuxbrew/.linuxbrew/bin')
        self.assertEqual(self.scan().returncode, 0)


if __name__ == '__main__':
    unittest.main()
