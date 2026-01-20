-- Autocmds are automatically loaded on the VeryLazy event
-- Default autocmds that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/autocmds.lua
--
-- Add any additional autocmds here
-- with `vim.api.nvim_create_autocmd`
--
-- Or remove existing autocmds by their group name (which is prefixed with `lazyvim_` for the defaults)
-- e.g. vim.api.nvim_del_augroup_by_name("lazyvim_wrap_spell")

-- Auto-reload files when changed externally
vim.api.nvim_create_autocmd({ "FocusGained", "BufEnter", "CursorHold", "CursorHoldI" }, {
  pattern = "*",
  callback = function()
    if vim.fn.mode() ~= "c" then
      vim.cmd("checktime")
    end
  end,
})

-- Periodically check for file changes (useful when external tools modify files)
-- This ensures files reload even without focus/cursor events
local timer = vim.loop.new_timer()
timer:start(
  1000, -- Start after 1 second
  1000, -- Check every 1 second
  vim.schedule_wrap(function()
    if vim.fn.mode() ~= "c" and vim.api.nvim_get_current_buf() ~= nil then
      vim.cmd("silent! checktime")
    end
  end)
)
