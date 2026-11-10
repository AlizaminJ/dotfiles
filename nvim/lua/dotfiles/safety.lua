local M = {}

-- Keep a fresh editor usable without fetching unreviewed plugins or running builds.
function M.plugins_ready()
  local function stop(message)
    vim.notify(message .. ' See nvim/README.md.', vim.log.levels.WARN)
    return false
  end
  if not (vim.pack and vim.pack.add) then return stop('This config needs Neovim with vim.pack.') end

  local ok, lock = pcall(function()
    local path = vim.fn.stdpath('config') .. '/nvim-pack-lock.json'
    return vim.json.decode(table.concat(vim.fn.readfile(path), '\n'))
  end)
  if not ok or type(lock) ~= 'table' or type(lock.plugins) ~= 'table' or next(lock.plugins) == nil then
    return stop('Plugin lockfile is missing or invalid; using core editor settings only.')
  end

  local root = vim.fn.stdpath('data') .. '/site/pack/core/opt/'
  for name, plugin in pairs(lock.plugins) do
    if type(name) ~= 'string' or name == '.' or name == '..' or not name:match('^[%w._-]+$') or
        type(plugin) ~= 'table' or type(plugin.src) ~= 'string' or type(plugin.rev) ~= 'string' or not plugin.rev:match('^%x+$') or
        (#plugin.rev ~= 40 and #plugin.rev ~= 64) or vim.fn.getftype(root .. name) ~= 'dir' then
      return stop('Plugin bootstrap is disabled; using core editor settings only.')
    end
  end

  local function origin(src)
    return src:gsub('^ssh://git@github.com/', 'https://github.com/')
      :gsub('^git@github.com:', 'https://github.com/'):gsub('/$', ''):gsub('%.git$', '')
  end
  local add = vim.pack.add
  vim.pack.add = function(specs, opts)
    local existing = {}
    for _, spec in ipairs(specs) do
      local src = type(spec) == 'string' and spec or spec.src
      local name = type(spec) == 'table' and spec.name or nil
      name = name or src:gsub('/$', ''):match('([^/]+)$'):gsub('%.git$', '')
      local pinned = lock.plugins[name]
      if not pinned or origin(src) ~= origin(pinned.src) or vim.fn.getftype(root .. name) ~= 'dir' then
        error('Plugin installation requires source/age review first. See nvim/README.md.')
      end
      local resolved = type(spec) == 'table' and vim.tbl_extend('force', {}, spec) or {}
      resolved.src = pinned.src
      existing[#existing + 1] = resolved
    end
    return add(existing, opts)
  end
  return true
end

return M
