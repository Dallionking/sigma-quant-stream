package views

import (
	"fmt"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/models"
)

// RunOnboarding launches the interactive onboarding wizard TUI. It blocks until
// the user completes or cancels the wizard. When explainMode is true, educational
// annotations are shown at every step.
func RunOnboarding(explainMode bool, projectRoot string) error {
	model := models.NewWizardModel(projectRoot, explainMode)
	p := tea.NewProgram(model, tea.WithAltScreen())

	finalModel, err := p.Run()
	if err != nil {
		return fmt.Errorf("onboarding wizard failed: %w", err)
	}

	_ = finalModel
	return nil
}

// RunOnboardingWizard is an alias preserved for backward compatibility with
// callers that use the older function signature (projectRoot, explain).
//
// The wizard walks through 7 steps:
//  1. Welcome       -- logo + "Press Enter to begin"
//  2. Path Select   -- developer or trader
//  3. Markets       -- futures, crypto CEX/DEX (multi-select)
//  4. API Keys      -- conditional text inputs
//  5. Data Download -- per-symbol progress bars
//  6. Health Check  -- run health.Checker.RunAll()
//  7. Ready         -- summary + next steps
func RunOnboardingWizard(projectRoot string, explain bool) error {
	return RunOnboarding(explain, projectRoot)
}
