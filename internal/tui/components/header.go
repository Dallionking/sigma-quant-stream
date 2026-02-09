package components

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// Header renders the app header bar.
type Header struct {
	Profile      string // "FUTURES", "CRYPTO-CEX", etc.
	Workers      int    // running worker count
	TotalWorkers int
	Cost         float64
	Width        int
}

// Render returns the styled header string.
func (h Header) Render() string {
	width := h.Width
	if width <= 0 {
		width = 80
	}

	logo := lipgloss.NewStyle().
		Foreground(styles.AccentPrimary).
		Bold(true).
		Render(styles.CompactLogo)

	sep := lipgloss.NewStyle().Foreground(styles.TextMuted).Render("  │  ")

	profile := styles.Label.Render("Profile: ") +
		lipgloss.NewStyle().Foreground(styles.AccentGold).Bold(true).Render(strings.ToUpper(h.Profile))

	workerColor := styles.StatusOK
	if h.Workers < h.TotalWorkers {
		workerColor = styles.StatusWarn
	}
	if h.Workers == 0 {
		workerColor = styles.StatusError
	}
	workers := styles.Label.Render("Workers: ") +
		lipgloss.NewStyle().Foreground(workerColor).Bold(true).
			Render(fmt.Sprintf("%d/%d", h.Workers, h.TotalWorkers))

	cost := styles.Label.Render("Cost: ") +
		lipgloss.NewStyle().Foreground(styles.TextPrimary).Bold(true).
			Render(fmt.Sprintf("$%.2f", h.Cost))

	content := logo + sep + profile + sep + workers + sep + cost

	headerStyle := lipgloss.NewStyle().
		Background(styles.BgDeep).
		Foreground(styles.TextPrimary).
		Width(width).
		PaddingLeft(1).
		PaddingRight(1)

	return headerStyle.Render(content)
}
