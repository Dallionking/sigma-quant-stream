package components

import (
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// KeyHint describes a single keybinding hint for display in the footer.
type KeyHint struct {
	Key  string // "q", "tab", "up/dn"
	Desc string // "quit", "switch", "navigate"
}

// Footer renders context-aware keybinding hints.
type Footer struct {
	Hints []KeyHint
	Width int
}

// Render returns the styled footer string.
func (f Footer) Render() string {
	width := f.Width
	if width <= 0 {
		width = 80
	}

	keyStyle := lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true)
	descStyle := lipgloss.NewStyle().Foreground(styles.TextMuted)
	sepStyle := lipgloss.NewStyle().Foreground(styles.TextMuted)

	var parts []string
	for _, h := range f.Hints {
		parts = append(parts, keyStyle.Render(h.Key)+" "+descStyle.Render(h.Desc))
	}

	content := strings.Join(parts, sepStyle.Render(" • "))

	footerStyle := lipgloss.NewStyle().
		Background(styles.BgDeep).
		Foreground(styles.TextMuted).
		Width(width).
		PaddingLeft(1).
		PaddingRight(1)

	return footerStyle.Render(content)
}

// DashboardFooter returns a footer preset for the main dashboard.
func DashboardFooter(width int) Footer {
	return Footer{
		Hints: []KeyHint{
			{Key: "q", Desc: "quit"},
			{Key: "tab", Desc: "switch"},
			{Key: "↑↓", Desc: "navigate"},
			{Key: "enter", Desc: "select"},
			{Key: "?", Desc: "help"},
		},
		Width: width,
	}
}

// WizardFooter returns a footer preset for wizard/setup screens.
func WizardFooter(width int) Footer {
	return Footer{
		Hints: []KeyHint{
			{Key: "tab", Desc: "next field"},
			{Key: "shift+tab", Desc: "prev field"},
			{Key: "enter", Desc: "confirm"},
			{Key: "esc", Desc: "cancel"},
		},
		Width: width,
	}
}

// BrowserFooter returns a footer preset for strategy browsing.
func BrowserFooter(width int) Footer {
	return Footer{
		Hints: []KeyHint{
			{Key: "↑↓", Desc: "navigate"},
			{Key: "enter", Desc: "details"},
			{Key: "/", Desc: "filter"},
			{Key: "q", Desc: "back"},
		},
		Width: width,
	}
}
