package python

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
)

// DownloadOptions configures a market data download invocation.
type DownloadOptions struct {
	Market  string   // "futures", "crypto-cex", "crypto-dex"
	Symbols []string // e.g. ["ES", "NQ"] or ["BTC/USDT"]
	Period  string   // e.g. "2y", "5y", "15y"
	APIKey  string   // optional API key (e.g. for Databento)
}

// DownloadProgress represents a single progress update emitted as a JSON line
// by the download script.
type DownloadProgress struct {
	Symbol   string  `json:"symbol"`
	Progress float64 `json:"progress"` // 0.0 to 1.0
	Message  string  `json:"message"`
	Done     bool    `json:"done"`
	Error    string  `json:"error"`
}

// DownloadData invokes scripts/download-data.py and streams progress updates
// back through a channel. Each line of stdout is expected to be a JSON object
// conforming to DownloadProgress. The returned channel is closed when the
// script finishes. Any fatal error is reported via the error return value.
func (r *Runner) DownloadData(ctx context.Context, opts DownloadOptions) (<-chan DownloadProgress, error) {
	if len(opts.Symbols) == 0 {
		return nil, fmt.Errorf("at least one symbol is required")
	}

	args := []string{
		"--market", opts.Market,
		"--symbols", strings.Join(opts.Symbols, ","),
		"--period", opts.Period,
	}

	if opts.APIKey != "" {
		args = append(args, "--api-key", opts.APIKey)
	}

	lines, errc := r.ExecStreaming(ctx, "scripts/download-data.py", args)

	progress := make(chan DownloadProgress, 32)

	go func() {
		defer close(progress)

		for line := range lines {
			line = strings.TrimSpace(line)
			if line == "" {
				continue
			}

			var p DownloadProgress
			if err := json.Unmarshal([]byte(line), &p); err != nil {
				// Non-JSON lines are forwarded as informational messages.
				progress <- DownloadProgress{
					Message: line,
				}
				continue
			}
			progress <- p
		}

		// Propagate script-level errors as a final progress event.
		if err := <-errc; err != nil {
			progress <- DownloadProgress{
				Error: err.Error(),
				Done:  true,
			}
		}
	}()

	return progress, nil
}
