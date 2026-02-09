package cmd

import (
	"os"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/views"
	"github.com/spf13/cobra"
)

var (
	initExplain bool
	initPath    string
	initMarket  string
)

var initCmd = &cobra.Command{
	Use:   "init",
	Short: "Launch the onboarding wizard",
	Long: `Initialize a new Sigma-Quant Stream project.

The onboarding wizard guides you through:
  1. Welcome       -- logo and introduction
  2. Path Select   -- developer or trader
  3. Markets       -- futures, crypto-cex, crypto-dex
  4. API Keys      -- configure data source credentials
  5. Data Download -- download historical market data
  6. Health Check  -- validate system readiness
  7. Ready         -- summary and next steps

Use --explain for educational annotations at each step.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		// Resolve the project root (current working directory).
		projectRoot, err := os.Getwd()
		if err != nil {
			return err
		}

		return views.RunOnboarding(initExplain, projectRoot)
	},
}

func init() {
	initCmd.Flags().BoolVar(&initExplain, "explain", false, "enable educational annotations at each step")
	initCmd.Flags().StringVar(&initPath, "path", "", "user path: developer or trader")
	initCmd.Flags().StringVar(&initMarket, "market", "", "target market: futures, crypto-cex, or crypto-dex")
	rootCmd.AddCommand(initCmd)
}
