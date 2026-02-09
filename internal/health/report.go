package health

import (
	"fmt"
	"strings"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
	"github.com/charmbracelet/lipgloss"
)

// category display order
var categoryOrder = []string{"system", "project", "data", "runtime"}

// categoryLabel returns a human-friendly title for a category key.
func categoryLabel(cat string) string {
	switch cat {
	case "system":
		return "System Dependencies"
	case "project":
		return "Project Structure"
	case "data":
		return "Data & API Keys"
	case "runtime":
		return "Runtime"
	default:
		return strings.Title(cat) //nolint:staticcheck
	}
}

// FormatReport creates a lipgloss-styled health report string.
// This is used by non-TUI output (e.g. sigma-quant health --once).
func FormatReport(r *Report) string {
	var b strings.Builder

	// Title
	title := lipgloss.NewStyle().
		Foreground(styles.AccentPrimary).
		Bold(true).
		Render("System Health Check")
	b.WriteString("\n  " + title + "\n")
	b.WriteString("  " + styles.Divider(50) + "\n")

	// Group results by category
	grouped := make(map[string][]CheckResult)
	for _, res := range r.Results {
		grouped[res.Category] = append(grouped[res.Category], res)
	}

	// Style definitions for the table
	nameStyle := lipgloss.NewStyle().Width(22).Foreground(styles.TextPrimary)
	msgStyle := lipgloss.NewStyle().Width(40).Foreground(styles.TextSecondary)
	durStyle := lipgloss.NewStyle().Width(8).Foreground(styles.TextMuted).Align(lipgloss.Right)
	catStyle := lipgloss.NewStyle().
		Foreground(styles.AccentSecondary).
		Bold(true).
		MarginTop(1)

	for _, cat := range categoryOrder {
		results, ok := grouped[cat]
		if !ok || len(results) == 0 {
			continue
		}

		b.WriteString("\n  " + catStyle.Render(categoryLabel(cat)) + "\n")

		for _, res := range results {
			symbol := statusSymbol(res.Status)
			name := nameStyle.Render(res.Name)
			msg := msgStyle.Render(truncate(res.Message, 38))
			dur := durStyle.Render(formatDuration(res.Duration))
			b.WriteString(fmt.Sprintf("  %s %s %s %s\n", symbol, name, msg, dur))
		}
	}

	// Summary line
	b.WriteString("\n  " + styles.Divider(50) + "\n")
	summary := fmt.Sprintf("%d/%d passed", r.Passed, r.Total)
	if r.Warned > 0 {
		summary += fmt.Sprintf(", %d warning(s)", r.Warned)
	}
	if r.Failed > 0 {
		summary += fmt.Sprintf(", %d failed", r.Failed)
	}
	summaryStyled := lipgloss.NewStyle().Foreground(styles.TextSecondary).Render(summary)
	b.WriteString("  " + summaryStyled)

	// Overall status
	b.WriteString("  ")
	b.WriteString(overallBadge(r))
	b.WriteString("\n")

	// Total duration
	totalDur := lipgloss.NewStyle().
		Foreground(styles.TextMuted).
		Render(fmt.Sprintf("  completed in %s", formatDuration(r.Duration)))
	b.WriteString(totalDur + "\n")

	return b.String()
}

// statusSymbol returns a color-coded status symbol.
func statusSymbol(s Status) string {
	switch s {
	case StatusPass:
		return lipgloss.NewStyle().Foreground(styles.StatusOK).Bold(true).Render("+")
	case StatusWarn:
		return lipgloss.NewStyle().Foreground(styles.StatusWarn).Bold(true).Render("!")
	case StatusFail:
		return lipgloss.NewStyle().Foreground(styles.StatusError).Bold(true).Render("x")
	default:
		return lipgloss.NewStyle().Foreground(styles.TextMuted).Render("?")
	}
}

// overallBadge returns a styled overall status badge.
func overallBadge(r *Report) string {
	if r.Failed > 0 {
		return lipgloss.NewStyle().
			Foreground(styles.StatusError).
			Bold(true).
			Render("UNHEALTHY")
	}
	if r.Warned > 0 {
		return lipgloss.NewStyle().
			Foreground(styles.StatusWarn).
			Bold(true).
			Render("DEGRADED")
	}
	return lipgloss.NewStyle().
		Foreground(styles.StatusOK).
		Bold(true).
		Render("HEALTHY")
}

// formatDuration formats a time.Duration to a short human-readable string.
func formatDuration(d interface{ Milliseconds() int64 }) string {
	ms := d.Milliseconds()
	if ms < 1 {
		return "<1ms"
	}
	if ms < 1000 {
		return fmt.Sprintf("%dms", ms)
	}
	return fmt.Sprintf("%.1fs", float64(ms)/1000.0)
}

// truncate shortens a string with ellipsis if it exceeds max length.
func truncate(s string, max int) string {
	runes := []rune(s)
	if len(runes) <= max {
		return s
	}
	if max < 4 {
		return string(runes[:max])
	}
	return string(runes[:max-3]) + "..."
}
