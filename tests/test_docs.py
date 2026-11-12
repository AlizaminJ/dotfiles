"""Keep onboarding links and documented task names aligned with the checkout."""

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from urllib.parse import unquote, urlsplit


REPO = Path(__file__).resolve().parents[1]
DOCUMENTS = [REPO / 'README.md', *sorted((REPO / 'docs').glob('*.md')), REPO / 'nvim/README.md']


class DocumentationTest(unittest.TestCase):
    def test_relative_links_and_heading_anchors_exist(self):
        for document in DOCUMENTS:
            for target in re.findall(r'\]\(([^)]+)\)', document.read_text()):
                link = urlsplit(target)
                if link.scheme or link.netloc:
                    continue
                destination = document.parent / unquote(link.path) if link.path else document
                with self.subTest(document=str(document.relative_to(REPO)), target=target):
                    self.assertTrue(destination.exists(), 'Broken local documentation link')
                    if link.fragment and destination.suffix == '.md':
                        headings = re.findall(r'^#{1,6}\s+(.+)$', destination.read_text(), re.MULTILINE)
                        anchors = [re.sub(r'[^\w -]', '', heading.lower()).replace(' ', '-') for heading in headings]
                        self.assertIn(unquote(link.fragment), anchors)

    def test_documented_tasks_accept_dry_run_without_local_setup(self):
        commands = set()
        for document in DOCUMENTS:
            commands.update(re.findall(r'(?:^|`)(?:\./bin/)?dotfiles[ \t]+(?:--dry-run[ \t]+)?([a-z][a-z-]*)',
                                       document.read_text(), re.MULTILINE))
        self.assertTrue(commands, 'No documented commands were checked')
        with tempfile.TemporaryDirectory() as home:
            for command in sorted(commands):
                with self.subTest(command=command):
                    result = subprocess.run([str(REPO / 'bin/dotfiles'), '--dry-run', command], cwd=home,
                                            env={'HOME': home, 'PATH': os.defpath}, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(Path(home).iterdir()), [], 'Documentation previews must not configure anything')


if __name__ == '__main__':
    unittest.main()
