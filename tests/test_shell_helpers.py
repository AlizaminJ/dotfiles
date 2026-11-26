"""Credential helpers use fake CLIs, never a real vault, account, or clipboard."""

import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('zsh'), 'zsh unavailable')
class ShellHelpersTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        tools = self.home / 'bin'
        tools.mkdir()
        fake = tools / 'fixture-cli'
        fake.write_text(f'#!{sys.executable}\n' + '''import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
home = pathlib.Path(os.environ['HOME'])
with (home / 'calls').open('a') as output:
    output.write(json.dumps([name, *args]) + '\\n')
if name == 'bw':
    print('fixture-session' if args[0] == 'unlock' else os.environ['VAULT_ITEM'])
elif name == 'databricks' and args[0] == 'secrets':
    print(json.dumps({'value': os.environ['ENCODED_VALUE']}))
elif name == 'pbcopy':
    (home / 'clipboard').write_bytes(sys.stdin.buffer.read())
if os.environ.get('FAIL_TOOL') == name:
    sys.exit(1)
''')
        fake.chmod(0o755)
        for name in ['bw', 'databricks', 'pbcopy', 'aws', 'git', 'curl', 'prettyping', 'date']:
            (tools / name).symlink_to(fake)
        self.item = {'fields': [
            {'name': 'aws_access_key_id', 'value': 'fixture-access'},
            {'name': 'aws_secret_access_key', 'value': 'fixture-secret'},
        ]}
        self.env = dict(HOME=str(self.home), PATH=str(tools) + os.pathsep + os.environ['PATH'],
                        VAULT_ITEM=json.dumps(self.item), ENCODED_VALUE=base64.b64encode(b'fixture\n\n').decode(),
                        AWS_ACCESS_KEY_ID='previous-access', AWS_SECRET_ACCESS_KEY='previous-secret',
                        AWS_SESSION_TOKEN='previous-token', AWS_PROFILE='previous-profile', BW_SESSION='previous-session')

    def run_shell(self, body, **env):
        return subprocess.run(['/bin/zsh', '-f', '-c', 'source "$1"; ' + body,
                               'test', str(REPO / 'shell/functions.zsh')], env=dict(self.env, **env),
                              capture_output=True, text=True)

    def calls(self):
        path = self.home / 'calls'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_missing_targets_do_not_invoke_tools(self):
        result = self.run_shell('for helper in gclean latency weather dlogin awslogin get-secret; do "$helper"; [[ $? == 2 ]] || exit 1; done')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [])

    def test_branch_cleanup_and_logins_use_explicit_arguments(self):
        result = self.run_shell('gclean feature-one && dlogin account-profile workspace-profile && weather "Sample City" && latency example.com')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [
            ['git', 'branch', '-d', '--', 'feature-one'], ['git', 'fetch', '--prune'],
            ['databricks', 'auth', 'login', '--profile', 'account-profile'],
            ['databricks', 'auth', 'login', '--profile', 'workspace-profile'],
            ['curl', '-q', '--fail', '--silent', '--show-error', 'https://wttr.in/Sample%20City'],
            ['date'], ['prettyping', 'example.com'],
        ])
        (self.home / 'calls').unlink()
        self.assertNotEqual(self.run_shell('gclean feature-one', FAIL_TOOL='git').returncode, 0)
        self.assertEqual(self.calls(), [['git', 'branch', '-d', '--', 'feature-one']])

    def test_vault_unlock_preserves_session_on_failure_and_hides_trace(self):
        for failed in [False, True]:
            expected = 'previous-session' if failed else 'fixture-session'
            result = self.run_shell(f'set -x; bwu; set +x; [[ "$BW_SESSION" == {expected} ]]', FAIL_TOOL='bw' if failed else '')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('fixture-session', result.stdout + result.stderr)

    def test_aws_credentials_are_replaced_together_without_logging_values(self):
        result = self.run_shell('set -x; awslogin selected-item selected-profile; set +x; '
                                '[[ "$AWS_ACCESS_KEY_ID" == fixture-access && "$AWS_SECRET_ACCESS_KEY" == fixture-secret && '
                                '"$AWS_PROFILE" == selected-profile && -z ${AWS_SESSION_TOKEN+x} ]]')
        self.assertEqual(result.returncode, 0, result.stderr)
        for value in ['fixture-access', 'fixture-secret']:
            self.assertNotIn(value, result.stdout + result.stderr)
        self.item['fields'].append({'name': 'aws_session_token', 'value': 'fixture-token'})
        result = self.run_shell('awslogin selected-item selected-profile && [[ "$AWS_SESSION_TOKEN" == fixture-token ]]',
                                VAULT_ITEM=json.dumps(self.item))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_failed_vault_reads_or_invalid_fields_preserve_existing_credentials(self):
        invalid = {'fields': [{'name': 'aws_access_key_id', 'value': 'fixture-access'}]}
        for overrides in [dict(FAIL_TOOL='bw'), dict(VAULT_ITEM=json.dumps(invalid)), dict(VAULT_ITEM='invalid json')]:
            result = self.run_shell('awslogin selected-item selected-profile; [[ $? != 0 ]] || exit 1; '
                                    '[[ "$AWS_ACCESS_KEY_ID" == previous-access && "$AWS_SECRET_ACCESS_KEY" == previous-secret && '
                                    '"$AWS_PROFILE" == previous-profile && "$AWS_SESSION_TOKEN" == previous-token ]]', **overrides)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_secret_copy_preserves_newlines_and_failed_reads_leave_clipboard_untouched(self):
        clipboard = self.home / 'clipboard'
        result = self.run_shell('set -x; get-secret selected-key selected-profile selected-scope; set +x')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(clipboard.read_bytes(), b'fixture\n\n')
        self.assertNotIn('fixture\n', result.stdout + result.stderr)
        self.assertIn(['databricks', 'secrets', 'get-secret', 'selected-scope', 'selected-key', '--profile', 'selected-profile'], self.calls())
        for overrides in [dict(FAIL_TOOL='databricks'), dict(ENCODED_VALUE='invalid!'), dict(ENCODED_VALUE='')]:
            clipboard.write_bytes(b'previous clipboard')
            self.assertNotEqual(self.run_shell('get-secret selected-key selected-profile selected-scope', **overrides).returncode, 0)
            self.assertEqual(clipboard.read_bytes(), b'previous clipboard')


if __name__ == '__main__':
    unittest.main()
