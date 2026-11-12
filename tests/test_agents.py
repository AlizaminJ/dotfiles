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
                 self.home / 'Library/Application Support/Code/User/prompts/global.instructions.md',
                 self.home / '.agents/skills/code-review/SKILL.md',
                 self.home / '.agents/skills/security-review/SKILL.md',
                 self.home / '.agents/skills/essayist/SKILL.md',
                 self.home / '.agents/skills/essayist/references/writing-guide.md']
        before = {path: (path.read_bytes(), path.lstat().st_mtime_ns) for path in files}
        self.setup_agents()
        self.assertEqual(before, {path: (path.read_bytes(), path.lstat().st_mtime_ns) for path in files})
        self.assertEqual(list(self.pi.glob('AGENTS.md.bak*')), [])

    def test_only_managed_skill_files_are_linked_and_existing_content_is_backed_up(self):
        unrelated = self.home / '.agents/skills/custom-writing/SKILL.md'
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text('existing personal skill\n')
        original = unrelated.read_bytes(), unrelated.stat().st_mtime_ns
        existing = self.home / '.agents/skills/code-review/SKILL.md'
        existing.parent.mkdir(parents=True)
        existing.write_text('previous review instructions\n')
        essayist_files = ['essayist/SKILL.md', 'essayist/references/writing-guide.md']
        for relative in essayist_files:
            target = self.home / '.agents/skills' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('previous writing instructions\n')
            target.with_name(target.name + '.bak').write_text('older private backup\n')
        extra = self.home / '.agents/skills/essayist/private-notes.md'
        extra.write_text('local fixture notes\n')
        self.setup_agents()
        self.setup_agents()
        self.assertEqual((unrelated.read_bytes(), unrelated.stat().st_mtime_ns), original)
        self.assertEqual(existing.with_name('SKILL.md.bak').read_text(), 'previous review instructions\n')
        self.assertFalse(existing.with_name('SKILL.md.bak.1').exists())
        self.assertEqual(extra.read_text(), 'local fixture notes\n')
        for relative in essayist_files:
            target = self.home / '.agents/skills' / relative
            self.assertEqual(target.resolve(), REPO / 'agents/skills' / relative)
            self.assertEqual(target.with_name(target.name + '.bak').read_text(), 'older private backup\n')
            self.assertEqual(target.with_name(target.name + '.bak.1').read_text(), 'previous writing instructions\n')
            self.assertFalse(target.with_name(target.name + '.bak.2').exists())
        for name in ['code-review', 'security-review', 'essayist']:
            target = self.home / '.agents/skills' / name / 'SKILL.md'
            self.assertEqual(target.resolve(), REPO / 'agents/skills' / name / 'SKILL.md')
            text = target.read_text()
            self.assertTrue(text.startswith(f'---\nname: {name}\ndescription: '))
            self.assertEqual(text.split('---', 2)[1].count('description:'), 1)

    def test_mandatory_policy_and_skill_routing_remain_in_global_instructions(self):
        text = (REPO / 'agents/AGENTS.md').read_text()
        self.assertIn('≥7-day', text)
        self.assertIn('stop and ask for an explicit exception', text)
        self.assertIn('credentials and private data out of logs', text)
        for name in ['code-review', 'security-review', 'essayist']:
            self.assertIn(f'~/.agents/skills/{name}/SKILL.md', text)

    def test_missing_managed_skill_stops_before_installing_references(self):
        source = self.home / 'incomplete-checkout'
        (source / 'agents').mkdir(parents=True)
        (source / 'agents/AGENTS.md').write_text('fixture instructions\n')
        for name in ['code-review', 'security-review', 'essayist']:
            path = source / 'agents/skills' / name / 'SKILL.md'
            path.parent.mkdir(parents=True)
            path.write_text('fixture instructions\n')
        result = self.setup_agents(check=False, REPO_ROOT=str(source))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing managed skill file', result.stderr)
        self.assertFalse((self.home / '.agents').exists())
        self.assertFalse((self.pi / 'AGENTS.md').exists())

    def test_essayist_keeps_privacy_rules_and_a_working_writing_guide(self):
        root = REPO / 'agents/skills/essayist'
        text = (root / 'SKILL.md').read_text()
        self.assertIn('(./references/writing-guide.md)', text)
        self.assertIn('Ask permission before searching past sessions', text)
        self.assertIn('Do not publish or upload drafts unless explicitly requested', text)
        guide = (root / 'references/writing-guide.md').read_text()
        self.assertIn('Use anonymous placeholders', text)
        self.assertNotIn('```markdown', guide)
        self.assertIn('Extract the core facts', text)
        self.assertNotIn('Use anonymous placeholders', guide)
        self.assertEqual({str(path.relative_to(root)) for path in root.rglob('*') if path.is_file()},
                         {'SKILL.md', 'references/writing-guide.md'})

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
