package cmd

import (
	"fmt"

	"github.com/Dallionking/sigma-quant-stream/internal/config"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/views"
	"github.com/spf13/cobra"
)

var setupClaudeCmd = &cobra.Command{
	Use:   "setup-claude",
	Short: "Set up Claude Code agent team",
	Long: `Configure the Claude Code agent team for your project.

This interactive wizard will:
  1. Check prerequisites (Claude CLI, tmux)
  2. Configure .claude/settings.json
  3. Choose terminal layout (tmux / iTerm2 / Manual)
  4. Run an optional smoke test`,
	RunE: func(cmd *cobra.Command, args []string) error {
		root, err := config.DetectProjectRoot()
		if err != nil {
			return fmt.Errorf("detecting project root: %w", err)
		}

		return views.RunSetupClaude(root)
	},
}

func init() {
	rootCmd.AddCommand(setupClaudeCmd)
}
