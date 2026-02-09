package python

import (
	"context"
	"encoding/json"
	"fmt"
	"time"
)

// BacktestResult represents the JSON output of a backtest run produced by
// lib/backtest_runner.py.
type BacktestResult struct {
	StrategyName string  `json:"strategy_name"`
	Sharpe       float64 `json:"sharpe_ratio"`
	MaxDrawdown  float64 `json:"max_drawdown"`
	WinRate      float64 `json:"win_rate"`
	TradeCount   int     `json:"trade_count"`
	ProfitFactor float64 `json:"profit_factor"`
	OOSDecay     float64 `json:"oos_decay"`
	TotalReturn  float64 `json:"total_return"`
	AvgTrade     float64 `json:"avg_trade_pnl"`
}

// BacktestOptions configures a single backtest invocation.
type BacktestOptions struct {
	StrategyFile string // path to the strategy Python file
	DataFile     string // path to the OHLCV data CSV / parquet
	CostModel    string // path to cost model config (JSON)
	DateRange    string // optional date range filter, e.g. "2022-01-01:2024-01-01"
	WalkForward  bool   // enable walk-forward validation
}

// backtestTimeout is the maximum time allowed for a single backtest run.
const backtestTimeout = 5 * time.Minute

// RunBacktest invokes lib/backtest_runner.py with the given options and parses
// its JSON output into a BacktestResult. A 5-minute timeout is enforced.
func (r *Runner) RunBacktest(ctx context.Context, opts BacktestOptions) (*BacktestResult, error) {
	ctx, cancel := context.WithTimeout(ctx, backtestTimeout)
	defer cancel()

	args := []string{
		"--strategy", opts.StrategyFile,
		"--data", opts.DataFile,
	}

	if opts.CostModel != "" {
		args = append(args, "--cost-model", opts.CostModel)
	}

	if opts.DateRange != "" {
		args = append(args, "--date-range", opts.DateRange)
	}

	if opts.WalkForward {
		args = append(args, "--walk-forward")
	}

	// Invoke the backtest runner script.
	out, err := r.Exec(ctx, "lib/backtest_runner.py", args...)
	if err != nil {
		return nil, fmt.Errorf("backtest execution failed: %w", err)
	}

	var result BacktestResult
	if err := json.Unmarshal([]byte(out), &result); err != nil {
		return nil, fmt.Errorf("parsing backtest output: %w (raw: %s)", err, truncate(out, 200))
	}

	return &result, nil
}

// ValidateResult checks whether the backtest result meets the given pass
// criteria. It returns a slice of human-readable failure reasons. An empty
// slice means all criteria passed.
func (br *BacktestResult) ValidateResult(
	minSharpe float64,
	maxSharpe float64,
	maxDD float64,
	minTrades int,
	maxWinRate float64,
	maxOOSDecay float64,
) []string {
	var failures []string

	if br.Sharpe < minSharpe {
		failures = append(failures,
			fmt.Sprintf("sharpe %.2f < min %.2f", br.Sharpe, minSharpe))
	}

	if br.Sharpe > maxSharpe {
		failures = append(failures,
			fmt.Sprintf("sharpe %.2f > max %.2f (possible overfitting)", br.Sharpe, maxSharpe))
	}

	if br.MaxDrawdown > maxDD {
		failures = append(failures,
			fmt.Sprintf("max drawdown %.2f%% > limit %.2f%%", br.MaxDrawdown, maxDD))
	}

	if br.TradeCount < minTrades {
		failures = append(failures,
			fmt.Sprintf("trade count %d < min %d (insufficient sample)", br.TradeCount, minTrades))
	}

	if br.WinRate > maxWinRate {
		failures = append(failures,
			fmt.Sprintf("win rate %.2f%% > max %.2f%% (suspicious)", br.WinRate, maxWinRate))
	}

	if br.OOSDecay > maxOOSDecay {
		failures = append(failures,
			fmt.Sprintf("OOS decay %.2f%% > max %.2f%%", br.OOSDecay, maxOOSDecay))
	}

	return failures
}

// truncate shortens a string to at most n characters, appending "..." if
// truncated. Used for error messages that include raw output.
func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "..."
}
