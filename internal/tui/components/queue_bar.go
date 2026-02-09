package components

import (
	"fmt"

	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// QueueBar shows the pipeline visualization as a horizontal flow.
type QueueBar struct {
	Hypotheses int
	ToConvert  int
	ToBacktest int
	ToOptimize int
	Width      int
}

// Render returns the styled pipeline bar.
func (q QueueBar) Render() string {
	width := q.Width
	if width <= 0 {
		width = 72
	}

	arrow := lipgloss.NewStyle().Foreground(styles.TextSecondary).Render(" ──▶ ")

	stages := []struct {
		label string
		count int
	}{
		{"Hypotheses", q.Hypotheses},
		{"To-Convert", q.ToConvert},
		{"To-Backtest", q.ToBacktest},
		{"Optimize", q.ToOptimize},
	}

	var parts []string
	for i, s := range stages {
		color := styles.TextMuted
		if s.count > 0 {
			color = styles.AccentPrimary
		}

		labelStyle := lipgloss.NewStyle().Foreground(color)
		countStyle := lipgloss.NewStyle().Foreground(color).Bold(true)

		segment := labelStyle.Render(s.label) + " " + countStyle.Render(fmt.Sprintf("[%d]", s.count))
		parts = append(parts, segment)

		if i < len(stages)-1 {
			parts = append(parts, arrow)
		}
	}

	var line string
	for _, p := range parts {
		line += p
	}

	// Title for the top of the border.
	title := lipgloss.NewStyle().
		Foreground(styles.TextSecondary).
		Bold(true).
		Render(" Pipeline ")

	panelStyle := lipgloss.NewStyle().
		Background(styles.BgPanel).
		Border(styles.RoundedBorder).
		BorderForeground(styles.BorderNormal).
		BorderTop(true).
		BorderBottom(true).
		BorderLeft(true).
		BorderRight(true).
		Padding(0, 1).
		Width(width - 2)

	content := panelStyle.Render(line)

	// Replace the top border segment with the title.
	// Find the first "──" after the top-left corner and inject the title.
	lines := splitLines(content)
	if len(lines) > 0 {
		topLine := lines[0]
		runes := []rune(topLine)
		if len(runes) > 4 {
			titleRunes := []rune(title)
			// Place title after the first 2 border characters.
			insertPos := 2
			end := insertPos + len(titleRunes)
			if end > len(runes) {
				end = len(runes)
			}
			newTop := make([]rune, len(runes))
			copy(newTop, runes)
			copy(newTop[insertPos:end], titleRunes)
			lines[0] = string(newTop)
		}
		return joinLines(lines)
	}

	return content
}
