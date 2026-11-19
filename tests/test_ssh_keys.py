"""Use fake keygen only: never create real keys, contact accounts, or touch a clipboard."""

import base64
import importlib.util
import io
import os
from pathlib import Path
import socket
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ssh_keys', REPO / 'scripts/ssh-keys.py')
keys = importlib.util.module_from_spec(spec)
spec.loader.exec_module(keys)
BLOB = base64.b64encode(b'fixture-public-data').decode()
PUBLIC = 'ssh-ed25519 ' + BLOB


class LocalKeyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ssh = Path(self.temp.name) / '.ssh'
        self.ssh.mkdir(mode=0o700)
        self.private = self.ssh / 'id_personal'
        self.public = self.ssh / 'id_personal.pub'
        self.output = io.StringIO()
        self.addCleanup(patch.stopall)
        patch('sys.stdout', self.output).start()
        patch.object(keys.subprocess, 'run', side_effect=AssertionError('Native tools forbidden in tests')).start()
        patch.object(socket, 'create_connection', side_effect=AssertionError('Network forbidden in tests')).start()
        self.fp = patch.object(keys, 'fingerprint', return_value='SHA256:fixture').start()

    def pair(self):
        self.private.write_text('fixture-private-data\n')
        self.public.write_bytes((PUBLIC + ' private-comment@example.com\n').encode())

    def test_generates_once_with_passphrase_prompt_and_safe_permissions(self):
        def generate(command, **kwargs):
            self.assertEqual(command[:5], ['ssh-keygen', '-q', '-t', 'ed25519', '-a'])
            self.assertNotIn('-N', command)
            self.assertNotIn('-P', command)
            target = Path(command[command.index('-f') + 1])
            target.write_text('fixture-private-data\n')
            Path(str(target) + '.pub').write_text(PUBLIC + ' generic-comment\n')
            return subprocess.CompletedProcess(command, 0)
        with patch.object(keys.subprocess, 'run', side_effect=generate) as runner:
            self.assertEqual(keys.ensure_key(self.ssh, 'id_personal', 'personal', True), PUBLIC)
            self.assertEqual(keys.ensure_key(self.ssh, 'id_personal', 'personal', True), PUBLIC)
            self.assertEqual(runner.call_count, 1)
        self.assertEqual(stat.S_IMODE(self.private.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.public.stat().st_mode), 0o644)
        self.assertNotIn('fixture-private-data', self.output.getvalue())
        self.assertNotIn(BLOB, self.output.getvalue())

    def test_concurrent_key_creation_is_not_overwritten(self):
        def generate(command, **kwargs):
            target = Path(command[command.index('-f') + 1])
            target.write_text('new fixture data\n')
            Path(str(target) + '.pub').write_text(PUBLIC + '\n')
            self.private.write_text('concurrent original\n')
            return subprocess.CompletedProcess(command, 0)
        with patch.object(keys.subprocess, 'run', side_effect=generate), self.assertRaises(FileExistsError):
            keys.ensure_key(self.ssh, 'id_personal', 'personal', True)
        self.assertEqual(self.private.read_text(), 'concurrent original\n')
        self.assertFalse(self.public.exists())

    def test_existing_pair_is_never_rewritten_or_displayed(self):
        self.pair()
        before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in [self.private, self.public]]
        with patch.object(keys.subprocess, 'run') as runner:
            material = keys.ensure_key(self.ssh, 'id_personal', 'personal', False)
            runner.assert_not_called()
        self.assertEqual(material, PUBLIC)
        self.assertEqual(before, [(path.read_bytes(), path.stat().st_mtime_ns) for path in [self.private, self.public]])
        self.assertNotIn('private-comment', self.output.getvalue())

    def test_missing_public_key_is_recovered_without_replacing_private(self):
        self.private.write_text('fixture-private-data\n')
        with patch.object(keys.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout=PUBLIC + '\n')) as runner:
            self.assertEqual(keys.ensure_key(self.ssh, 'id_personal', 'personal', True), PUBLIC)
            self.assertEqual(runner.call_args.args[0], ['ssh-keygen', '-y', '-f', str(self.private)])
        self.assertEqual(self.private.read_text(), 'fixture-private-data\n')

    def test_missing_keys_refuse_noninteractive_empty_passphrase_generation(self):
        with patch.object(keys.subprocess, 'run') as runner:
            with self.assertRaises(keys.SetupError):
                keys.ensure_key(self.ssh, 'id_personal', 'personal', False)
            runner.assert_not_called()
        self.assertFalse(self.private.exists())

    def test_orphan_public_key_and_symlinks_are_not_overwritten(self):
        self.public.write_text(PUBLIC + '\n')
        with self.assertRaises(keys.SetupError):
            keys.ensure_key(self.ssh, 'id_personal', 'personal', True)
        self.public.unlink()
        self.private.symlink_to(self.ssh / 'missing')
        with self.assertRaises(keys.SetupError):
            keys.ensure_key(self.ssh, 'id_personal', 'personal', True)
        self.assertTrue(self.private.is_symlink())

    def test_mismatch_and_unsafe_filenames_fail(self):
        self.pair()
        self.fp.side_effect = ['SHA256:first', 'SHA256:second']
        with self.assertRaises(keys.SetupError):
            keys.ensure_key(self.ssh, 'id_personal', 'personal', False)
        for name in ['../escape', 'config', 'Known_Hosts', 'id_key.pub', '-option']:
            with self.subTest(name=name), self.assertRaises(keys.SetupError):
                keys.key_name(name)

    def test_main_prints_only_manual_commands_without_touching_accounts_or_clipboard(self):
        self.pair()
        (self.ssh / 'id_work').write_text('fixture-private-data\n')
        (self.ssh / 'id_work.pub').write_text(PUBLIC + '\n')
        env = dict(PERSONAL_KEY_NAME='id_personal', WORK_KEY_NAME='id_work')
        with patch.dict(os.environ, env, clear=True), patch.object(keys.Path, 'home', return_value=self.ssh.parent), \
             patch.object(keys.os, 'umask'), patch.object(keys.sys.stdin, 'isatty', return_value=False):
            keys.main()
        output = self.output.getvalue()
        self.assertIn('Personal: pbcopy < "$HOME/.ssh/id_personal.pub"', output)
        self.assertIn('Work: pbcopy < "$HOME/.ssh/id_work.pub"', output)
        self.assertIn('https://github.com/settings/ssh/new', output)
        self.assertIn('nothing was copied, opened, or uploaded', output)
        for value in ['fixture-private-data', BLOB, 'private-comment']:
            self.assertNotIn(value, output)


class FingerprintTest(unittest.TestCase):
    def test_private_fingerprint_cannot_fall_back_to_adjacent_public_file(self):
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory) / 'key'
            private.write_text('fixture-private-data')
            Path(str(private) + '.pub').write_text('unrelated fixture')
            def inspect(command, **kwargs):
                isolated = Path(command[-1])
                self.assertNotEqual(isolated, private)
                self.assertFalse(Path(str(isolated) + '.pub').exists())
                self.assertEqual(isolated.read_text(), 'fixture-private-data')
                self.assertEqual(stat.S_IMODE(isolated.stat().st_mode), 0o600)
                return subprocess.CompletedProcess(command, 0, stdout='256 SHA256:fixture comment\n')
            with patch.object(keys.subprocess, 'run', side_effect=inspect):
                self.assertEqual(keys.fingerprint(private, private=True), 'SHA256:fixture')
            self.assertEqual(len(list(Path(directory).iterdir())), 2)


if __name__ == '__main__':
    unittest.main()
