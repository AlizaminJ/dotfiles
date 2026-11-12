"""Project sessions must be repeatable without attaching to the user's tmux server."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class ProjectSessionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        mock = self.bin / "tmux"
        mock.write_text(f"#!{sys.executable}\n" + '''import json, os, pathlib, sys
args = sys.argv[1:]
home = pathlib.Path(os.environ['HOME'])
with (home / 'calls.jsonl').open('a') as log:
    log.write(json.dumps(args) + '\\n')
state = home / 'sessions.json'
sessions = json.loads(state.read_text()) if state.exists() else []
if args[0] == 'has-session':
    sys.exit(0 if args[2].removeprefix('=') in sessions else 1)
if args[0] == 'switch-client':
    sys.exit(0 if args[2].removeprefix('=') in sessions else 1)
if args[0] == 'new-session':
    session = args[args.index('-s') + 1]
    if session in sessions and '-A' not in args:
        sys.exit(1)
    if session not in sessions:
        sessions.append(session)
    state.write_text(json.dumps(sessions))
    sys.exit(0)
sys.exit(2)
''')
        mock.chmod(0o755)
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_") and key != "TMUX"}
        self.env.update(HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / ".config"),
                        GIT_CONFIG_NOSYSTEM="1", PATH=str(self.bin) + os.pathsep + os.environ["PATH"])

    def tat(self, directory, inside=False):
        env = dict(self.env)
        if inside:
            env["TMUX"] = "test-client"
        return subprocess.run([str(REPO / "bin/tat"), str(directory)], env=env,
                              capture_output=True, text=True, check=True)

    def calls(self):
        return [json.loads(line) for line in (self.home / "calls.jsonl").read_text().splitlines()]

    def test_outside_tmux_resumes_and_separates_identical_names(self):
        first = self.home / "personal/project with spaces"
        second = self.home / "work/project with spaces"
        first.mkdir(parents=True)
        second.mkdir(parents=True)
        self.tat(first)
        self.tat(first)
        self.tat(second)
        calls = self.calls()
        names = [call[call.index('-s') + 1] for call in calls]
        self.assertEqual(names[0], names[1])
        self.assertNotEqual(names[0], names[2])
        self.assertTrue(all(call[:2] == ['new-session', '-A'] for call in calls))
        self.assertEqual(calls[0][-1], str(first.resolve()))

    def test_inside_tmux_creates_once_then_switches_without_nesting(self):
        project = self.home / "project"
        project.mkdir()
        self.tat(project, inside=True)
        self.tat(project, inside=True)
        calls = self.calls()
        self.assertEqual(sum(call[0] == 'new-session' for call in calls), 1)
        self.assertEqual(sum(call[0] == 'switch-client' for call in calls), 2)
        self.assertIn('-d', next(call for call in calls if call[0] == 'new-session'))
        self.assertTrue(all(call[2].startswith('=') for call in calls if call[0] in ('has-session', 'switch-client')))

    def test_git_subdirectories_and_symlinks_reuse_the_same_session(self):
        project = self.home / "project"
        project.mkdir()
        subprocess.run(['git', 'init', '-q', str(project)], env=self.env, check=True)
        nested = project / "src/nested"
        nested.mkdir(parents=True)
        alias = self.home / "project-link"
        alias.symlink_to(project)
        for directory in [project, nested, alias]:
            self.tat(directory)
        names = [call[call.index('-s') + 1] for call in self.calls()]
        self.assertEqual(len(set(names)), 1)

    def test_worktrees_get_separate_sessions(self):
        project = self.home / "repository"
        worktree = self.home / "feature"
        subprocess.run(['git', 'init', '-q', str(project)], env=self.env, check=True)
        subprocess.run(['git', '-C', str(project), '-c', 'user.name=Test', '-c', 'user.email=test@example.com',
                        'commit', '--allow-empty', '--no-gpg-sign', '-q', '-m', 'Initial'], env=self.env, check=True)
        subprocess.run(['git', '-C', str(project), 'worktree', 'add', '--detach', str(worktree)],
                       env=self.env, check=True, capture_output=True)
        self.tat(project)
        self.tat(worktree)
        names = [call[call.index('-s') + 1] for call in self.calls()]
        self.assertNotEqual(names[0], names[1])

    def test_invalid_directory_does_not_start_tmux(self):
        result = subprocess.run([str(REPO / 'bin/tat'), str(self.home / 'missing')],
                                env=self.env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / 'calls.jsonl').exists())


if __name__ == '__main__':
    unittest.main()
