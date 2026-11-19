"""Task dispatch must preserve caller context without running real setup scripts."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class DotfilesCommandTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.repo = self.home / 'repo with spaces'
        (self.repo / 'bin').mkdir(parents=True)
        (self.repo / 'scripts').mkdir()
        self.wrapper = self.repo / 'bin/dotfiles'
        shutil.copy2(REPO / 'bin/dotfiles', self.wrapper)
        self.caller = self.home / 'other project'
        self.caller.mkdir()
        self.tools = self.home / 'tools'
        self.tools.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), REPO_ROOT='/incorrect-caller-root',
                        PATH=str(self.tools) + os.pathsep + os.environ['PATH'])
        self.stub = '''#!/bin/bash
set -eu
printf '%s\\0' "$0" "$REPO_ROOT" "$PWD" "$@" > "$HOME/invocation"
exit "${STUB_EXIT:-0}"
'''
        self.scripts = {
            'agents': 'agents', 'editors': 'editors', 'shell': 'shell',
            'plugins': 'shell-plugins', 'pnpm': 'pnpm', 'uv': 'uv',
            'git-ssh': 'git-ssh', 'ssh-keys': 'ssh-keys', 'macos': 'macos-defaults', 'homebrew': 'homebrew',
            'doctor': 'doctor',
        }
        for script in self.scripts.values():
            (self.repo / 'scripts' / (script + '.sh')).write_text(self.stub)
        (self.repo / 'bootstrap.sh').write_text(self.stub)
        python = self.tools / 'python3'
        python.write_text(self.stub)
        python.chmod(0o755)

    def run_wrapper(self, *args, executable=None, **env):
        return subprocess.run([str(executable or self.wrapper), *args],
                              cwd=self.caller, env=dict(self.env, **env), capture_output=True, text=True)

    def invocation(self):
        return (self.home / 'invocation').read_bytes().decode().rstrip('\0').split('\0')

    def test_help_and_preview_run_nothing(self):
        for args in [(), ('help',), ('--help',), ('--dry-run', 'setup'),
                     ('--dry-run', 'plugins'), ('--dry-run', 'ssh-keys'), ('--dry-run', 'doctor', 'path with spaces')]:
            with self.subTest(args=args):
                result = self.run_wrapper(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse((self.home / 'invocation').exists())
        self.assertIn('path\\ with\\ spaces', result.stdout)

    def test_each_command_dispatches_once_to_existing_script(self):
        for command, script in self.scripts.items():
            with self.subTest(command=command):
                result = self.run_wrapper(command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.invocation(), [str(self.repo.resolve() / 'scripts' / (script + '.sh')),
                                                     str(self.repo.resolve()), str(self.caller.resolve())])
        self.assertEqual(self.run_wrapper('setup').returncode, 0)
        self.assertEqual(self.invocation()[0], str(self.repo.resolve() / 'bootstrap.sh'))

    def test_doctor_paths_preserve_spaces_and_relative_context(self):
        self.assertEqual(self.run_wrapper('doctor', 'a relative path with spaces').returncode, 0)
        self.assertEqual(self.invocation()[2:], [str(self.caller.resolve()), 'a relative path with spaces'])

    def test_secret_scan_targets_checkout_without_changing_caller_directory(self):
        result = self.run_wrapper('secrets')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.invocation()[1:], [str(self.repo.resolve()), str(self.caller.resolve()),
                                               str(self.repo.resolve() / 'scripts/check-secrets.py')])

    def test_tests_run_from_checkout_not_caller_directory(self):
        result = self.run_wrapper('test')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.invocation()[1:], [str(self.repo.resolve()), str(self.repo.resolve()),
                                               '-m', 'unittest', 'discover', '-s', 'tests', '-v'])

    def test_invalid_commands_and_arguments_run_nothing(self):
        for args in [('unknown',), ('agents; echo nope',), ('agents', 'extra'),
                     ('doctor', 'one', 'two'), ('--dry-run',), ('--help', 'extra')]:
            with self.subTest(args=args):
                result = self.run_wrapper(*args)
                self.assertEqual(result.returncode, 2)
                self.assertFalse((self.home / 'invocation').exists())

    def test_script_failure_is_not_hidden_or_retried(self):
        result = self.run_wrapper('agents', STUB_EXIT='7')
        self.assertEqual(result.returncode, 7)
        self.assertEqual(self.invocation()[0], str(self.repo.resolve() / 'scripts/agents.sh'))

    def test_relative_symlink_still_finds_checkout(self):
        launchers = self.home / 'launchers'
        launchers.mkdir()
        link = launchers / 'dotfiles'
        link.symlink_to(os.path.relpath(self.wrapper, launchers))
        result = self.run_wrapper('agents', executable=link)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.invocation()[1], str(self.repo.resolve()))


if __name__ == '__main__':
    unittest.main()
