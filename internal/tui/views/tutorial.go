package views

import (
	"fmt"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/models"
)

// RunTutorial launches the interactive Bubble Tea tutorial.
// startStep is 0-based (0=Hypothesis, 5=Deploy). projectRoot is the absolute
// path to the sigma-quant project directory.
func RunTutorial(startStep int, projectRoot string) error {
	model := models.NewTutorialModel(startStep, projectRoot)
	p := tea.NewProgram(model, tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		return fmt.Errorf("running tutorial: %w", err)
	}
	return nil
}
