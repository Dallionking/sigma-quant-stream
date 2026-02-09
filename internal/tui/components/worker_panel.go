package components

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// WorkerPanel shows a single worker's status inside a bordered panel.
type WorkerPanel struct {
	Name        string // "Researcher", "Converter", etc.
	Icon        string // "🔬", "🔄", "📊", "⚡"
	State       string // "running", "idle", "stopped", "error"
	Sessions    int    // sessions completed
	Tasks       int    // tasks completed
	CurrentTask string // what the worker is doing now
	Width       int    // available width
	Focused     bool   // if this panel has focus
}

// stateColor returns the dot color for the given state string.
func stateColor(state string) lipgloss.Color {
	switch strings.ToLower(state) {
	case "running":
		return styles.StatusOK
	case "idle":
		return styles.StatusWarn
	case "stopped":
		return styles.TextMuted
	case "error":
		return styles.StatusError
	default:
		return styles.TextMuted
	}
}

// stateLabel returns the human-readable label for a state.
func stateLabel(state string) string {
	switch strings.ToLower(state) {
	case "running":
		return "Running"
	case "idle":
		return "Idle"
	case "stopped":
		return "Stopped"
	case "error":
		return "Error"
	default:
		return strings.Title(state) //nolint:staticcheck
	}
}

// Render returns the styled panel string.
func (w WorkerPanel) Render() string {
	width := w.Width
	if width <= 0 {
		width = 36
	}

	// Choose border style based on focus.
	border := styles.RoundedBorder
	borderColor := styles.BorderNormal
	if w.Focused {
		border = styles.DoubleBorder
		borderColor = styles.BorderFocused
	}

	// Inner content width accounts for border (1 char each side) and padding (1 each side).
	innerWidth := width - 4
	if innerWidth < 10 {
		innerWidth = 10
	}

	// Line 1: Icon + NAME + state dot.
	nameStyle := lipgloss.NewStyle().Foreground(styles.TextPrimary).Bold(true)
	nameStr := nameStyle.Render(w.Icon + " " + strings.ToUpper(w.Name))

	dotStyle := lipgloss.NewStyle().Foreground(stateColor(w.State))
	labelStyle := lipgloss.NewStyle().Foreground(stateColor(w.State))
	stateStr := dotStyle.Render("●") + " " + labelStyle.Render(stateLabel(w.State))

	// Pad to fill the line.
	nameLen := lipgloss.Width(nameStr)
	stateLen := lipgloss.Width(stateStr)
	gap := innerWidth - nameLen - stateLen
	if gap < 1 {
		gap = 1
	}
	line1 := nameStr + strings.Repeat(" ", gap) + stateStr

	// Line 2: Session and Tasks counts.
	sessionLabel := styles.Label.Render("Session:")
	sessionVal := styles.Value.Render(fmt.Sprintf(" %d", w.Sessions))
	sep := lipgloss.NewStyle().Foreground(styles.TextMuted).Render(" │ ")
	taskLabel := styles.Label.Render("Tasks:")
	taskVal := styles.Value.Render(fmt.Sprintf(" %d", w.Tasks))
	line2 := sessionLabel + sessionVal + sep + taskLabel + taskVal

	// Line 3: Current task (truncated if too long).
	currentLabel := styles.Label.Render("Current: ")
	taskText := w.CurrentTask
	if taskText == "" {
		taskText = "---"
	}
	maxTaskLen := innerWidth - lipgloss.Width(currentLabel)
	if maxTaskLen < 0 {
		maxTaskLen = 0
	}
	taskText = styles.TruncateWithEllipsis(taskText, maxTaskLen)
	line3 := currentLabel + lipgloss.NewStyle().Foreground(styles.TextSecondary).Render(taskText)

	content := lipgloss.JoinVertical(lipgloss.Left, line1, line2, line3)

	panelStyle := lipgloss.NewStyle().
		Background(styles.BgPanel).
		Border(border).
		BorderForeground(borderColor).
		Padding(0, 1).
		Width(width - 2) // subtract border width

	return panelStyle.Render(content)
}
