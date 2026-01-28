-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here
-- Use jk to escape insert mode
vim.keymap.set("i", "jk", "<Esc>", { noremap = true, silent = true })

-- Tmux copy/paste integration
-- Copy visual selection to tmux buffer and send to system clipboard via OSC 52
vim.keymap.set("v", "<leader>tc", function()
  -- Yank to register 0
  vim.cmd("normal! y")
  local content = vim.fn.getreg("0")
  -- Load into tmux buffer
  vim.fn.system("tmux load-buffer -", content)
  -- Send OSC 52 sequence to sync with system clipboard
  local osc52 = require("vim.ui.clipboard.osc52")
  local lines = vim.split(content, "\n")
  osc52.copy("+")(lines)
  -- Restore visual selection
  vim.cmd("normal! gv")
end, { noremap = true, desc = "Copy to tmux/system clipboard" })
-- Paste from tmux buffer
vim.keymap.set(
  "n",
  "<leader>tp",
  ':let @0 = system("tmux save-buffer -")<cr>"0p<cr>g;',
  { noremap = true, desc = "Paste from tmux buffer" }
)
