"""Record preference writes without changing macOS settings or restarting apps."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class MacOSDefaultsTest(unittest.TestCase):
    def test_preferences_are_repeatable_without_real_defaults_or_killall(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            bin_dir = home / 'bin'
            bin_dir.mkdir()
            defaults = bin_dir / 'defaults'
            defaults.write_text(f'#!{sys.executable}\n' + '''import json, os, pathlib, sys
args = sys.argv[1:]
assert args[0] == 'write', args
assert len(args) == 5, args
state = pathlib.Path(os.environ['HOME']) / 'preferences.json'
values = json.loads(state.read_text()) if state.exists() else {}
values[args[1] + '/' + args[2]] = args[3:]
state.write_text(json.dumps(values, sort_keys=True))
''')
            killall = bin_dir / 'killall'
            killall.write_text(f'#!{sys.executable}\n' + '''import os, pathlib, sys
with (pathlib.Path(os.environ['HOME']) / 'restarts.txt').open('a') as log:
    log.write(' '.join(sys.argv[1:]) + '\\n')
''')
            uname = bin_dir / 'uname'
            uname.write_text('#!/bin/bash\necho "${TEST_OS:-Darwin}"\n')
            defaults.chmod(0o755)
            uname.chmod(0o755)
            killall.chmod(0o755)
            env = dict(os.environ, HOME=directory, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'])
            command = ['bash', str(REPO / 'scripts/macos-defaults.sh')]
            subprocess.run(command, env=env, check=True, capture_output=True)
            before = (home / 'preferences.json').read_bytes()
            subprocess.run(command, env=env, check=True, capture_output=True)
            self.assertEqual(before, (home / 'preferences.json').read_bytes())
            values = json.loads(before)
            expected = {
                'NSGlobalDomain/AppleShowAllExtensions': ['-bool', 'true'],
                'com.apple.finder/ShowPathbar': ['-bool', 'true'],
                'com.apple.finder/ShowStatusBar': ['-bool', 'true'],
                'NSGlobalDomain/NSAutomaticQuoteSubstitutionEnabled': ['-bool', 'false'],
                'NSGlobalDomain/NSAutomaticDashSubstitutionEnabled': ['-bool', 'false'],
                'com.apple.finder/AppleShowAllFiles': ['-bool', 'true'],
                'NSGlobalDomain/KeyRepeat': ['-int', '2'],
                'NSGlobalDomain/InitialKeyRepeat': ['-int', '15'],
                'com.apple.dock/autohide': ['-bool', 'true'],
                'com.apple.screencapture/location': ['-string', str(home / 'Screenshots')],
            }
            self.assertEqual(values, expected)
            self.assertTrue((home / 'Screenshots').is_dir())
            self.assertEqual((home / 'restarts.txt').read_text().splitlines(), ['Finder', 'Dock'] * 2)

            (home / 'preferences.json').unlink()
            result = subprocess.run(command, env=dict(env, TEST_OS='Linux'), check=True, capture_output=True, text=True)
            self.assertIn('skipped', result.stdout)
            self.assertFalse((home / 'preferences.json').exists())


if __name__ == '__main__':
    unittest.main()
