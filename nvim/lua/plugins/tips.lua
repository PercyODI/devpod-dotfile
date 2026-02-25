return {
  "folke/snacks.nvim",
  opts = function(_, opts)
    -- Function to load tips from JSON file
    local function load_tips()
      local tips_file = vim.fn.stdpath("config") .. "/tips.json"
      local file = io.open(tips_file, "r")

      if not file then
        return {
          {
            title = "Tips System Error",
            description = "Could not load tips.json file.\n\nPlease ensure the file exists at: " .. tips_file,
          },
        }
      end

      local content = file:read("*all")
      file:close()

      local success, data = pcall(vim.fn.json_decode, content)
      if not success or not data or not data.tips then
        return {
          {
            title = "Tips System Error",
            description = "Failed to parse tips.json file.\n\nPlease check the JSON syntax.",
          },
        }
      end

      return data.tips
    end

    -- Create user command that opens tips picker
    vim.api.nvim_create_user_command("Tip", function()
      local tips = load_tips()
      local items = {}

      for _, tip in ipairs(tips) do
        table.insert(items, {
          text = tip.title .. " " .. tip.description,
          display_text = tip.title,
          preview = {
            text = tip.description,
            ft = "markdown",
          },
        })
      end

      local Snacks = require("snacks")
      Snacks.picker({
        -- prompt = "LazyVim Tips",
        items = items,
        layout = { preset = "default" },
        preview = "preview",
        win = {
          preview = {
            wo = {
              wrap = true,
            },
          },
        },
        format = function(item)
          return { { item.display_text or item.text, "SnacksPickerLabel" } }
        end,
        confirm = function(picker)
          picker:close()
        end,
      })
    end, {
      desc = "Show tips picker",
    })

    return opts
  end,
}
