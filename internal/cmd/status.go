package cmd

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/Dallionking/sigma-quant-stream/internal/agent"
	"github.com/Dallionking/sigma-quant-stream/internal/config"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/views"
	"github.com/spf13/cobra"
)

var (
	statusOnce bool
	statusJSON bool
)

var statusCmd = &cobra.Command{
	Use:   "status",
	Short: "Show the dashboard or a quick status snapshot",
	Long: `Launch the interactive dashboard TUI.

By default, opens a full-screen terminal UI with live-updating worker
status, queue depths, and recent research logs.

Flags:
  --once   print a single snapshot and exit (no TUI)
  --json   output status as JSON (implies --once)`,
	RunE: func(cmd *cobra.Command, args []string) error {
		// JSON implies once.
		if statusJSON {
			statusOnce = true
		}

		root, err := config.DetectProjectRoot()
		if err != nil {
			return fmt.Errorf("detecting project root: %w", err)
		}

		cfg, err := config.Load(root)
		if err != nil {
			return fmt.Errorf("loading config: %w", err)
		}

		if statusOnce {
			mgr := agent.NewManager(root, "sigma-quant")
			return printStatusSnapshot(cfg, mgr)
		}

		// Full TUI mode -- launch interactive dashboard.
		return views.RunDashboard(root)
	},
}

// printStatusSnapshot outputs a single-shot status report.
func printStatusSnapshot(cfg *config.Config, mgr *agent.Manager) error {
	running := mgr.IsRunning()
	states := mgr.GetWorkerStates()

	if statusJSON {
		type workerJSON struct {
			Name  string `json:"name"`
			State string `json:"state"`
			Tasks int    `json:"tasks_completed"`
		}

		type snapshot struct {
			SessionActive bool         `json:"session_active"`
			Mode          string       `json:"mode"`
			Profile       string       `json:"active_profile"`
			Workers       []workerJSON `json:"workers"`
		}

		s := snapshot{
			SessionActive: running,
			Mode:          cfg.Defaults.Mode,
			Profile:       cfg.ActiveProfile,
		}

		for _, wt := range agent.AllWorkerTypes() {
			w := workerJSON{Name: string(wt), State: "stopped"}
			if rw, ok := states[wt]; ok {
				w.State = rw.State.String()
				w.Tasks = rw.TasksCompleted
			}
			s.Workers = append(s.Workers, w)
		}

		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		return enc.Encode(s)
	}

	// Styled text output.
	fmt.Println(styles.Title.Render("Status Snapshot"))
	fmt.Println()

	sessionLabel := styles.StatusBadge("error") + " " + styles.Dim("inactive")
	if running {
		sessionLabel = styles.StatusBadge("ok") + " " + styles.Dim("active")
	}
	fmt.Println(styles.Label.Render("SESSION") + "   " + sessionLabel)
	fmt.Println(styles.Label.Render("MODE") + "      " + styles.Value.Render(cfg.Defaults.Mode))
	fmt.Println(styles.Label.Render("PROFILE") + "   " + styles.Value.Render(cfg.ActiveProfile))
	fmt.Println()
	fmt.Println(styles.Divider(50))
	fmt.Println()

	for _, wt := range agent.AllWorkerTypes() {
		state := "stopped"
		badge := styles.StatusBadge("error")
		if rw, ok := states[wt]; ok {
			state = rw.State.String()
			switch {
			case rw.State == agent.StateRunning || rw.State == agent.StateIdle:
				badge = styles.StatusBadge("ok")
			case rw.State == agent.StateStarting || rw.State == agent.StateStopping:
				badge = styles.StatusBadge("warn")
			default:
				badge = styles.StatusBadge("error")
			}
		}
		fmt.Printf("  %s  %-12s %s\n", badge, styles.Bold(string(wt)), styles.Dim(state))
	}
	fmt.Println()

	return nil
}

func init() {
	statusCmd.Flags().BoolVar(&statusOnce, "once", false, "print a single snapshot and exit")
	statusCmd.Flags().BoolVar(&statusJSON, "json", false, "output status as JSON (implies --once)")
	rootCmd.AddCommand(statusCmd)
}
