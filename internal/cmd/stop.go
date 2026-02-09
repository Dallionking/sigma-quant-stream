package cmd

import (
	"fmt"

	"github.com/Dallionking/sigma-quant-stream/internal/agent"
	"github.com/Dallionking/sigma-quant-stream/internal/config"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
	"github.com/spf13/cobra"
)

var stopForce bool

var stopCmd = &cobra.Command{
	Use:   "stop",
	Short: "Gracefully stop all workers",
	Long: `Stop all running agent workers.

By default, sends SIGINT (Ctrl-C) to each tmux pane and waits up to
10 seconds for graceful shutdown. Use --force to kill immediately.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		root, err := config.DetectProjectRoot()
		if err != nil {
			return fmt.Errorf("detecting project root: %w", err)
		}

		if _, err := config.Load(root); err != nil {
			return fmt.Errorf("loading config: %w", err)
		}

		mgr := agent.NewManager(root, "sigma-quant")

		if !mgr.IsRunning() {
			fmt.Println(styles.Dim("No active tmux session found. Nothing to stop."))
			return nil
		}

		if stopForce {
			fmt.Println(styles.Title.Render("Force stopping all workers"))
		} else {
			fmt.Println(styles.Title.Render("Gracefully stopping all workers"))
		}
		fmt.Println()

		if err := mgr.StopAll(); err != nil {
			return fmt.Errorf("stopping workers: %w", err)
		}

		fmt.Println("  " + styles.StatusBadge("ok") + "  " + styles.Bold("All workers stopped"))
		fmt.Println()
		fmt.Println(styles.Green("Shutdown complete."))
		return nil
	},
}

func init() {
	stopCmd.Flags().BoolVar(&stopForce, "force", false, "kill workers immediately without graceful shutdown")
	rootCmd.AddCommand(stopCmd)
}
