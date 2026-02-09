package cmd

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/Dallionking/sigma-quant-stream/internal/agent"
	"github.com/Dallionking/sigma-quant-stream/internal/config"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
	"github.com/spf13/cobra"
)

var (
	startMode  string
	startPanes int
)

var startCmd = &cobra.Command{
	Use:   "start [worker]",
	Short: "Launch workers in tmux panes",
	Long: `Start the agent worker swarm.

When run with no arguments, all 4 workers are launched in a 2x2 tmux grid:
  - researcher   discovers and generates strategy hypotheses
  - converter    converts hypotheses into backtestable code
  - backtester   runs walk-forward backtests
  - optimizer    optimises parameters and validates results

Pass a specific worker name to start only that worker.`,
	Args: cobra.MaximumNArgs(1),
	ValidArgs: []string{
		string(agent.Researcher),
		string(agent.Converter),
		string(agent.Backtester),
		string(agent.Optimizer),
	},
	RunE: func(cmd *cobra.Command, args []string) error {
		// Detect project root and load config.
		root, err := config.DetectProjectRoot()
		if err != nil {
			return fmt.Errorf("detecting project root: %w", err)
		}

		if _, err := config.Load(root); err != nil {
			return fmt.Errorf("loading config: %w", err)
		}

		fmt.Println(styles.Logo())
		fmt.Println()

		// Create agent manager.
		mgr := agent.NewManager(root, "sigma-quant")
		mgr.SetMode(startMode)

		ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
		defer stop()

		if len(args) == 0 {
			// Start all workers.
			fmt.Println(styles.Title.Render("Starting all workers"))
			fmt.Println(styles.Dim(fmt.Sprintf("mode=%s  panes=%d", startMode, startPanes)))
			fmt.Println()

			if err := mgr.StartAll(ctx); err != nil {
				return fmt.Errorf("starting workers: %w", err)
			}

			for _, wt := range agent.AllWorkerTypes() {
				fmt.Println("  " + styles.StatusBadge("ok") + "  " + styles.Bold(string(wt)))
			}
		} else {
			// Start a single worker.
			workerName := strings.ToLower(args[0])
			wt := agent.WorkerType(workerName)

			fmt.Println(styles.Title.Render(fmt.Sprintf("Starting worker: %s", workerName)))
			fmt.Println(styles.Dim(fmt.Sprintf("mode=%s", startMode)))
			fmt.Println()

			if err := mgr.StartWorker(ctx, wt); err != nil {
				return fmt.Errorf("starting worker %s: %w", workerName, err)
			}

			fmt.Println("  " + styles.StatusBadge("ok") + "  " + styles.Bold(workerName))
		}

		fmt.Println()
		fmt.Println(styles.Green("Workers launched.") + " " + styles.Dim("Attach with: tmux attach -t sigma-quant"))
		return nil
	},
}

func init() {
	startCmd.Flags().StringVar(&startMode, "mode", "research", "operational mode: research or production")
	startCmd.Flags().IntVar(&startPanes, "panes", 4, "number of tmux panes")
	rootCmd.AddCommand(startCmd)
}
