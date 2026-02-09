package cmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/Dallionking/sigma-quant-stream/internal/config"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/views"
)

var tutorialStep int

var tutorialCmd = &cobra.Command{
	Use:   "tutorial",
	Short: "Launch the interactive tutorial",
	Long: `Walk through a 6-step guided tutorial covering the full
Sigma-Quant Stream workflow.

Use --step to jump directly to a specific step (1-6).`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if tutorialStep < 0 || tutorialStep > 6 {
			return fmt.Errorf("step must be between 1 and 6 (got %d)", tutorialStep)
		}

		root, err := config.DetectProjectRoot()
		if err != nil {
			return fmt.Errorf("detecting project root: %w", err)
		}

		// --step is 1-indexed for the user, but the model is 0-indexed.
		startStep := 0
		if tutorialStep > 0 {
			startStep = tutorialStep - 1
		}

		return views.RunTutorial(startStep, root)
	},
}

func init() {
	tutorialCmd.Flags().IntVar(&tutorialStep, "step", 0, "jump to a specific step (1-6)")
	rootCmd.AddCommand(tutorialCmd)
}
