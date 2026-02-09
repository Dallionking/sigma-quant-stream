package python

import (
	"context"
	"encoding/json"
	"fmt"
	"time"
)

// DeployOptions configures a strategy export to Freqtrade format.
type DeployOptions struct {
	StrategyFile string // path to the source strategy file
	Exchange     string // target exchange: "binance", "bybit", etc.
	DryRun       bool   // if true, generate config for paper trading
}

// DeployResult contains the output paths and command produced by the
// Freqtrade deployment script.
type DeployResult struct {
	IStrategyFile string `json:"istrategy_file"` // path to the generated IStrategy .py
	ConfigFile    string `json:"config_file"`     // path to the generated Freqtrade config
	Command       string `json:"command"`         // shell command to start Freqtrade
}

// deployTimeout is the maximum time allowed for a Freqtrade deployment export.
const deployTimeout = 2 * time.Minute

// DeployToFreqtrade exports a strategy to Freqtrade IStrategy format by
// invoking scripts/freqtrade-deploy.sh (which in turn calls the Python
// converter). It returns the generated file paths and the command to launch
// Freqtrade.
func (r *Runner) DeployToFreqtrade(ctx context.Context, opts DeployOptions) (*DeployResult, error) {
	ctx, cancel := context.WithTimeout(ctx, deployTimeout)
	defer cancel()

	args := []string{
		"--strategy", opts.StrategyFile,
		"--exchange", opts.Exchange,
	}

	if opts.DryRun {
		args = append(args, "--dry-run")
	}

	// The converter script lives alongside the backtest runner in lib/.
	out, err := r.Exec(ctx, "lib/freqtrade_converter.py", args...)
	if err != nil {
		return nil, fmt.Errorf("freqtrade deployment failed: %w", err)
	}

	var result DeployResult
	if err := json.Unmarshal([]byte(out), &result); err != nil {
		return nil, fmt.Errorf("parsing deploy output: %w (raw: %s)", err, truncate(out, 200))
	}

	return &result, nil
}
