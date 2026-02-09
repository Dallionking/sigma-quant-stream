package config

import (
	"fmt"
	"os"
	"path/filepath"
)

// ValidationError describes a single config validation failure.
type ValidationError struct {
	Field   string
	Message string
}

// Error implements the error interface for a single validation error.
func (ve ValidationError) Error() string {
	return fmt.Sprintf("%s: %s", ve.Field, ve.Message)
}

// Validate checks the Config for completeness and consistency. It returns a
// slice of all discovered issues rather than stopping at the first one.
func Validate(cfg *Config) []ValidationError {
	var errs []ValidationError

	// --- Required fields ---
	if cfg.Name == "" {
		errs = append(errs, ValidationError{Field: "name", Message: "required field is empty"})
	}
	if cfg.Version == "" {
		errs = append(errs, ValidationError{Field: "version", Message: "required field is empty"})
	}
	if cfg.ActiveProfile == "" {
		errs = append(errs, ValidationError{Field: "activeProfile", Message: "required field is empty"})
	}

	// --- Workers ---
	if cfg.Workers.Count <= 0 {
		errs = append(errs, ValidationError{
			Field:   "workers.count",
			Message: fmt.Sprintf("must be > 0, got %d", cfg.Workers.Count),
		})
	}
	if len(cfg.Workers.Types) == 0 {
		errs = append(errs, ValidationError{
			Field:   "workers.types",
			Message: "at least one worker type is required",
		})
	}

	// --- Strategy validation thresholds ---
	sv := cfg.Validation.Strategy

	if sv.MinSharpe >= sv.MaxSharpe {
		errs = append(errs, ValidationError{
			Field:   "validation.strategy.minSharpe / maxSharpe",
			Message: fmt.Sprintf("minSharpe (%.2f) must be less than maxSharpe (%.2f)", sv.MinSharpe, sv.MaxSharpe),
		})
	}
	if sv.GoodSharpe < sv.MinSharpe || sv.GoodSharpe > sv.MaxSharpe {
		errs = append(errs, ValidationError{
			Field:   "validation.strategy.goodSharpe",
			Message: fmt.Sprintf("goodSharpe (%.2f) must be between minSharpe (%.2f) and maxSharpe (%.2f)", sv.GoodSharpe, sv.MinSharpe, sv.MaxSharpe),
		})
	}

	if sv.MaxDrawdown <= 0 || sv.MaxDrawdown > 1 {
		errs = append(errs, ValidationError{
			Field:   "validation.strategy.maxDrawdown",
			Message: fmt.Sprintf("must be in (0, 1], got %.2f", sv.MaxDrawdown),
		})
	}
	if sv.GoodMaxDrawdown > sv.MaxDrawdown {
		errs = append(errs, ValidationError{
			Field:   "validation.strategy.goodMaxDrawdown",
			Message: fmt.Sprintf("goodMaxDrawdown (%.2f) should be <= maxDrawdown (%.2f)", sv.GoodMaxDrawdown, sv.MaxDrawdown),
		})
	}
	if sv.RejectMaxDrawdown < sv.MaxDrawdown {
		errs = append(errs, ValidationError{
			Field:   "validation.strategy.rejectMaxDrawdown",
			Message: fmt.Sprintf("rejectMaxDrawdown (%.2f) should be >= maxDrawdown (%.2f)", sv.RejectMaxDrawdown, sv.MaxDrawdown),
		})
	}

	if sv.MinTrades <= 0 {
		errs = append(errs, ValidationError{
			Field:   "validation.strategy.minTrades",
			Message: fmt.Sprintf("must be > 0, got %d", sv.MinTrades),
		})
	}
	if sv.GoodMinTrades < sv.MinTrades {
		errs = append(errs, ValidationError{
			Field:   "validation.strategy.goodMinTrades",
			Message: fmt.Sprintf("goodMinTrades (%d) should be >= minTrades (%d)", sv.GoodMinTrades, sv.MinTrades),
		})
	}

	if sv.MaxWinRate <= 0 || sv.MaxWinRate > 1 {
		errs = append(errs, ValidationError{
			Field:   "validation.strategy.maxWinRate",
			Message: fmt.Sprintf("must be in (0, 1], got %.2f", sv.MaxWinRate),
		})
	}

	if sv.MaxOosDecay < 0 || sv.MaxOosDecay > 1 {
		errs = append(errs, ValidationError{
			Field:   "validation.strategy.maxOosDecay",
			Message: fmt.Sprintf("must be in [0, 1], got %.2f", sv.MaxOosDecay),
		})
	}
	if sv.RejectOosDecay < sv.MaxOosDecay {
		errs = append(errs, ValidationError{
			Field:   "validation.strategy.rejectOosDecay",
			Message: fmt.Sprintf("rejectOosDecay (%.2f) should be >= maxOosDecay (%.2f)", sv.RejectOosDecay, sv.MaxOosDecay),
		})
	}

	if cfg.Validation.PropFirmMinPassing <= 0 {
		errs = append(errs, ValidationError{
			Field:   "validation.propFirmMinPassing",
			Message: fmt.Sprintf("must be > 0, got %d", cfg.Validation.PropFirmMinPassing),
		})
	}

	// --- Modes ---
	if len(cfg.Modes) == 0 {
		errs = append(errs, ValidationError{
			Field:   "modes",
			Message: "at least one mode must be defined",
		})
	}
	if cfg.Defaults.Mode != "" {
		if _, ok := cfg.Modes[cfg.Defaults.Mode]; !ok {
			errs = append(errs, ValidationError{
				Field:   "defaults.mode",
				Message: fmt.Sprintf("references undefined mode %q", cfg.Defaults.Mode),
			})
		}
	}

	// --- File existence checks (only when project root is set) ---
	root := Root()
	if root != "" {
		// Active profile path.
		if cfg.ActiveProfile != "" {
			profileAbs := cfg.ActiveProfile
			if !filepath.IsAbs(profileAbs) {
				profileAbs = filepath.Join(root, profileAbs)
			}
			if _, err := os.Stat(profileAbs); err != nil {
				errs = append(errs, ValidationError{
					Field:   "activeProfile",
					Message: fmt.Sprintf("file not found: %s", profileAbs),
				})
			}
		}

		// Prompt files.
		for workerType, promptPath := range cfg.Workers.Prompts {
			promptAbs := promptPath
			if !filepath.IsAbs(promptAbs) {
				promptAbs = filepath.Join(root, promptAbs)
			}
			if _, err := os.Stat(promptAbs); err != nil {
				errs = append(errs, ValidationError{
					Field:   fmt.Sprintf("workers.prompts.%s", workerType),
					Message: fmt.Sprintf("prompt file not found: %s", promptAbs),
				})
			}
		}
	}

	// --- Recovery ---
	if cfg.Recovery.MaxConsecutiveFailures <= 0 {
		errs = append(errs, ValidationError{
			Field:   "recovery.maxConsecutiveFailures",
			Message: fmt.Sprintf("must be > 0, got %d", cfg.Recovery.MaxConsecutiveFailures),
		})
	}

	return errs
}
