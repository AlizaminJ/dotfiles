"""Keep CI checks pinned, low-permission, and separate from machine provisioning."""

import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest


REPO = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('ruby'), 'Ruby YAML parser unavailable')
class WorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parser = 'require "yaml"; require "json"; puts JSON.generate(YAML.safe_load(File.read(ARGV.fetch(0)), aliases: false))'
        result = subprocess.check_output(['ruby', '-e', parser, str(REPO / '.github/workflows/checks.yml')], text=True)
        cls.workflow = json.loads(result)

    def test_events_and_permissions_do_not_use_privileged_pr_context(self):
        self.assertEqual(set(self.workflow['on']), {'push', 'pull_request', 'workflow_dispatch'})
        self.assertEqual(self.workflow['permissions'], {'contents': 'read'})
        for job in self.workflow['jobs'].values():
            self.assertNotIn('secrets', job)
            self.assertNotIn('permissions', job)
            self.assertLessEqual(job['timeout-minutes'], 10)

    def test_only_checkout_action_is_used_and_all_revisions_match(self):
        actions = []
        for job in self.workflow['jobs'].values():
            for step in job['steps']:
                if 'uses' in step:
                    self.assertRegex(step['uses'], r'^actions/checkout@[0-9a-f]{40}$')
                    self.assertEqual(step['with']['persist-credentials'], False)
                    self.assertEqual(step['with']['submodules'], False)
                    self.assertEqual(step['with']['lfs'], False)
                    actions.append(step['uses'])
        self.assertEqual(len(actions), 2)
        self.assertEqual(len(set(actions)), 1)

    def test_lint_uses_preinstalled_shellcheck_and_tests_use_system_bash(self):
        lint = self.workflow['jobs']['shellcheck']
        macos = self.workflow['jobs']['macos']
        self.assertEqual(lint['runs-on'], 'ubuntu-24.04')
        self.assertEqual(macos['runs-on'], 'macos-15')
        self.assertIn('shellcheck --external-sources --shell=bash', lint['steps'][-1]['run'])
        scripts = '\n'.join(step.get('run', '') for step in macos['steps'])
        self.assertIn('/bin/bash -n', scripts)
        self.assertIn('/bin/zsh -n', scripts)
        self.assertIn('/bin/bash bin/dotfiles test', scripts)
        self.assertIn('/bin/bash bin/dotfiles secrets', scripts)
        self.assertEqual(macos['steps'][0]['with']['fetch-depth'], 0)
        for step in macos['steps']:
            if 'run' in step:
                self.assertTrue(step['shell'].startswith('/bin/bash --noprofile --norc'))

    def test_run_steps_do_not_install_packages_or_run_setup(self):
        scripts = '\n'.join(step.get('run', '') for job in self.workflow['jobs'].values() for step in job['steps'])
        for command in ['brew install', 'brew bundle', 'npm install', 'pnpm install',
                        'pip install', 'uv sync', 'curl ', 'wget ', 'dotfiles setup']:
            self.assertNotIn(command, scripts)
        self.assertIsNone(re.search(r'^\s*(?:(?:/bin/)?bash\s+)?(?:\./)?bootstrap\.sh\b', scripts, re.MULTILINE))


if __name__ == '__main__':
    unittest.main()
