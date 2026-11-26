"""The Linux app installer uses a fake curl: no network, no real downloads."""

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
WEZ_NAME = 'WezTerm-20990101-000000-abcdef12-Ubuntu20.04.AppImage'


def font_archive(member='JetBrainsMonoNerdFont-Regular.ttf'):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:xz') as archive:
        data = b'font'
        info = tarfile.TarInfo(member)
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class LinuxTerminalTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.tools = self.home / 'tools'
        self.web = self.home / 'web'
        self.tools.mkdir()
        self.web.mkdir()
        self.publish(b'wezterm-binary', font_archive())
        # Serves files by URL basename; release JSON by repository.
        curl = self.tools / 'curl'
        curl.write_text('''#!/bin/bash
set -eu
out=""; url=""
while [ $# -gt 0 ]; do
  case "$1" in -o) out="$2"; shift 2 ;; -*) shift ;; *) url="$1"; shift ;; esac
done
echo "$url" >> "$HOME/urls"
case "$url" in
  */repos/wezterm/wezterm/releases/latest) src="$HOME/web/wezterm.json" ;;
  */repos/ryanoasis/nerd-fonts/releases/latest) src="$HOME/web/fonts.json" ;;
  *) src="$HOME/web/$(basename "$url")" ;;
esac
if [ -n "$out" ]; then cp "$src" "$out"; else cat "$src"; fi
''')
        curl.chmod(0o755)
        for name, output in [('uname', '#!/bin/bash\nif [ "${1:-}" = -m ]; then echo x86_64; else echo "${TEST_OS:-Linux}"; fi\n'),
                             ('fc-cache', '#!/bin/bash\necho "$@" >> "$HOME/fc-cache"\n')]:
            path = self.tools / name
            path.write_text(output)
            path.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), XDG_DATA_HOME=str(self.home / 'data'),
                        PATH=str(self.tools) + os.pathsep + os.environ['PATH'])

    def publish(self, wezterm, font, wez_sum=None, prerelease=False):
        (self.web / WEZ_NAME).write_bytes(wezterm)
        (self.web / (WEZ_NAME + '.sha256')).write_text(
            f'{wez_sum or hashlib.sha256(wezterm).hexdigest()}  {WEZ_NAME}\n')
        (self.web / 'JetBrainsMono.tar.xz').write_bytes(font)
        (self.web / 'SHA-256.txt').write_text(
            f'{hashlib.sha256(font).hexdigest()}  JetBrainsMono.tar.xz\n{"0" * 64}  Other.tar.xz\n')
        base = 'https://example.invalid/'
        (self.web / 'wezterm.json').write_text(json.dumps({
            'tag_name': '20990101-000000-abcdef12', 'prerelease': prerelease, 'draft': False,
            'assets': [{'name': n, 'browser_download_url': base + n} for n in [WEZ_NAME, WEZ_NAME + '.sha256']]}))
        (self.web / 'fonts.json').write_text(json.dumps({
            'tag_name': 'v9.9.9', 'prerelease': False, 'draft': False,
            'assets': [{'name': n, 'browser_download_url': base + n}
                       for n in ['JetBrainsMono.tar.xz', 'SHA-256.txt']]}))

    def run_script(self, **env):
        return subprocess.run(['bash', str(REPO / 'scripts/linux-terminal.sh')],
                              env=dict(self.env, **env), capture_output=True, text=True)

    def test_installs_verified_latest_to_user_directories_and_is_repeatable(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        wezterm = self.home / '.local/bin/wezterm'
        self.assertEqual(wezterm.read_bytes(), b'wezterm-binary')
        self.assertTrue(os.access(wezterm, os.X_OK))
        font = self.home / 'data/fonts/JetBrainsMonoNerdFont/JetBrainsMonoNerdFont-Regular.ttf'
        self.assertEqual(font.read_bytes(), b'font')
        urls = (self.home / 'urls').read_text()
        (self.home / 'urls').unlink()
        again = self.run_script()
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn('already installed', again.stdout)
        self.assertNotIn(WEZ_NAME, (self.home / 'urls').read_text().replace('releases/latest', ''))
        self.assertIn('releases/latest', urls)

    def test_checksum_mismatch_installs_nothing(self):
        self.publish(b'wezterm-binary', font_archive(), wez_sum='0' * 64)
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('mismatch', result.stderr)
        self.assertFalse((self.home / '.local/bin/wezterm').exists())
        self.assertFalse((self.home / 'data/fonts').exists())

    def test_prerelease_is_not_installed(self):
        self.publish(b'wezterm-binary', font_archive(), prerelease=True)
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertFalse((self.home / '.local/bin/wezterm').exists())

    def test_unsafe_font_archive_is_rejected(self):
        self.publish(b'wezterm-binary', font_archive('../escape.ttf'))
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / 'data/fonts/JetBrainsMonoNerdFont').exists())
        self.assertFalse((self.home / 'data/escape.ttf').exists())

    def test_macos_does_nothing(self):
        result = self.run_script(TEST_OS='Darwin')
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.home / 'urls').exists())


if __name__ == '__main__':
    unittest.main()
