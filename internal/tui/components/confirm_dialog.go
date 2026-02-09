package components

import (
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// ConfirmDialog is a modal yes/no dialog implementing the Bubble Tea Model interface.
type ConfirmDialog struct {
	Title     string
	Message   string
	Confirmed bool
	Done      bool
	selected  int // 0 = Yes, 1 = No
}

// NewConfirmDialog creates a new confirmation dialog.
func NewConfirmDialog(title, message string) ConfirmDialog {
	return ConfirmDialog{
		Title:    title,
		Message:  message,
		selected: 1, // default to No for safety
	}
}

// Init satisfies tea.Model. No initial command needed.
func (d ConfirmDialog) Init() tea.Cmd {
	return nil
}

// Update satisfies tea.Model. Handles keyboard input for confirmation.
func (d ConfirmDialog) Update(msg tea.Msg) (ConfirmDialog, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "y", "Y":
			d.Confirmed = true
			d.Done = true
			return d, nil
		case "n", "N", "esc":
			d.Confirmed = false
			d.Done = true
			return d, nil
		case "enter":
			d.Confirmed = d.selected == 0
			d.Done = true
			return d, nil
		case "left", "h", "tab":
			d.selected = 0
		case "right", "l", "shift+tab":
			d.selected = 1
		}
	}
	return d, nil
}

// View satisfies tea.Model. Returns the styled dialog.
func (d ConfirmDialog) View() string {
	// Title.
	titleStyle := lipgloss.NewStyle().
		Foreground(styles.AccentPrimary).
		Bold(true)
	title := titleStyle.Render(d.Title)

	// Message.
	msgStyle := lipgloss.NewStyle().
		Foreground(styles.TextSecondary)
	message := msgStyle.Render(d.Message)

	// Buttons.
	yesLabel := " Yes "
	noLabel := " No "

	selectedStyle := lipgloss.NewStyle().
		Background(styles.AccentPrimary).
		Foreground(styles.BgDeep).
		Bold(true).
		Padding(0, 1)

	unselectedStyle := lipgloss.NewStyle().
		Background(styles.BgSurface).
		Foreground(styles.TextSecondary).
		Padding(0, 1)

	var yesBtn, noBtn string
	if d.selected == 0 {
		yesBtn = selectedStyle.Render(yesLabel)
		noBtn = unselectedStyle.Render(noLabel)
	} else {
		yesBtn = unselectedStyle.Render(yesLabel)
		noBtn = selectedStyle.Render(noLabel)
	}

	buttons := lipgloss.JoinHorizontal(lipgloss.Center, yesBtn, "  ", noBtn)

	hint := lipgloss.NewStyle().Foreground(styles.TextMuted).
		Render("y/n or ←→ + enter")

	content := lipgloss.JoinVertical(lipgloss.Center,
		title,
		"",
		message,
		"",
		buttons,
		"",
		hint,
	)

	dialogStyle := lipgloss.NewStyle().
		Background(styles.BgPanel).
		Border(styles.RoundedBorder).
		BorderForeground(styles.AccentTertiary).
		Padding(1, 2).
		Width(48).
		Align(lipgloss.Center)

	return dialogStyle.Render(content)
}
