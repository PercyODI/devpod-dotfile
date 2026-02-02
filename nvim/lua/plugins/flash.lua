return {
  "folke/flash.nvim",
  opts = {
    modes = {
      char = {
        -- Disable the default f, F, t, T keys so they work normally
        -- This allows commands like 3df; to work as expected
        enabled = false,
      },
    },
  },
  keys = {
    -- Disable default LazyVim flash keymaps
    { "s", false },
    { "S", false },

    -- Flash keymaps using <leader>j prefix (j for jump)
    {
      "<leader>jj",
      mode = { "n", "x", "o" },
      function()
        require("flash").jump()
      end,
      desc = "Flash Jump",
    },
    {
      "<leader>js",
      mode = { "n", "x", "o" },
      function()
        require("flash").jump()
      end,
      desc = "Flash Search",
    },
    {
      "<leader>jS",
      mode = { "n", "x", "o" },
      function()
        require("flash").treesitter()
      end,
      desc = "Flash Treesitter",
    },

    -- Flash-enhanced f/t/F/T motions with <leader>j prefix
    -- Press <leader>jf, then type a character, and flash will show labels for all matches
    {
      "<leader>jf",
      mode = { "n", "x", "o" },
      function()
        local char = vim.fn.getcharstr()
        if char == "" or char == "\27" then -- Empty or ESC
          return
        end
        require("flash").jump({
          search = { mode = "search", forward = true, wrap = false, multi_line = true },
          pattern = vim.pesc(char),
          label = { after = { 0, 0 } },
        })
      end,
      desc = "Flash forward to char",
    },
    {
      "<leader>jF",
      mode = { "n", "x", "o" },
      function()
        local char = vim.fn.getcharstr()
        if char == "" or char == "\27" then
          return
        end
        require("flash").jump({
          search = { mode = "search", forward = false, wrap = false, multi_line = true },
          pattern = vim.pesc(char),
          label = { after = { 0, 0 } },
        })
      end,
      desc = "Flash backward to char",
    },
    {
      "<leader>jt",
      mode = { "n", "x", "o" },
      function()
        local char = vim.fn.getcharstr()
        if char == "" or char == "\27" then
          return
        end
        require("flash").jump({
          search = { mode = "search", forward = true, wrap = false, multi_line = true },
          pattern = vim.pesc(char),
          jump = { pos = "start", offset = -1 },
          label = { after = { 0, 0 } },
        })
      end,
      desc = "Flash forward till char",
    },
    {
      "<leader>jT",
      mode = { "n", "x", "o" },
      function()
        local char = vim.fn.getcharstr()
        if char == "" or char == "\27" then
          return
        end
        require("flash").jump({
          search = { mode = "search", forward = false, wrap = false, multi_line = true },
          pattern = vim.pesc(char),
          jump = { pos = "start", offset = 1 },
          label = { after = { 0, 0 } },
        })
      end,
      desc = "Flash backward till char",
    },
  },
}
