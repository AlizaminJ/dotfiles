"""Use fake keygen and GitHub clients: never create real keys or contact accounts."""

import base64
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error


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

    def test_existing_pair_is_never_rewritten_and_comments_are_not_uploaded(self):
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

    def test_main_skips_all_github_work_without_a_terminal(self):
        env = dict(PERSONAL_KEY_NAME='id_personal', WORK_KEY_NAME='id_work', REGISTER_GITHUB_KEYS='true')
        with patch.dict(os.environ, env), patch.object(keys.Path, 'home', return_value=self.ssh.parent), \
             patch.object(keys.os, 'umask'), patch.object(keys, 'ensure_key', return_value=PUBLIC), \
             patch.object(keys.sys.stdin, 'isatty', return_value=False), patch.object(keys, 'GitHub') as client:
            keys.main()
            client.assert_not_called()


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


class GitHubKeyTest(unittest.TestCase):
    def setUp(self):
        for guard in [patch.dict(os.environ, {'PATH': os.defpath}, clear=True),
                      patch.object(keys.subprocess, 'run', side_effect=AssertionError('Native tools forbidden in tests')),
                      patch.object(keys.urllib.request, 'build_opener', side_effect=AssertionError('Network forbidden in tests'))]:
            guard.start()
            self.addCleanup(guard.stop)
        self.output = io.StringIO()
        self.stream = contextlib.redirect_stdout(self.output)
        self.stream.__enter__()
        self.addCleanup(self.stream.__exit__, None, None, None)
        self.ask = Mock(return_value=True)
        self.client = keys.GitHub(self.ask)
        self.client.token = Mock(return_value='fixture-token')
        self.client.login = Mock(side_effect=AssertionError('Unexpected login'))

    def test_registers_once_on_verified_account_and_does_not_change_active_login(self):
        stored = []
        def request(token, method, path, data=None):
            self.assertEqual(token, 'fixture-token')
            if path == '/user': return {'login': 'Example'}
            if method == 'POST': stored.append(data); return {'id': 1}
            return stored
        self.client.request = Mock(side_effect=request)
        self.client.register('Example', PUBLIC, 'personal')
        self.client.register('Example', PUBLIC, 'personal')
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0], {'title': 'dotfiles-personal', 'key': PUBLIC})
        self.assertEqual(self.ask.call_count, 1)
        self.client.token.assert_called_with('Example')
        self.client.login.assert_not_called()
        self.assertNotIn('fixture-token', self.output.getvalue())
        self.assertNotIn(BLOB, self.output.getvalue())

    def test_wrong_account_never_gets_a_key(self):
        self.client.request = Mock(return_value={'login': 'DifferentAccount'})
        with self.assertRaises(keys.SetupError): self.client.register('Example', PUBLIC, 'personal')
        self.assertEqual(self.client.request.call_count, 1)
        self.ask.assert_not_called()

    def test_declined_upload_is_not_posted(self):
        self.ask.return_value = False
        self.client.request = Mock(side_effect=[{'login': 'Example'}, []])
        self.client.register('Example', PUBLIC, 'personal')
        self.assertTrue(all(call.args[1] == 'GET' for call in self.client.request.call_args_list))

    def test_duplicate_key_detection_checks_all_pages(self):
        self.client.request = Mock(side_effect=[{'login': 'Example'}, [{'key': 'other'}] * 100, [{'key': PUBLIC + ' old-comment'}]])
        self.client.register('Example', PUBLIC, 'personal')
        self.ask.assert_not_called()
        self.assertEqual(self.client.request.call_args.args[2], '/user/keys?per_page=100&page=2')

    def test_environment_tokens_and_debug_are_not_used_for_account_selection(self):
        with patch.dict(os.environ, {'GH_TOKEN': 'wrong-token', 'GITHUB_TOKEN': 'wrong-token', 'GH_DEBUG': 'api'}):
            client = keys.GitHub()
        with patch.object(keys.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout='fixture-token\n')) as runner:
            self.assertEqual(client.token('Example'), 'fixture-token')
            self.assertEqual(runner.call_args.args[0][-2:], ['--user', 'Example'])
            self.assertNotIn('GH_TOKEN', runner.call_args.kwargs['env'])
            self.assertNotIn('GITHUB_TOKEN', runner.call_args.kwargs['env'])
            self.assertNotIn('GH_DEBUG', runner.call_args.kwargs['env'])

    def test_token_lookup_handles_username_case_without_selecting_another_account(self):
        client = keys.GitHub()
        status = json.dumps({'hosts': {'github.com': [{'login': 'Example', 'active': True}, {'login': 'Other'}]}})
        responses = [subprocess.CompletedProcess([], 1, stdout=''), subprocess.CompletedProcess([], 0, stdout=status),
                     subprocess.CompletedProcess([], 0, stdout='fixture-token')]
        with patch.object(keys.subprocess, 'run', side_effect=responses) as runner:
            self.assertEqual(client.token('example'), 'fixture-token')
            self.assertEqual(runner.call_args.args[0][-2:], ['--user', 'Example'])
            self.assertFalse(any('switch' in call.args[0] for call in runner.call_args_list))

    def test_browser_login_restores_previous_active_account(self):
        client = keys.GitHub(self.ask)
        status = json.dumps({'hosts': {'github.com': [{'login': 'Previous', 'active': True}]}})
        responses = [subprocess.CompletedProcess([], 0, stdout=status), subprocess.CompletedProcess([], 0),
                     subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 0, stdout='fixture-token')]
        with patch.object(keys.subprocess, 'run', side_effect=responses) as runner:
            self.assertEqual(client.login('Example'), 'fixture-token')
            commands = [call.args[0] for call in runner.call_args_list]
            self.assertIn('--skip-ssh-key', commands[1])
            self.assertIn('admin:public_key', commands[1])
            self.assertEqual(commands[2][-2:], ['--user', 'Previous'])

    def test_first_browser_login_works_without_an_existing_account(self):
        for status in [subprocess.CompletedProcess([], 1, stdout=json.dumps({'hosts': {}}), stderr=''),
                       subprocess.CompletedProcess([], 1, stdout='', stderr='You are not logged into any GitHub hosts.')]:
            client = keys.GitHub(self.ask)
            responses = [status, subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 0, stdout='fixture-token')]
            with patch.object(keys.subprocess, 'run', side_effect=responses) as runner:
                self.assertEqual(client.login('Example'), 'fixture-token')
                self.assertFalse(any('switch' in call.args[0] for call in runner.call_args_list))

    def test_failed_browser_login_still_restores_the_previous_account(self):
        client = keys.GitHub(self.ask)
        status = json.dumps({'hosts': {'github.com': [{'login': 'Previous', 'active': True}]}})
        responses = [subprocess.CompletedProcess([], 0, stdout=status), subprocess.CompletedProcess([], 1),
                     subprocess.CompletedProcess([], 0)]
        with patch.object(keys.subprocess, 'run', side_effect=responses) as runner:
            with self.assertRaises(keys.SetupError): client.login('Example')
            self.assertEqual(runner.call_args.args[0][-2:], ['--user', 'Previous'])

    def test_api_errors_and_redirects_do_not_disclose_tokens_or_bodies(self):
        error = urllib.error.HTTPError('https://api.github.com/user/keys', 403, 'private-body', {}, None)
        client = keys.GitHub()
        with patch.object(keys.urllib.request, 'build_opener') as builder:
            builder.return_value.open.side_effect = error
            with self.assertRaises(keys.SetupError) as result:
                client.request('fixture-token', 'POST', '/user/keys', {'key': PUBLIC})
        self.assertNotIn('fixture-token', str(result.exception))
        self.assertNotIn('private-body', str(result.exception))
        self.assertIsNone(keys.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.invalid'))


if __name__ == '__main__':
    unittest.main()
