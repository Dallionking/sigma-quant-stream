package views

import (
	"fmt"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/models"
)

// RunStrategyBrowser launches the interactive Bubble Tea strategy browser.
// filter should be a category key ("good", "review", "rejected", "prop-firm",
// or "" for all). projectRoot is the absolute path to the sigma-quant project.
func RunStrategyBrowser(filter string, projectRoot string) error {
	model := models.NewStrategiesModel(filter, projectRoot)
	p := tea.NewProgram(model, tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		return fmt.Errorf("running strategy browser: %w", err)
	}
	return nil
}
