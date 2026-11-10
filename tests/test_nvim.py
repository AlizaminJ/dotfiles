"""A fresh editor must not fetch plugins, tools, or parser builds on startup."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class NeovimSafetyTest(unittest.TestCase):
    def test_automatic_install_paths_stay_disabled(self):
        config = (REPO / 'nvim/init.lua').read_text()
        self.assertIn("if not require('dotfiles.safety').plugins_ready() then return end", config)
        self.assertIn('run_on_start = false, auto_update = false', config)
        for automatic in ["require('nvim-treesitter').install", "vim.cmd 'TSUpdate'", 'run_build(']:
            self.assertNotIn(automatic, config)
        debug = (REPO / 'nvim/lua/kickstart/plugins/debug.lua').read_text()
        self.assertIn('automatic_installation = false', debug)
        self.assertIn('ensure_installed = {}', debug)

    @unittest.skipUnless(shutil.which('luajit'), 'LuaJIT unavailable')
    def test_plugin_guard_blocks_missing_unlocked_and_invalid_plugins(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = Path(directory) / 'check.lua'
            runner.write_text('''local mode = arg[2]
local calls = 0
local lock = { plugins = { known = { rev = string.rep('a', 40), src = 'ssh://git@github.com/example/known' } } }
if mode == 'invalid-revision' then lock.plugins.known.rev = 'floating' end
vim = {
  pack = { add = function() calls = calls + 1 end },
  fn = {
    stdpath = function(kind) return '/fixture/' .. kind end,
    readfile = function() if mode == 'invalid-lock' then error('bad lock') end; return {} end,
    getftype = function() return mode == 'missing' and '' or mode == 'symlink' and 'link' or 'dir' end,
  },
  json = { decode = function() return lock end },
  log = { levels = { WARN = 1 } },
  notify = function() end,
}
local ready = assert(loadfile(arg[1]))().plugins_ready()
if mode ~= 'ready' then
  assert(ready == false)
  assert(calls == 0)
  return
end
assert(ready == true)
vim.pack.add { 'https://github.com/example/known' }
assert(calls == 1)
assert(not pcall(vim.pack.add, { 'https://github.com/example/unreviewed' }))
assert(not pcall(vim.pack.add, { 'https://github.com/unreviewed/known' }))
assert(calls == 1)
''')
            for mode in ['missing', 'symlink', 'invalid-lock', 'invalid-revision', 'ready']:
                subprocess.run(['luajit', str(runner), str(REPO / 'nvim/lua/dotfiles/safety.lua'), mode], check=True)

    @unittest.skipUnless(shutil.which('nvim'), 'Neovim unavailable')
    def test_fresh_editor_keeps_core_settings_without_git_or_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / '.config').mkdir()
            (home / '.config/nvim').symlink_to(REPO / 'nvim')
            tools = home / 'bin'
            tools.mkdir()
            git = tools / 'git'
            git.write_text('#!/bin/bash\ntouch "$HOME/git-was-called"\nexit 99\n')
            git.chmod(0o755)
            env = dict(os.environ, HOME=directory, XDG_CONFIG_HOME=str(home / '.config'),
                       XDG_DATA_HOME=str(home / '.local/share'), XDG_CACHE_HOME=str(home / '.cache'),
                       XDG_STATE_HOME=str(home / '.local/state'), XDG_CONFIG_DIRS=str(home / 'empty'),
                       XDG_DATA_DIRS=str(home / 'empty'), NVIM_APPNAME='nvim',
                       PATH=str(tools) + os.pathsep + os.environ['PATH'])
            result = subprocess.run([shutil.which('nvim'), '--headless', '-u', str(REPO / 'nvim/init.lua'), '+qa!'],
                                    env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Plugin bootstrap is disabled', result.stderr)
            self.assertFalse((home / 'git-was-called').exists())
            self.assertFalse((home / '.local/share/nvim/site/pack').exists())


if __name__ == '__main__':
    unittest.main()
