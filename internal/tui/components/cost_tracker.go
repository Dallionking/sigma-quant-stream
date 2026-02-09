package components

import (
	"fmt"
	"math"
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// CostTracker shows API cost information with a progress bar.
type CostTracker struct {
	CurrentCost float64
	BudgetCap   float64
	SessionCost float64
}

// Render returns the styled cost tracker.
func (c CostTracker) Render() string {
	ratio := 0.0
	if c.BudgetCap > 0 {
		ratio = c.CurrentCost / c.BudgetCap
	}

	// Pick color based on ratio.
	color := styles.StatusOK
	if ratio >= 0.80 {
		color = styles.StatusError
	} else if ratio >= 0.50 {
		color = styles.StatusWarn
	}

	// Cost text.
	costStyle := lipgloss.NewStyle().Foreground(color).Bold(true)
	capStyle := lipgloss.NewStyle().Foreground(styles.TextMuted)
	costLine := costStyle.Render(fmt.Sprintf("$%.2f", c.CurrentCost)) +
		capStyle.Render(fmt.Sprintf(" / $%.2f", c.BudgetCap))

	// Progress bar (20 chars wide).
	barWidth := 20
	filled := int(math.Round(ratio * float64(barWidth)))
	if filled > barWidth {
		filled = barWidth
	}
	if filled < 0 {
		filled = 0
	}
	empty := barWidth - filled

	filledStr := lipgloss.NewStyle().Foreground(color).Render(strings.Repeat("█", filled))
	emptyStr := lipgloss.NewStyle().Foreground(styles.TextMuted).Render(strings.Repeat("░", empty))
	bar := filledStr + emptyStr

	// Session cost note.
	sessionLine := lipgloss.NewStyle().Foreground(styles.TextMuted).
		Render(fmt.Sprintf("Session: $%.2f", c.SessionCost))

	return lipgloss.JoinVertical(lipgloss.Left,
		costLine,
		bar,
		sessionLine,
	)
}
