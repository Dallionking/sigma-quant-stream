package views

import (
	"fmt"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/models"
)

// RunSetupClaude launches the interactive Claude Code setup wizard.
// It blocks until the user completes or cancels the wizard.
func RunSetupClaude(projectRoot string) error {
	m := models.NewSetupClaudeModel(projectRoot)
	p := tea.NewProgram(m, tea.WithAltScreen())

	finalModel, err := p.Run()
	if err != nil {
		return fmt.Errorf("setup wizard failed: %w", err)
	}

	// The final model is discarded -- all side effects happen during the TUI.
	_ = finalModel
	return nil
}
