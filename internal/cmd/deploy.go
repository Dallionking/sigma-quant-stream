package cmd

import (
	"fmt"

	"github.com/Dallionking/sigma-quant-stream/internal/config"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
	"github.com/spf13/cobra"
)

var (
	deployExchange string
	deployDryRun   bool
)

var deployCmd = &cobra.Command{
	Use:   "deploy <strategy>",
	Short: "Deploy a strategy to Freqtrade",
	Long: `Export and deploy a validated strategy to a Freqtrade instance.

The deployment process:
  1. Converts the strategy to Freqtrade IStrategy format
  2. Generates an exchange-specific config file
  3. Outputs the command to launch Freqtrade

By default, strategies are deployed in dry-run (paper trading) mode.
Use --dry-run=false for live deployment.`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		strategyArg := args[0]

		root, err := config.DetectProjectRoot()
		if err != nil {
			return fmt.Errorf("detecting project root: %w", err)
		}

		if _, err := config.Load(root); err != nil {
			return fmt.Errorf("loading config: %w", err)
		}

		fmt.Println(styles.Title.Render("Deploy to Freqtrade"))
		fmt.Println()

		fmt.Println(styles.Label.Render("STRATEGY") + "  " + styles.Value.Render(strategyArg))
		fmt.Println(styles.Label.Render("EXCHANGE") + "  " + styles.Value.Render(deployExchange))

		modeLabel := styles.Green("dry-run (paper)")
		if !deployDryRun {
			modeLabel = styles.Red("LIVE")
		}
		fmt.Println(styles.Label.Render("MODE") + "      " + modeLabel)
		fmt.Println()

		fmt.Println(styles.Divider(60))
		fmt.Println()

		// TODO: Wire to python.DeployToFreqtrade when Runner is available.
		// The deployment pipeline will:
		//   runner, err := python.NewRunner(root)
		//   result, err := runner.DeployToFreqtrade(ctx, python.DeployOptions{
		//       StrategyFile: strategyArg,
		//       Exchange:     deployExchange,
		//       DryRun:       deployDryRun,
		//   })

		fmt.Println(styles.Panel.Width(60).Render(
			styles.Cyan("Step 1") + "  Convert to IStrategy format\n" +
				styles.Cyan("Step 2") + "  Generate exchange config\n" +
				styles.Cyan("Step 3") + "  Validate deployment package\n" +
				styles.Cyan("Step 4") + "  Output launch command",
		))
		fmt.Println()
		fmt.Println(styles.Dim("Deployment pipeline placeholder -- will invoke python.DeployToFreqtrade"))

		return nil
	},
}

func init() {
	deployCmd.Flags().StringVar(&deployExchange, "exchange", "binance", "target exchange: binance, bybit, or okx")
	deployCmd.Flags().BoolVar(&deployDryRun, "dry-run", true, "deploy in paper trading mode (default: true)")
	rootCmd.AddCommand(deployCmd)
}
