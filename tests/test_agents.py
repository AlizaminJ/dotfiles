"""Share instructions without importing or changing agent runtime state."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class AgentInstructionsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.pi = self.home / '.pi/agent'
        self.pi.mkdir(parents=True)
        self.env = dict(os.environ, HOME=str(self.home), REPO_ROOT=str(REPO), PI_CODING_AGENT_DIR=str(self.pi))
        self.state = {}
        for name in ['auth.json', 'settings.json', 'trust.json', 'models.json', 'mcp.json',
                     'sessions/local.jsonl', 'extensions/local.ts', 'skills/local/SKILL.md', 'npm/local/cache']:
            path = self.pi / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('local fixture data\n')
            self.state[path] = (path.read_bytes(), path.stat().st_mtime_ns)

    def setup_agents(self, check=True, **env):
        return subprocess.run(
            ['bash', str(REPO / 'scripts/agents.sh')], env=dict(self.env, **env),
            capture_output=True, text=True, check=check,
        )

    def test_pi_links_shared_instructions_and_preserves_runtime_state(self):
        (self.pi / 'AGENTS.md').write_text('existing private instructions\n')
        (self.pi / 'AGENTS.md.bak').write_text('older backup\n')
        self.setup_agents()
        target = self.pi / 'AGENTS.md'
        self.assertEqual(os.readlink(target), str(self.home / '.agents/AGENTS.md'))
        self.assertEqual(target.resolve(), REPO / 'agents/AGENTS.md')
        self.assertEqual((self.pi / 'AGENTS.md.bak.1').read_text(), 'existing private instructions\n')
        self.assertEqual((self.pi / 'AGENTS.md.bak').read_text(), 'older backup\n')
        self.assertFalse(self.pi.is_symlink())
        for path, expected in self.state.items():
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), expected)

    def test_repeat_run_does_not_duplicate_backups_or_rewrite_references(self):
        self.setup_agents()
        files = [self.home / '.agents/AGENTS.md', self.pi / 'AGENTS.md',
                 self.home / '.claude/CLAUDE.md',
                 self.home / 'Library/Application Support/Code/User/prompts/global.instructions.md']
        before = {path: (path.read_bytes(), path.lstat().st_mtime_ns) for path in files}
        self.setup_agents()
        self.assertEqual(before, {path: (path.read_bytes(), path.lstat().st_mtime_ns) for path in files})
        self.assertEqual(list(self.pi.glob('AGENTS.md.bak*')), [])

    def test_custom_pi_directory_and_existing_broken_link(self):
        custom = self.home / 'custom pi agent'
        custom.mkdir()
        (custom / 'AGENTS.md').symlink_to(self.home / 'missing-instructions')
        self.setup_agents(PI_CODING_AGENT_DIR=str(custom))
        self.assertEqual((custom / 'AGENTS.md').resolve(), REPO / 'agents/AGENTS.md')
        self.assertTrue((custom / 'AGENTS.md.bak').is_symlink())
        self.assertFalse((self.pi / 'AGENTS.md').exists())

    def test_override_stops_before_changing_other_agent_files(self):
        override = self.pi / 'AGENTS.override.md'
        override.write_text('existing override\n')
        result = self.setup_agents(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('would hide', result.stderr)
        self.assertEqual(override.read_text(), 'existing override\n')
        self.assertFalse((self.home / '.agents').exists())
        self.assertFalse((self.pi / 'AGENTS.md').exists())

    def test_relative_pi_directory_is_rejected(self):
        result = self.setup_agents(check=False, PI_CODING_AGENT_DIR='relative-agent')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('absolute path', result.stderr)
        self.assertFalse((self.home / '.agents').exists())


if __name__ == '__main__':
    unittest.main()
