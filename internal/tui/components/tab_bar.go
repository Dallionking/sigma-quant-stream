package components

import (
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// TabBar renders horizontal tab selection.
type TabBar struct {
	Tabs      []string
	ActiveTab int
	Width     int
}

// Render returns the styled tab bar string.
func (t TabBar) Render() string {
	if len(t.Tabs) == 0 {
		return ""
	}

	activeStyle := lipgloss.NewStyle().
		Foreground(styles.AccentPrimary).
		Bold(true).
		Underline(true).
		PaddingLeft(1).
		PaddingRight(1)

	inactiveStyle := lipgloss.NewStyle().
		Foreground(styles.TextSecondary).
		PaddingLeft(1).
		PaddingRight(1)

	var tabs []string
	for i, tab := range t.Tabs {
		if i == t.ActiveTab {
			tabs = append(tabs, activeStyle.Render(tab))
		} else {
			tabs = append(tabs, inactiveStyle.Render(tab))
		}
	}

	sep := lipgloss.NewStyle().Foreground(styles.TextMuted).Render("│")
	content := strings.Join(tabs, sep)

	barStyle := lipgloss.NewStyle().
		Background(styles.BgDeep).
		Width(t.Width)

	return barStyle.Render(content)
}
