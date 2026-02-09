package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
)

// Config represents the full config.json schema for Sigma-Quant Stream.
type Config struct {
	Name          string                    `json:"name" mapstructure:"name"`
	Version       string                    `json:"version" mapstructure:"version"`
	Description   string                    `json:"description" mapstructure:"description"`
	Architecture  string                    `json:"architecture" mapstructure:"architecture"`
	ActiveProfile string                    `json:"activeProfile" mapstructure:"activeProfile"`
	MarketProfiles map[string]MarketProfileRef `json:"marketProfiles" mapstructure:"marketProfiles"`
	Defaults      Defaults                  `json:"defaults" mapstructure:"defaults"`
	Modes         map[string]Mode           `json:"modes" mapstructure:"modes"`
	Workers       WorkersConfig             `json:"workers" mapstructure:"workers"`
	Queues        QueuesConfig              `json:"queues" mapstructure:"queues"`
	Patterns      PatternsConfig            `json:"patterns" mapstructure:"patterns"`
	Validation    ValidationConfig          `json:"validation" mapstructure:"validation"`
	Output        OutputConfig              `json:"output" mapstructure:"output"`
	Recovery      RecoveryConfig            `json:"recovery" mapstructure:"recovery"`
	Notifications NotificationsConfig       `json:"notifications" mapstructure:"notifications"`
}

// MarketProfileRef is a reference to a market profile file.
type MarketProfileRef struct {
	Path        string `json:"path" mapstructure:"path"`
	DisplayName string `json:"displayName" mapstructure:"displayName"`
	MarketType  string `json:"marketType" mapstructure:"marketType"`
}

// Defaults holds the default runtime settings.
type Defaults struct {
	Panes    int    `json:"panes" mapstructure:"panes"`
	Mode     string `json:"mode" mapstructure:"mode"`
	MaxHours int    `json:"maxHours" mapstructure:"maxHours"`
	Notify   string `json:"notify" mapstructure:"notify"`
}

// Mode configures a specific operational mode (research vs production).
type Mode struct {
	SessionTimeout int     `json:"sessionTimeout" mapstructure:"sessionTimeout"`
	BudgetCap      float64 `json:"budgetCap" mapstructure:"budgetCap"`
	DataSource     string  `json:"dataSource" mapstructure:"dataSource"`
}

// WorkersConfig defines the worker pane layout and prompt assignments.
type WorkersConfig struct {
	Count   int               `json:"count" mapstructure:"count"`
	Types   []string          `json:"types" mapstructure:"types"`
	Layout  map[string]string `json:"layout" mapstructure:"layout"`
	Prompts map[string]string `json:"prompts" mapstructure:"prompts"`
}

// QueuesConfig maps queue names to their filesystem directories.
type QueuesConfig struct {
	Hypotheses string `json:"hypotheses" mapstructure:"hypotheses"`
	ToConvert  string `json:"toConvert" mapstructure:"toConvert"`
	ToBacktest string `json:"toBacktest" mapstructure:"toBacktest"`
	ToOptimize string `json:"toOptimize" mapstructure:"toOptimize"`
}

// PatternsConfig maps pattern categories to their markdown files.
type PatternsConfig struct {
	WhatWorks       string `json:"whatWorks" mapstructure:"whatWorks"`
	WhatFails       string `json:"whatFails" mapstructure:"whatFails"`
	IndicatorCombos string `json:"indicatorCombos" mapstructure:"indicatorCombos"`
	PropFirmGotchas string `json:"propFirmGotchas" mapstructure:"propFirmGotchas"`
}

