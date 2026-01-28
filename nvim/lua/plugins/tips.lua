return {
  "folke/snacks.nvim",
  opts = function(_, opts)
    -- Initialize random seed
    math.randomseed(os.time())

    -- Function to load tips from JSON file
    local function load_tips()
      local tips_file = vim.fn.stdpath("config") .. "/tips.json"
      local file = io.open(tips_file, "r")

      if not file then
        return {
          tips = {
            {
              title = "Tips System Error",
              description = "Could not load tips.json file.\n\nPlease ensure the file exists at: " .. tips_file,
            },
          },
        }
      end

      local content = file:read("*all")
      file:close()

      local success, data = pcall(vim.fn.json_decode, content)
      if not success or not data or not data.tips then
        return {
          tips = {
            {
              title = "Tips System Error",
              description = "Failed to parse tips.json file.\n\nPlease check the JSON syntax.",
            },
          },
        }
      end

      return data
    end

    -- Function to show a random tip
    local function show_tip()
      local data = load_tips()
      local tips = data.tips

      if not tips or #tips == 0 then
        vim.notify("No tips available", vim.log.levels.WARN)
        return
      end

      -- Select random starting tip
      local current_index = math.random(1, #tips)

      -- Create buffer
      local buf = vim.api.nvim_create_buf(false, true)
      vim.api.nvim_buf_set_option(buf, "filetype", "markdown")
      vim.api.nvim_buf_set_option(buf, "modifiable", true)

      -- Function to render a tip by index
      -- Variable to hold the window object
      local win
      local win_id

      local function render_tip(index)
        local tip = tips[index]

        -- Format the tip content (just the description)
        local content = tip.description

        -- Split content into lines and add empty line at the top for cursor
        local lines = vim.split(content, "\n")
        table.insert(lines, 1, "")

        -- Update buffer content
        vim.api.nvim_buf_set_option(buf, "modifiable", true)
        vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
        vim.api.nvim_buf_set_option(buf, "modifiable", false)

        -- Position cursor on the empty first line
        if win_id and vim.api.nvim_win_is_valid(win_id) then
          vim.api.nvim_win_set_cursor(win_id, { 1, 0 })
        end

        -- Update window title if window exists
        if win_id and vim.api.nvim_win_is_valid(win_id) then
          local config = vim.api.nvim_win_get_config(win_id)
          config.title = { { " " .. tip.title .. " ", "FloatTitle" } }
          vim.api.nvim_win_set_config(win_id, config)
        end

        -- Calculate window dimensions based on content
        local max_width = 80
        local longest_line = 0
        for _, line in ipairs(lines) do
          local display_len = vim.fn.strdisplaywidth(line)
          if display_len > longest_line then
            longest_line = display_len
          end
        end

        -- Set width: use content width but cap at max_width, minimum 40
        local width = math.min(math.max(longest_line + 4, 40), max_width)
        -- Set height: use line count + 2 for padding
        local height = #lines + 2

        return width, height, tip.title
      end

      -- Render initial tip
      local width, height, title = render_tip(current_index)

      -- Display in snacks window
      local snacks = require("snacks")
      win = snacks.win({
        buf = buf,
        width = width,
        height = height,
        border = "rounded",
        title = " " .. title .. " ",
        footer = " [j] Next  [k] Previous  [q] Close ",
        wo = {
          conceallevel = 3,
          wrap = true,
        },
        keys = {
          q = "close",
          ["<Esc>"] = "close",
          j = function()
            -- Next tip (cycle forward)
            current_index = current_index % #tips + 1
            render_tip(current_index)
          end,
          k = function()
            -- Previous tip (cycle backward)
            current_index = current_index - 1
            if current_index < 1 then
              current_index = #tips
            end
            render_tip(current_index)
          end,
        },
        backdrop = 60,
      })

      -- Store the window ID for title updates
      win_id = win.win
    end

    -- Create user command
    vim.api.nvim_create_user_command("Tip", show_tip, {
      desc = "Show a random LazyVim tip",
    })

    -- Show tip on startup with delay
    vim.api.nvim_create_autocmd("VimEnter", {
      callback = function()
        vim.defer_fn(show_tip, 100)
      end,
      desc = "Show random tip on startup",
    })

    return opts
  end,
}
