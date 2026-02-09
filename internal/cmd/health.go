package cmd

import (
	"context"
	"fmt"
	"time"

	"github.com/Dallionking/sigma-quant-stream/internal/config"
	"github.com/Dallionking/sigma-quant-stream/internal/health"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
	"github.com/spf13/cobra"
)

var (
	healthCheck    string
	healthCategory string
)

var healthCmd = &cobra.Command{
	Use:   "health",
	Short: "Run system and project health checks",
	Long: `Run diagnostic health checks against the project environment.

Checks are grouped into categories:
  system   - OS tools, tmux, Python, disk space
  project  - config.json, directory structure, prompts
  data     - data files, queue status
  runtime  - running workers, tmux session

Use --category to run only a specific group, or --check to run a single
named check.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		root, err := config.DetectProjectRoot()
		if err != nil {
			return fmt.Errorf("detecting project root: %w", err)
		}

		if _, err := config.Load(root); err != nil {
			return fmt.Errorf("loading config: %w", err)
		}

		fmt.Println(styles.Title.Render("Health Check"))
		fmt.Println()

		checker := health.NewChecker(root)
		ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
		defer cancel()

		var report *health.Report
		if healthCategory != "" {
			fmt.Println(styles.Label.Render("CATEGORY") + "  " + styles.Value.Render(healthCategory))
			fmt.Println()
			report = checker.RunCategory(ctx, healthCategory)
		} else {
			report = checker.RunAll(ctx)
		}

		// Print results.
		for _, r := range report.Results {
			symbol := r.Status.Symbol()
			var badge string
			switch r.Status {
			case health.StatusPass:
				badge = styles.Green("[" + symbol + "]")
			case health.StatusWarn:
				badge = styles.Gold("[" + symbol + "]")
			case health.StatusFail:
				badge = styles.Red("[" + symbol + "]")
			default:
				badge = styles.Dim("[?]")
			}

			dur := ""
			if r.Duration > 0 {
				dur = styles.Dim(fmt.Sprintf(" (%s)", r.Duration.Round(time.Millisecond)))
			}

			fmt.Printf("  %s  %-30s %s%s\n",
				badge,
				styles.Bold(r.Name),
				styles.Dim(r.Message),
				dur,
			)
		}

		fmt.Println()
		fmt.Println(styles.Divider(60))
		fmt.Println()

		summary := fmt.Sprintf("Passed: %d  Warned: %d  Failed: %d  Total: %d  (%s)",
			report.Passed, report.Warned, report.Failed, report.Total,
			report.Duration.Round(time.Millisecond),
		)

		if report.Healthy {
			fmt.Println(styles.Green("HEALTHY") + "  " + styles.Dim(summary))
		} else {
			fmt.Println(styles.Red("UNHEALTHY") + "  " + styles.Dim(summary))
		}

		return nil
	},
}

func init() {
	healthCmd.Flags().StringVar(&healthCheck, "check", "", "run a specific named check")
	healthCmd.Flags().StringVar(&healthCategory, "category", "", "run checks in a category: system, project, data, or runtime")
	rootCmd.AddCommand(healthCmd)
}
