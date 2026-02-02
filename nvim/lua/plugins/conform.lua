return {
  "stevearc/conform.nvim",
  opts = {
    formatters_by_ft = {
      json = { "biome", "prettier" },
      jsonc = { "prettier" },
      javascript = { "prettier" },
      typescript = { "prettier" },
    },
  },
}
