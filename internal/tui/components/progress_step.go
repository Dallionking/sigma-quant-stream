package components

import (
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// ProgressStep shows a multi-step progress indicator.
type ProgressStep struct {
	Steps   []string // step labels
	Current int      // 0-indexed current step
	Width   int
}

// Render returns the styled progress indicator.
// Completed steps get a filled green dot, the current step gets a cyan bold
// dot, and future steps get an empty muted circle.
func (p ProgressStep) Render() string {
	if len(p.Steps) == 0 {
		return ""
	}

	var parts []string

	for i, label := range p.Steps {
		var dot string
		var labelStr string

		switch {
		case i < p.Current:
			// Completed.
			dot = lipgloss.NewStyle().Foreground(styles.StatusOK).Render("●")
			labelStr = lipgloss.NewStyle().Foreground(styles.StatusOK).Render(label)
		case i == p.Current:
			// Current step.
			dot = lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true).Render("●")
			labelStr = lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true).Render(label)
		default:
			// Future step.
			dot = lipgloss.NewStyle().Foreground(styles.TextMuted).Render("○")
			labelStr = lipgloss.NewStyle().Foreground(styles.TextMuted).Render(label)
		}

		parts = append(parts, dot+" "+labelStr)
	}

	separator := lipgloss.NewStyle().Foreground(styles.TextMuted).Render("  ")
	return strings.Join(parts, separator)
}
