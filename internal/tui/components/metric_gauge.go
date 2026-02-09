package components

import (
	"fmt"

	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// MetricGauge displays a single metric with color coding based on thresholds.
type MetricGauge struct {
	Label      string
	Value      float64
	Format     string     // "%.2f", "%.1f%%", "%d"
	Thresholds [2]float64 // [warn, critical]
	HighIsGood bool       // true for Sharpe, false for MaxDD
}

// gaugeColor returns the appropriate color based on value and thresholds.
func (m MetricGauge) gaugeColor() lipgloss.Color {
	warn := m.Thresholds[0]
	critical := m.Thresholds[1]

	if m.HighIsGood {
		// Higher is better: value > warn = good, value > critical = bad does not apply
		// Thresholds: [warn_below, critical_below]
		if m.Value <= critical {
			return styles.StatusError
		}
		if m.Value <= warn {
			return styles.StatusWarn
		}
		return styles.StatusOK
	}

	// Lower is better (e.g., MaxDD): value > warn = bad
	if m.Value >= critical {
		return styles.StatusError
	}
	if m.Value >= warn {
		return styles.StatusWarn
	}
	return styles.StatusOK
}

// Render returns the styled metric gauge.
func (m MetricGauge) Render() string {
	color := m.gaugeColor()

	format := m.Format
	if format == "" {
		format = "%.2f"
	}

	valueStr := fmt.Sprintf(format, m.Value)

	valueStyle := lipgloss.NewStyle().
		Foreground(color).
		Bold(true)

	labelStyle := lipgloss.NewStyle().
		Foreground(styles.TextMuted)

	return lipgloss.JoinVertical(
		lipgloss.Center,
		valueStyle.Render(valueStr),
		labelStyle.Render(m.Label),
	)
}
