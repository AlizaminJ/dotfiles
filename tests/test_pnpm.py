"""Configure pnpm defaults without calling a real installer or registry."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class PnpmPreferencesTest(unittest.TestCase):
    def test_defaults_backups_and_repeat_run_preserve_unrelated_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            tools = home / 'bin'
            tools.mkdir()
            config = home / 'pnpm preferences.json'
            original = {'fetchRetries': 3, 'ignoreScripts': False}
            config.write_text(json.dumps(original))
            mock = tools / 'pnpm'
            mock.write_text(f'#!{sys.executable}\n' + '''import json, os, pathlib, sys
args = sys.argv[1:]
config = pathlib.Path(os.environ['MOCK_PNPM_CONFIG'])
if args == ['--version']:
    print('12.16.1')
    sys.exit(0)
assert args[0] == 'config' and '--global' in args
args = [arg for arg in args if arg not in ('--global', '--json')]
values = json.loads(config.read_text())
if args[1] == 'get':
    if args[2] == 'globalconfig': print(config)
    elif args[2] not in values: print('undefined')
    else: print(json.dumps(values[args[2]]))
elif args[1] == 'set':
    values[args[2]] = json.loads(args[3])
    config.write_text(json.dumps(values, sort_keys=True))
else: sys.exit(2)
''')
            mock.chmod(0o755)
            env = dict(os.environ, HOME=directory, MOCK_PNPM_CONFIG=str(config),
                       PATH=str(tools) + os.pathsep + os.environ['PATH'])
            command = ['bash', str(REPO / 'scripts/pnpm.sh')]
            subprocess.run(command, env=env, check=True, capture_output=True)
            self.assertEqual(json.loads(Path(str(config) + '.bak').read_text()), original)
            values = json.loads(config.read_text())
            self.assertEqual(values, dict(fetchRetries=3, ignoreScripts=True, minimumReleaseAge=10080,
                                         minimumReleaseAgeStrict=True, minimumReleaseAgeIgnoreMissingTime=False,
                                         trustLockfile=False))
            before = config.read_bytes(), config.stat().st_mtime_ns
            subprocess.run(command, env=env, check=True, capture_output=True)
            self.assertEqual(before, (config.read_bytes(), config.stat().st_mtime_ns))
            self.assertFalse(Path(str(config) + '.bak.1').exists())


if __name__ == '__main__':
    unittest.main()