// StrategyValidation holds threshold values for evaluating strategy quality.
type StrategyValidation struct {
	MinSharpe         float64 `json:"minSharpe" mapstructure:"minSharpe"`
	GoodSharpe        float64 `json:"goodSharpe" mapstructure:"goodSharpe"`
	MaxSharpe         float64 `json:"maxSharpe" mapstructure:"maxSharpe"`
	MaxDrawdown       float64 `json:"maxDrawdown" mapstructure:"maxDrawdown"`
	GoodMaxDrawdown   float64 `json:"goodMaxDrawdown" mapstructure:"goodMaxDrawdown"`
	RejectMaxDrawdown float64 `json:"rejectMaxDrawdown" mapstructure:"rejectMaxDrawdown"`
	MinTrades         int     `json:"minTrades" mapstructure:"minTrades"`
	GoodMinTrades     int     `json:"goodMinTrades" mapstructure:"goodMinTrades"`
	MaxWinRate        float64 `json:"maxWinRate" mapstructure:"maxWinRate"`
	MaxOosDecay       float64 `json:"maxOosDecay" mapstructure:"maxOosDecay"`
	RejectOosDecay    float64 `json:"rejectOosDecay" mapstructure:"rejectOosDecay"`
}

// ValidationConfig groups all validation thresholds.
type ValidationConfig struct {
	Strategy           StrategyValidation `json:"strategy" mapstructure:"strategy"`
	PropFirmMinPassing int                `json:"propFirmMinPassing" mapstructure:"propFirmMinPassing"`
}

// OutputConfig describes output directory structure and retention policies.
type OutputConfig struct {
	Directories   map[string]interface{} `json:"directories" mapstructure:"directories"`
	RetentionDays map[string]int         `json:"retentionDays" mapstructure:"retentionDays"`
}

// RecoveryConfig controls checkpoint and crash recovery behaviour.
type RecoveryConfig struct {
	CheckpointAfterEachSession bool   `json:"checkpointAfterEachSession" mapstructure:"checkpointAfterEachSession"`
	CheckpointDir              string `json:"checkpointDir" mapstructure:"checkpointDir"`
	MaxConsecutiveFailures     int    `json:"maxConsecutiveFailures" mapstructure:"maxConsecutiveFailures"`
	AutoResume                 bool   `json:"autoResume" mapstructure:"autoResume"`
}

// NotificationsConfig holds notification provider settings.
type NotificationsConfig struct {
	ElevenLabs map[string]interface{} `json:"elevenlabs" mapstructure:"elevenlabs"`
	Fallback   string                 `json:"fallback" mapstructure:"fallback"`
}

// singleton holds the global loaded config and the project root path.
var (
	globalCfg  *Config
	globalRoot string
	mu         sync.RWMutex
)

// Load reads config.json from the given project root directory. It caches
// the result so that subsequent calls to Get() return immediately.
func Load(projectRoot string) (*Config, error) {
	cfgPath := filepath.Join(projectRoot, "config.json")

	data, err := os.ReadFile(cfgPath)
	if err != nil {
		return nil, fmt.Errorf("reading config.json: %w", err)
	}

	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("parsing config.json: %w", err)
	}

	mu.Lock()
	globalCfg = &cfg
	globalRoot = projectRoot
	mu.Unlock()

	return &cfg, nil
}

// Get returns the cached global config. It panics if Load has not been called.
func Get() *Config {
	mu.RLock()
	defer mu.RUnlock()

	if globalCfg == nil {
		panic("config.Get() called before config.Load()")
	}
	return globalCfg
}

// Root returns the project root directory set during Load.
func Root() string {
	mu.RLock()
	defer mu.RUnlock()
	return globalRoot
}

// Save writes the provided config back to config.json in the project root.
func Save(cfg *Config) error {
	mu.RLock()
	root := globalRoot
	mu.RUnlock()

	if root == "" {
		return fmt.Errorf("cannot save: project root not set (call Load first)")
	}

	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return fmt.Errorf("marshalling config: %w", err)
	}

	cfgPath := filepath.Join(root, "config.json")
	if err := os.WriteFile(cfgPath, append(data, '\n'), 0644); err != nil {
		return fmt.Errorf("writing config.json: %w", err)
	}

	mu.Lock()
	globalCfg = cfg
	mu.Unlock()

	return nil
}

// GetActiveMode returns the Mode matching defaults.mode. Returns nil if the
// mode name is not found in the modes map.
func GetActiveMode() *Mode {
	cfg := Get()
	modeName := cfg.Defaults.Mode
	if m, ok := cfg.Modes[modeName]; ok {
		return &m
	}
	return nil
}
