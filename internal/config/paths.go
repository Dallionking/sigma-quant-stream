package config

import (
	"fmt"
	"os"
	"path/filepath"
)

// Paths holds all resolved filesystem paths for the project.
type Paths struct {
	Root     string
	Queues   QueuesPath
	Output   OutputPaths
	Patterns string
	Prompts  string
	Data     string
	Scripts  string
	Lib      string
	Profiles string
	Config   string
}

// QueuesPath holds resolved paths for each queue directory.
type QueuesPath struct {
	Hypotheses string
	ToConvert  string
	ToBacktest string
	ToOptimize string
}

// OutputPaths holds resolved paths for output subdirectories.
type OutputPaths struct {
	StrategiesGood     string
	StrategiesReview   string
	StrategiesRejected string
	StrategiesPropFirm string
	Indicators         string
	Backtests          string
	ResearchLogs       string
}

// DetectProjectRoot walks up from the current working directory looking for a
// directory that contains config.json. Returns the absolute path or an error
// if not found.
func DetectProjectRoot() (string, error) {
	dir, err := os.Getwd()
	if err != nil {
		return "", fmt.Errorf("getting working directory: %w", err)
	}

	for {
		candidate := filepath.Join(dir, "config.json")
		if _, err := os.Stat(candidate); err == nil {
			return dir, nil
		}

		parent := filepath.Dir(dir)
		if parent == dir {
			// Reached filesystem root without finding config.json.
			return "", fmt.Errorf("config.json not found in any parent directory")
		}
		dir = parent
	}
}

// NewPaths creates a Paths struct with all directories resolved relative to
// the project root. It reads queue paths from the loaded config when available,
// falling back to conventional defaults.
func NewPaths(root string) *Paths {
	p := &Paths{
		Root:     root,
		Patterns: filepath.Join(root, "patterns"),
		Prompts:  filepath.Join(root, "prompts"),
		Data:     filepath.Join(root, "data"),
		Scripts:  filepath.Join(root, "scripts"),
		Lib:      filepath.Join(root, "lib"),
		Profiles: filepath.Join(root, "profiles"),
		Config:   filepath.Join(root, "config.json"),
	}

	// Queue paths -- use config values when loaded, otherwise defaults.
	p.Queues = QueuesPath{
		Hypotheses: filepath.Join(root, "queues", "hypotheses"),
		ToConvert:  filepath.Join(root, "queues", "to-convert"),
		ToBacktest: filepath.Join(root, "queues", "to-backtest"),
		ToOptimize: filepath.Join(root, "queues", "to-optimize"),
	}

	mu.RLock()
	cfg := globalCfg
	mu.RUnlock()

	if cfg != nil {
		if cfg.Queues.Hypotheses != "" {
			p.Queues.Hypotheses = filepath.Join(root, cfg.Queues.Hypotheses)
		}
		if cfg.Queues.ToConvert != "" {
			p.Queues.ToConvert = filepath.Join(root, cfg.Queues.ToConvert)
		}
		if cfg.Queues.ToBacktest != "" {
			p.Queues.ToBacktest = filepath.Join(root, cfg.Queues.ToBacktest)
		}
		if cfg.Queues.ToOptimize != "" {
			p.Queues.ToOptimize = filepath.Join(root, cfg.Queues.ToOptimize)
		}
	}

	// Output paths -- conventional structure.
	p.Output = OutputPaths{
		StrategiesGood:     filepath.Join(root, "output", "strategies", "good"),
		StrategiesReview:   filepath.Join(root, "output", "strategies", "under_review"),
		StrategiesRejected: filepath.Join(root, "output", "strategies", "rejected"),
		StrategiesPropFirm: filepath.Join(root, "output", "strategies", "prop_firm_ready"),
		Indicators:         filepath.Join(root, "output", "indicators"),
		Backtests:          filepath.Join(root, "output", "backtests"),
		ResearchLogs:       filepath.Join(root, "output", "research-logs"),
	}

	return p
}

// EnsureDirectories creates all queue and output directories if they do not
// already exist. Returns the first error encountered, if any.
func EnsureDirectories(p *Paths) error {
	dirs := []string{
		// Queues
		p.Queues.Hypotheses,
		p.Queues.ToConvert,
		p.Queues.ToBacktest,
		p.Queues.ToOptimize,

		// Output
		p.Output.StrategiesGood,
		p.Output.StrategiesReview,
		p.Output.StrategiesRejected,
		p.Output.StrategiesPropFirm,
		p.Output.Indicators,
		p.Output.Backtests,
		p.Output.ResearchLogs,

		// Other standard directories
		p.Patterns,
		p.Prompts,
		p.Data,
		p.Profiles,
	}

	for _, d := range dirs {
		if err := os.MkdirAll(d, 0755); err != nil {
			return fmt.Errorf("creating directory %s: %w", d, err)
		}
	}
	return nil
}
