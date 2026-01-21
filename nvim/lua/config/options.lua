-- Options are automatically loaded before lazy.nvim startup
-- Default options that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
-- Add any additional options here
-- Don't use system clipboard by default (use <leader>tc for explicit sync)
-- Override LazyVim's default which auto-enables clipboard sync
vim.opt.clipboard = "" -- Keep yanks in vim registers only

-- Auto-reload files when changed on disk
vim.opt.autoread = true
