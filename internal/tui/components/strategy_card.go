package components

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// StrategyCard shows a strategy summary.
type StrategyCard struct {
	Name       string
	Status     string  // "good", "prop_firm_ready", "under_review", "rejected"
	Sharpe     float64
	MaxDD      float64
	WinRate    float64
	TradeCount int
	Market     string // "futures", "crypto"
}

// statusBadgeColor returns the color for a strategy status.
func statusBadgeColor(status string) lipgloss.Color {
	switch strings.ToLower(status) {
	case "good":
		return styles.StatusOK
	case "prop_firm_ready":
		return styles.AccentGold
	case "under_review":
		return styles.StatusWarn
	case "rejected":
		return styles.StatusError
	default:
		return styles.TextMuted
	}
}

// statusDisplayName returns a human-friendly label.
func statusDisplayName(status string) string {
	switch strings.ToLower(status) {
	case "good":
		return "GOOD"
	case "prop_firm_ready":
		return "PROP READY"
	case "under_review":
		return "REVIEW"
	case "rejected":
		return "REJECTED"
	default:
		return strings.ToUpper(status)
	}
}

// Render returns the styled strategy card as a multi-line block.
func (s StrategyCard) Render() string {
	// Badge line.
	color := statusBadgeColor(s.Status)
	badge := styles.Badge(statusDisplayName(s.Status), color)

	nameStyle := lipgloss.NewStyle().Foreground(styles.TextPrimary).Bold(true)
	marketStyle := lipgloss.NewStyle().Foreground(styles.TextMuted)

	line1 := nameStyle.Render(s.Name) + "  " + badge + "  " + marketStyle.Render("["+strings.ToUpper(s.Market)+"]")

	// Metrics line.
	sharpeColor := styles.StatusOK
	if s.Sharpe < 1.0 {
		sharpeColor = styles.StatusWarn
	}
	if s.Sharpe < 0.5 {
		sharpeColor = styles.StatusError
	}

	ddColor := styles.StatusOK
	if s.MaxDD > 5.0 {
		ddColor = styles.StatusWarn
	}
	if s.MaxDD > 10.0 {
		ddColor = styles.StatusError
	}

	wrColor := styles.StatusOK
	if s.WinRate < 50.0 {
		wrColor = styles.StatusWarn
	}
	if s.WinRate < 40.0 {
		wrColor = styles.StatusError
	}

	sharpe := lipgloss.NewStyle().Foreground(sharpeColor).Bold(true).Render(fmt.Sprintf("%.2f", s.Sharpe))
	maxDD := lipgloss.NewStyle().Foreground(ddColor).Bold(true).Render(fmt.Sprintf("%.1f%%", s.MaxDD))
	winRate := lipgloss.NewStyle().Foreground(wrColor).Bold(true).Render(fmt.Sprintf("%.1f%%", s.WinRate))
	trades := styles.Value.Render(fmt.Sprintf("%d", s.TradeCount))

	sep := lipgloss.NewStyle().Foreground(styles.TextMuted).Render("  │  ")

	line2 := styles.Label.Render("Sharpe: ") + sharpe + sep +
		styles.Label.Render("MaxDD: ") + maxDD + sep +
		styles.Label.Render("WR: ") + winRate + sep +
		styles.Label.Render("Trades: ") + trades

	cardStyle := lipgloss.NewStyle().
		Background(styles.BgSurface).
		Border(styles.ThinBorder).
		BorderForeground(styles.BorderNormal).
		Padding(0, 1)

	return cardStyle.Render(lipgloss.JoinVertical(lipgloss.Left, line1, line2))
}

// RenderCompact returns a single-line representation for use in tables.
func (s StrategyCard) RenderCompact() string {
	color := statusBadgeColor(s.Status)
	dot := lipgloss.NewStyle().Foreground(color).Render("●")
	name := lipgloss.NewStyle().Foreground(styles.TextPrimary).Render(styles.TruncateWithEllipsis(s.Name, 20))
	sharpe := lipgloss.NewStyle().Foreground(styles.TextSecondary).Render(fmt.Sprintf("SR:%.2f", s.Sharpe))
	dd := lipgloss.NewStyle().Foreground(styles.TextSecondary).Render(fmt.Sprintf("DD:%.1f%%", s.MaxDD))
	wr := lipgloss.NewStyle().Foreground(styles.TextSecondary).Render(fmt.Sprintf("WR:%.0f%%", s.WinRate))
	trades := lipgloss.NewStyle().Foreground(styles.TextMuted).Render(fmt.Sprintf("T:%d", s.TradeCount))
	market := lipgloss.NewStyle().Foreground(styles.TextMuted).Render(strings.ToUpper(s.Market))

	return fmt.Sprintf("%s %-22s  %s  %s  %s  %s  %s", dot, name, sharpe, dd, wr, trades, market)
}
