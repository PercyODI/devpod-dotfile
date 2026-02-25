return {
  "mfussenegger/nvim-dap",
  keys = {
    {
      "<C-j>",
      function()
        require("dap").step_over()
      end,
      desc = "Step Over",
    },
  },
}
