package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
)

// MarketProfile represents a fully loaded market profile JSON file.
type MarketProfile struct {
	Name       string                 `json:"profileId"`
	MarketType string                 `json:"marketType"`
	DataSource map[string]interface{} `json:"dataProvider"`
	CostModel  map[string]interface{} `json:"costs"`
	Compliance map[string]interface{} `json:"compliance"`
	Symbols    SymbolsConfig          `json:"symbols"`
}

// SymbolsConfig holds the symbol discovery and pinned symbol configuration.
type SymbolsConfig struct {
	Mode      string                 `json:"mode"`
	Discovery map[string]interface{} `json:"discovery"`
	Pinned    []string               `json:"pinned"`
	Excluded  []string               `json:"excluded"`
	Current   []string               `json:"current"`
}

// PinnedSymbols returns the list of pinned symbol strings for convenience.
func (mp *MarketProfile) PinnedSymbols() []string {
	return mp.Symbols.Pinned
}

// LoadProfile reads a market profile JSON file from an absolute or
// project-root-relative path.
func LoadProfile(profilePath string) (*MarketProfile, error) {
	// Resolve relative paths against the project root.
	if !filepath.IsAbs(profilePath) {
		root := Root()
		if root == "" {
			return nil, fmt.Errorf("cannot resolve relative profile path: project root not set")
		}
		profilePath = filepath.Join(root, profilePath)
	}

	data, err := os.ReadFile(profilePath)
	if err != nil {
		return nil, fmt.Errorf("reading profile %s: %w", profilePath, err)
	}

	var profile MarketProfile
	if err := json.Unmarshal(data, &profile); err != nil {
		return nil, fmt.Errorf("parsing profile %s: %w", profilePath, err)
	}

	return &profile, nil
}

// GetActiveProfile loads and returns the market profile referenced by
// config.activeProfile.
func GetActiveProfile() (*MarketProfile, error) {
	cfg := Get()
	if cfg.ActiveProfile == "" {
		return nil, fmt.Errorf("no activeProfile set in config")
	}
	return LoadProfile(cfg.ActiveProfile)
}

// ListProfiles returns all market profile references from the config, sorted
// alphabetically by key.
func ListProfiles() ([]MarketProfileRef, error) {
	cfg := Get()

	keys := make([]string, 0, len(cfg.MarketProfiles))
	for k := range cfg.MarketProfiles {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	refs := make([]MarketProfileRef, 0, len(keys))
	for _, k := range keys {
		refs = append(refs, cfg.MarketProfiles[k])
	}
	return refs, nil
}

// SwitchProfile updates the activeProfile field in config.json to point at
// the named profile. The name must be a key in marketProfiles.
func SwitchProfile(name string) error {
	cfg := Get()

	ref, ok := cfg.MarketProfiles[name]
	if !ok {
		available := make([]string, 0, len(cfg.MarketProfiles))
		for k := range cfg.MarketProfiles {
			available = append(available, k)
		}
		sort.Strings(available)
		return fmt.Errorf("profile %q not found; available: %v", name, available)
	}

	cfg.ActiveProfile = ref.Path
	return Save(cfg)
}
