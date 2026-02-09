package agent

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// PromptResolver loads and templates worker prompt files from the prompts
// directory. Each worker type has a corresponding markdown file
// (e.g., prompts/researcher.md).
type PromptResolver struct {
	promptsDir string
}

// NewPromptResolver creates a PromptResolver rooted at the given directory.
func NewPromptResolver(dir string) *PromptResolver {
	return &PromptResolver{promptsDir: dir}
}

// Resolve reads the prompt file for the given workerType and replaces
// template variables ({{KEY}}) with values from vars.
//
// Supported template variables:
//   - {{PROFILE}}     -- Active market profile name or path.
//   - {{DATA_DIR}}    -- Path to the data directory.
//   - {{COST_MODEL}}  -- Cost model identifier (e.g., "per_contract").
//   - {{MARKET_TYPE}} -- Market type (e.g., "futures", "crypto").
//
// Any additional keys in vars are also substituted.
func (pr *PromptResolver) Resolve(workerType WorkerType, vars map[string]string) (string, error) {
	path := pr.GetPromptPath(workerType)

	data, err := os.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("reading prompt file %s: %w", path, err)
	}

	content := string(data)

	// Replace each template variable.
	for key, value := range vars {
		placeholder := "{{" + strings.ToUpper(key) + "}}"
		content = strings.ReplaceAll(content, placeholder, value)
	}

	return content, nil
}

// GetPromptPath returns the file path for a worker's prompt markdown file.
func (pr *PromptResolver) GetPromptPath(workerType WorkerType) string {
	filename := string(workerType) + ".md"
	return filepath.Join(pr.promptsDir, filename)
}

// PromptExists returns true if the prompt file for the worker type exists
// on disk.
func (pr *PromptResolver) PromptExists(workerType WorkerType) bool {
	path := pr.GetPromptPath(workerType)
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}

// AllPromptsExist checks that every worker type has a prompt file and
// returns the list of missing ones (if any).
func (pr *PromptResolver) AllPromptsExist() []WorkerType {
	var missing []WorkerType
	for _, wt := range AllWorkerTypes() {
		if !pr.PromptExists(wt) {
			missing = append(missing, wt)
		}
	}
	return missing
}
