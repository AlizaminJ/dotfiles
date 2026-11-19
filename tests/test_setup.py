"""Setup tests use fake installers."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class SetupTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.tools = self.home / 'tools'
        self.tools.mkdir()
        self.prefix = self.home / 'homebrew'
        self.script = self.home / 'prerequisites.sh'
        # Never discover the host's brew/uv.
        self.script.write_text((REPO / 'scripts/prerequisites.sh').read_text()
                               .replace('/opt/homebrew', str(self.prefix))
                               .replace('/usr/local', str(self.home / 'legacy')))
        self.env = dict(os.environ, HOME=str(self.home), TEST_TOOLS=str(self.tools),
                        TEST_PREFIX=str(self.prefix), PATH=str(self.tools) + os.pathsep + os.defpath)
        self.mock('uname', 'echo "${TEST_OS:-Darwin}"\n')
        self.mock('curl', '''echo curl >> "$HOME/calls"
[[ "$*" == '-fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh' ]]
[[ "${FETCH_FAIL:-0}" == 0 ]] || exit 7
printf '%s\n' 'mkdir -p "$TEST_PREFIX/bin"; cp "$TEST_TOOLS/brew-template" "$TEST_PREFIX/bin/brew"'
''')
        self.mock('brew-template', '''{ printf 'brew'; printf '|%s' "$@"; printf '\\n'; } >> "$HOME/calls"
if [[ "$*" == 'install uv' ]]; then
  [[ "${UV_INSTALL_EXIT:-0}" == 0 ]] || exit "$UV_INSTALL_EXIT"
  cp "$TEST_TOOLS/uv-template" "$TEST_PREFIX/bin/uv"
fi
''')
        self.mock('uv-template', '''echo "uv|$*" >> "$HOME/calls"
[[ "$*" == 'python install --default' ]] || exit 2
[[ "${PYTHON_INSTALL_EXIT:-0}" == 0 ]] || exit "$PYTHON_INSTALL_EXIT"
''')

    def mock(self, name, body):
        path = self.tools / name
        path.write_text('#!/bin/bash\nset -euo pipefail\n' + body)
        path.chmod(0o755)
        return path

    def run_setup(self, **env):
        return subprocess.run(['/bin/bash', str(self.script)], env=dict(self.env, **env),
                              capture_output=True, text=True)

    def calls(self):
        path = self.home / 'calls'
        return path.read_text().splitlines() if path.exists() else []

    def install_fake_tools(self):
        (self.prefix / 'bin').mkdir(parents=True)
        for name in ['brew', 'uv']:
            shutil.copy2(self.tools / (name + '-template'), self.prefix / 'bin' / name)

    def test_fresh_setup_uses_standard_homebrew_uv_python_chain(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls(), ['curl', 'brew|install|uv', 'uv|python install --default'])
        self.assertFalse((self.home / '.config').exists())  # Development defaults are a later step.

    def test_repeat_run_reuses_brew_and_uv(self):
        self.assertEqual(self.run_setup().returncode, 0)
        (self.home / 'calls').unlink()
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), ['uv|python install --default'])

    def test_failed_installer_download_stops_before_execution(self):
        result = self.run_setup(FETCH_FAIL='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), ['curl'])
        self.assertFalse(self.prefix.exists())

    def test_uv_failure_stops_before_python_installation(self):
        result = self.run_setup(UV_INSTALL_EXIT='8')
        self.assertEqual(result.returncode, 8)
        self.assertEqual(self.calls(), ['curl', 'brew|install|uv'])

    def test_bootstrap_passes_new_tools_to_later_steps(self):
        checkout = self.home / 'repo with spaces'
        scripts = checkout / 'scripts'
        scripts.mkdir(parents=True)
        bootstrap = checkout / 'bootstrap.sh'
        bootstrap.write_text((REPO / 'bootstrap.sh').read_text()
                             .replace('/opt/homebrew', str(self.prefix))
                             .replace('/usr/local', str(self.home / 'legacy')))
        shutil.copy2(self.script, scripts / 'prerequisites.sh')
        (scripts / 'config.sh').write_text('set -euo pipefail\n')
        self.mock('python-template', 'exit 0\n')
        with (self.tools / 'uv-template').open('a') as stream:
            stream.write('mkdir -p "$HOME/.local/bin"\n'
                         'cp "$TEST_TOOLS/python-template" "$HOME/.local/bin/python3"\n')
        steps = ['agents', 'homebrew', 'pnpm', 'uv', 'editors', 'shell-plugins',
                 'shell', 'macos-defaults', 'ssh-keys', 'git-ssh']
        for step in steps:
            path = scripts / (step + '.sh')
            path.write_text('#!/bin/bash\nset -euo pipefail\n'
                            '[[ "$(command -v brew)" == "$TEST_PREFIX/bin/brew" ]]\n'
                            '[[ "$(command -v uv)" == "$TEST_PREFIX/bin/uv" ]]\n'
                            '[[ "$(command -v python3)" == "$HOME/.local/bin/python3" ]]\n'
                            f'echo {step} >> "$HOME/calls"\n')
            path.chmod(0o755)
        result = subprocess.run(['/bin/bash', str(bootstrap)], env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls(), ['curl', 'brew|install|uv', 'uv|python install --default', *steps])

    def test_python_failure_propagates_without_retry_or_fallback(self):
        self.install_fake_tools()
        result = self.run_setup(PYTHON_INSTALL_EXIT='9')
        self.assertEqual(result.returncode, 9)
        self.assertEqual(self.calls(), ['uv|python install --default'])

    def test_non_macos_does_not_run_installers(self):
        self.assertNotEqual(self.run_setup(TEST_OS='Linux').returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_brewfile_uses_normal_bundle_without_age_or_upgrade_flags(self):
        self.install_fake_tools()
        checkout = self.home / 'repo with spaces'
        checkout.mkdir()
        env = dict(self.env, REPO_ROOT=str(checkout),
                   PATH=str(self.prefix / 'bin') + os.pathsep + self.env['PATH'])
        result = subprocess.run(['/bin/bash', str(REPO / 'scripts/homebrew.sh')], env=env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls(), [f'brew|bundle|--file={checkout}/Brewfile'])

    def test_bootstrap_installs_before_configuring_development_defaults(self):
        text = (REPO / 'bootstrap.sh').read_text()
        self.assertLess(text.index('scripts/prerequisites.sh'), text.index('scripts/homebrew.sh'))
        self.assertLess(text.index('scripts/homebrew.sh'), text.index('scripts/pnpm.sh'))
        self.assertLess(text.index('scripts/homebrew.sh'), text.index('scripts/uv.sh'))
        self.assertNotIn('verify-wezterm', text)


if __name__ == '__main__':
    unittest.main()
