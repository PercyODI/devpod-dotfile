return {
  {
    "mason-org/mason.nvim",
    opts = {
      ensure_installed = {
        "typescript-language-server", -- TypeScript/JavaScript LSP
        "eslint_d", -- JavaScript/TypeScript linter
        "prettier", -- Code formatter
        "biome", -- JSON LSP
      },
    },
  },
}
