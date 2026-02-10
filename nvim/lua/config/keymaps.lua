-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here
-- Use jk to escape insert mode
vim.keymap.set("i", "jk", "<Esc>", { noremap = true, silent = true })

-- Tmux copy/paste integration
-- Copy visual selection to tmux buffer and send to system clipboard via OSC 52
vim.keymap.set("v", "<leader>yc", function()
  -- Yank to register 0
  vim.cmd("normal! y")
  local content = vim.fn.getreg("0")
  -- Load into tmux buffer
  vim.fn.system("tmux load-buffer -", content)
  -- Send OSC 52 sequence to sync with system clipboard
  local osc52 = require("vim.ui.clipboard.osc52")
  local lines = vim.split(content, "\n")
  osc52.copy("+")(lines)
end, { noremap = true, desc = "Copy to tmux/system clipboard" })
-- Paste from tmux buffer
vim.keymap.set(
  "n",
  "<leader>yp",
  ':let @0 = system("tmux save-buffer -")<cr>"0p<cr>g;',
  { noremap = true, desc = "Paste from tmux buffer" }
)

-- Keybinding for moving buffers in their buffer line
vim.keymap.set("n", "<leader>bH", "<cmd>BufferLineMovePrev<CR>", { desc = "Move buffer left" })
vim.keymap.set("n", "<leader>bL", "<cmd>BufferLineMoveNext<CR>", { desc = "Move buffer right" })

-- Git hunk diff quit - closes the diff view without landing in the old buffer
vim.keymap.set("n", "<leader>ghq", function()
  local current_win = vim.api.nvim_get_current_win()
  local wins = vim.api.nvim_list_wins()

  -- Find and close gitsigns diff window
  for _, win in ipairs(wins) do
    local buf = vim.api.nvim_win_get_buf(win)
    local bufname = vim.api.nvim_buf_get_name(buf)

    -- Check if this is a gitsigns diff buffer (contains "gitsigns://" or is a git object)
    if bufname:match("gitsigns://") or bufname:match("%.git/") then
      vim.api.nvim_win_close(win, false)
      return
    end
  end

  -- Fallback: if there are exactly 2 windows, close the other one
  if #wins == 2 then
    for _, win in ipairs(wins) do
      if win ~= current_win then
        vim.api.nvim_win_close(win, false)
        return
      end
    end
  end

  vim.notify("No git diff window found", vim.log.levels.WARN)
end, { desc = "Quit git hunk diff view" })
