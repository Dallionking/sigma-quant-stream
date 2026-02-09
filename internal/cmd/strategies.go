package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/Dallionking/sigma-quant-stream/internal/config"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/views"
	"github.com/spf13/cobra"
)

var (
	strategiesFilter string
	strategiesJSON   bool
)

var strategiesCmd = &cobra.Command{
	Use:   "strategies",
	Short: "Browse discovered strategies",
	Long: `Browse and filter strategies produced by the research pipeline.

Strategies are categorised by the validation pipeline into:
  good       - Passed all thresholds
  review     - Needs manual review
  rejected   - Failed validation
  prop-firm  - Passed prop firm compliance checks

Use --filter to show only a specific category, or --json for machine-
readable output.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		root, err := config.DetectProjectRoot()
		if err != nil {
			return fmt.Errorf("detecting project root: %w", err)
		}

		if _, err := config.Load(root); err != nil {
			return fmt.Errorf("loading config: %w", err)
		}

		// JSON mode: print machine-readable output and exit.
		if strategiesJSON {
			return runStrategiesJSON(root)
		}

		// Interactive TUI browser.
		return views.RunStrategyBrowser(strategiesFilter, root)
	},
}

// runStrategiesJSON prints strategy entries as JSON to stdout, preserving the
// original --json behaviour for machine-readable output.
func runStrategiesJSON(root string) error {
	paths := config.NewPaths(root)

	categoryDirs := map[string]string{
		"good":      paths.Output.StrategiesGood,
		"review":    paths.Output.StrategiesReview,
		"rejected":  paths.Output.StrategiesRejected,
		"prop-firm": paths.Output.StrategiesPropFirm,
	}

	scanDirs := categoryDirs
	if strategiesFilter != "" {
		dir, ok := categoryDirs[strategiesFilter]
		if !ok {
			return fmt.Errorf("unknown filter %q; valid options: good, review, rejected, prop-firm", strategiesFilter)
		}
		scanDirs = map[string]string{strategiesFilter: dir}
	}

	type jsonEntry struct {
		Name     string `json:"name"`
		Category string `json:"category"`
		Path     string `json:"path"`
	}

	var entries []jsonEntry

	for category, dir := range scanDirs {
		files, err := listStrategyFiles(dir)
		if err != nil {
			continue
		}
		for _, f := range files {
			entries = append(entries, jsonEntry{
				Name:     f,
				Category: category,
				Path:     filepath.Join(dir, f),
			})
		}
	}

	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(entries)
}

// listStrategyFiles returns filenames (not full paths) of strategy files in dir.
func listStrategyFiles(dir string) ([]string, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}

	var names []string
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		name := e.Name()
		// Include Python, JSON, and YAML strategy files.
		lower := strings.ToLower(name)
		if strings.HasSuffix(lower, ".py") ||
			strings.HasSuffix(lower, ".json") ||
			strings.HasSuffix(lower, ".yaml") ||
			strings.HasSuffix(lower, ".yml") {
			names = append(names, name)
		}
	}
	return names, nil
}

func init() {
	strategiesCmd.Flags().StringVar(&strategiesFilter, "filter", "", "filter by category: good, review, rejected, or prop-firm")
	strategiesCmd.Flags().BoolVar(&strategiesJSON, "json", false, "output strategy list as JSON")
	rootCmd.AddCommand(strategiesCmd)
}
