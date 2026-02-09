package health

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
)

// registerChecks registers all 16 health checks across four categories.
func (c *Checker) registerChecks() {
	// System checks
	c.add("python3", "system", c.checkPython)
	c.add("pip", "system", c.checkPip)
	c.add("python-packages", "system", c.checkPythonPackages)
	c.add("tmux", "system", c.checkTmux)
	c.add("claude-cli", "system", c.checkClaudeCLI)
	c.add("git", "system", c.checkGit)

	// Project checks
	c.add("config-json", "project", c.checkConfigJSON)
	c.add("active-profile", "project", c.checkActiveProfile)
	c.add("worker-prompts", "project", c.checkWorkerPrompts)
	c.add("agent-definitions", "project", c.checkAgentDefinitions)
	c.add("skills", "project", c.checkSkills)
	c.add("queue-dirs", "project", c.checkQueueDirs)
	c.add("output-dirs", "project", c.checkOutputDirs)

	// Data checks
	c.add("data-files", "data", c.checkDataFiles)
	c.add("api-keys", "data", c.checkAPIKeys)

	// Runtime checks
	c.add("stale-sessions", "runtime", c.checkStaleSessions)
}

// ---------------------------------------------------------------------------
// System checks
// ---------------------------------------------------------------------------

func (c *Checker) checkPython(ctx context.Context) CheckResult {
	out, err := exec.CommandContext(ctx, "python3", "--version").CombinedOutput()
	if err != nil {
		return CheckResult{Status: StatusFail, Message: "python3 not found"}
	}
	version := strings.TrimSpace(string(out))
	// Parse "Python 3.X.Y" and verify >= 3.9
	parts := strings.Fields(version)
	if len(parts) < 2 {
		return CheckResult{Status: StatusWarn, Message: fmt.Sprintf("unexpected version string: %s", version)}
	}
	nums := strings.Split(parts[1], ".")
	if len(nums) < 2 {
		return CheckResult{Status: StatusWarn, Message: fmt.Sprintf("cannot parse version: %s", parts[1])}
	}
	major, errMaj := strconv.Atoi(nums[0])
	minor, errMin := strconv.Atoi(nums[1])
	if errMaj != nil || errMin != nil {
		return CheckResult{Status: StatusWarn, Message: fmt.Sprintf("cannot parse version numbers: %s", parts[1])}
	}
	if major < 3 || (major == 3 && minor < 9) {
		return CheckResult{Status: StatusFail, Message: fmt.Sprintf("%s (requires >= 3.9)", parts[1])}
	}
	return CheckResult{Status: StatusPass, Message: parts[1]}
}

func (c *Checker) checkPip(ctx context.Context) CheckResult {
	out, err := exec.CommandContext(ctx, "pip3", "--version").CombinedOutput()
	if err != nil {
		// Fall back to python3 -m pip
		out2, err2 := exec.CommandContext(ctx, "python3", "-m", "pip", "--version").CombinedOutput()
		if err2 != nil {
			return CheckResult{Status: StatusFail, Message: "pip not found (tried pip3 and python3 -m pip)"}
		}
		out = out2
	}
	ver := strings.TrimSpace(string(out))
	// First field is "pip X.Y.Z ..."
	fields := strings.Fields(ver)
	if len(fields) >= 2 {
		return CheckResult{Status: StatusPass, Message: fields[1]}
	}
	return CheckResult{Status: StatusPass, Message: ver}
}

func (c *Checker) checkPythonPackages(ctx context.Context) CheckResult {
	required := []string{"freqtrade", "pandas", "numpy"}
	missing := []string{}

	for _, pkg := range required {
		cmd := exec.CommandContext(ctx, "python3", "-c", fmt.Sprintf("import %s", pkg))
		if err := cmd.Run(); err != nil {
			missing = append(missing, pkg)
		}
	}

	if len(missing) == 0 {
		return CheckResult{Status: StatusPass, Message: fmt.Sprintf("all %d required packages found", len(required))}
	}
	if len(missing) == len(required) {
		return CheckResult{Status: StatusFail, Message: fmt.Sprintf("missing: %s", strings.Join(missing, ", "))}
	}
	return CheckResult{Status: StatusWarn, Message: fmt.Sprintf("missing: %s", strings.Join(missing, ", "))}
}

func (c *Checker) checkTmux(ctx context.Context) CheckResult {
	out, err := exec.CommandContext(ctx, "tmux", "-V").CombinedOutput()
	if err != nil {
		return CheckResult{Status: StatusFail, Message: "tmux not found"}
	}
	ver := strings.TrimSpace(string(out))
	return CheckResult{Status: StatusPass, Message: ver}
}

func (c *Checker) checkClaudeCLI(ctx context.Context) CheckResult {
	out, err := exec.CommandContext(ctx, "claude", "--version").CombinedOutput()
	if err != nil {
		return CheckResult{Status: StatusFail, Message: "claude CLI not found"}
	}
	ver := strings.TrimSpace(string(out))
	// Take first line only in case of multi-line output
	if idx := strings.IndexByte(ver, '\n'); idx > 0 {
		ver = ver[:idx]
	}
	return CheckResult{Status: StatusPass, Message: ver}
}

func (c *Checker) checkGit(ctx context.Context) CheckResult {
	out, err := exec.CommandContext(ctx, "git", "--version").CombinedOutput()
	if err != nil {
		return CheckResult{Status: StatusFail, Message: "git not found"}
	}
	ver := strings.TrimSpace(string(out))
	// "git version 2.X.Y"
	parts := strings.Fields(ver)
	if len(parts) >= 3 {
		return CheckResult{Status: StatusPass, Message: parts[2]}
	}
	return CheckResult{Status: StatusPass, Message: ver}
}

// ---------------------------------------------------------------------------
// Project checks
// ---------------------------------------------------------------------------

func (c *Checker) checkConfigJSON(ctx context.Context) CheckResult {
	cfgPath := filepath.Join(c.projectRoot, "config.json")
	data, err := os.ReadFile(cfgPath)
	if err != nil {
		return CheckResult{Status: StatusFail, Message: "config.json not found"}
	}
	var raw map[string]interface{}
	if err := json.Unmarshal(data, &raw); err != nil {
		return CheckResult{Status: StatusFail, Message: fmt.Sprintf("invalid JSON: %s", err)}
	}
	// Check for essential keys
	essentials := []string{"name", "version", "activeProfile", "workers"}
	missing := []string{}
	for _, k := range essentials {
		if _, ok := raw[k]; !ok {
			missing = append(missing, k)
		}
	}
	if len(missing) > 0 {
		return CheckResult{Status: StatusWarn, Message: fmt.Sprintf("missing keys: %s", strings.Join(missing, ", "))}
	}
	ver, _ := raw["version"].(string)
	return CheckResult{Status: StatusPass, Message: fmt.Sprintf("valid (v%s)", ver)}
}

func (c *Checker) checkActiveProfile(ctx context.Context) CheckResult {
	cfgPath := filepath.Join(c.projectRoot, "config.json")
	data, err := os.ReadFile(cfgPath)
	if err != nil {
		return CheckResult{Status: StatusFail, Message: "cannot read config.json"}
	}
	var raw map[string]interface{}
	if err := json.Unmarshal(data, &raw); err != nil {
		return CheckResult{Status: StatusFail, Message: "cannot parse config.json"}
	}
	profilePath, ok := raw["activeProfile"].(string)
	if !ok || profilePath == "" {
		return CheckResult{Status: StatusFail, Message: "activeProfile not set in config.json"}
	}
	absPath := profilePath
	if !filepath.IsAbs(absPath) {
		absPath = filepath.Join(c.projectRoot, absPath)
	}
	if _, err := os.Stat(absPath); err != nil {
		return CheckResult{Status: StatusFail, Message: fmt.Sprintf("profile not found: %s", profilePath)}
	}
	// Try to parse the profile
	profData, err := os.ReadFile(absPath)
	if err != nil {
		return CheckResult{Status: StatusWarn, Message: fmt.Sprintf("cannot read profile: %s", profilePath)}
	}
	var prof map[string]interface{}
	if err := json.Unmarshal(profData, &prof); err != nil {
		return CheckResult{Status: StatusWarn, Message: fmt.Sprintf("invalid profile JSON: %s", profilePath)}
	}
	name, _ := prof["profileId"].(string)
	if name == "" {
		name = filepath.Base(profilePath)
	}
	return CheckResult{Status: StatusPass, Message: name}
}

func (c *Checker) checkWorkerPrompts(ctx context.Context) CheckResult {
	prompts := []string{
		"prompts/researcher.md",
		"prompts/converter.md",
		"prompts/backtester.md",
		"prompts/optimizer.md",
	}
	missing := []string{}
	for _, p := range prompts {
		absPath := filepath.Join(c.projectRoot, p)
		if _, err := os.Stat(absPath); err != nil {
			missing = append(missing, filepath.Base(p))
		}
	}
	if len(missing) == 0 {
		return CheckResult{Status: StatusPass, Message: fmt.Sprintf("all %d prompts found", len(prompts))}
	}
	if len(missing) == len(prompts) {
		return CheckResult{Status: StatusFail, Message: fmt.Sprintf("missing: %s", strings.Join(missing, ", "))}
	}
	return CheckResult{Status: StatusWarn, Message: fmt.Sprintf("missing: %s", strings.Join(missing, ", "))}
}

func (c *Checker) checkAgentDefinitions(ctx context.Context) CheckResult {
	// Look for agent definition files (YAML/JSON) in common locations
	searchDirs := []string{
		filepath.Join(c.projectRoot, ".claude", "agents"),
		filepath.Join(c.projectRoot, "agents"),
	}
	found := 0
	searchedDir := ""
	for _, dir := range searchDirs {
		entries, err := os.ReadDir(dir)
		if err != nil {
			continue
		}
		searchedDir = dir
		for _, e := range entries {
			if e.IsDir() {
				continue
			}
			ext := strings.ToLower(filepath.Ext(e.Name()))
			if ext == ".yaml" || ext == ".yml" || ext == ".json" || ext == ".md" {
				found++
			}
		}
	}
	if found == 0 {
		return CheckResult{Status: StatusWarn, Message: "no agent definition files found"}
	}
	relDir := searchedDir
	if rel, err := filepath.Rel(c.projectRoot, searchedDir); err == nil {
		relDir = rel
	}
	return CheckResult{Status: StatusPass, Message: fmt.Sprintf("%d definitions in %s", found, relDir)}
}

func (c *Checker) checkSkills(ctx context.Context) CheckResult {
	skillsDirs := []string{
		filepath.Join(c.projectRoot, ".claude", "skills"),
		filepath.Join(c.projectRoot, "skills"),
	}
	found := 0
	for _, dir := range skillsDirs {
		entries, err := os.ReadDir(dir)
		if err != nil {
			continue
		}
		for _, e := range entries {
			ext := strings.ToLower(filepath.Ext(e.Name()))
			if ext == ".md" || e.IsDir() {
				found++
			}
		}
	}
	if found == 0 {
		return CheckResult{Status: StatusWarn, Message: "no skills found"}
	}
	return CheckResult{Status: StatusPass, Message: fmt.Sprintf("%d skill entries found", found)}
}

func (c *Checker) checkQueueDirs(ctx context.Context) CheckResult {
	queues := []string{
		"queues/hypotheses",
		"queues/to-convert",
		"queues/to-backtest",
		"queues/to-optimize",
	}
	missing := []string{}
	for _, q := range queues {
		absPath := filepath.Join(c.projectRoot, q)
		info, err := os.Stat(absPath)
		if err != nil || !info.IsDir() {
			missing = append(missing, filepath.Base(q))
		}
	}
	if len(missing) == 0 {
		return CheckResult{Status: StatusPass, Message: fmt.Sprintf("all %d queue dirs present", len(queues))}
	}
	if len(missing) == len(queues) {
		return CheckResult{Status: StatusFail, Message: fmt.Sprintf("missing: %s", strings.Join(missing, ", "))}
	}
	return CheckResult{Status: StatusWarn, Message: fmt.Sprintf("missing: %s", strings.Join(missing, ", "))}
}

func (c *Checker) checkOutputDirs(ctx context.Context) CheckResult {
	outputDirs := []string{
		"output/strategies/good",
		"output/strategies/under_review",
		"output/strategies/rejected",
		"output/strategies/prop_firm_ready",
		"output/indicators",
		"output/backtests",
		"output/research-logs",
	}
	missing := []string{}
	for _, d := range outputDirs {
		absPath := filepath.Join(c.projectRoot, d)
		info, err := os.Stat(absPath)
		if err != nil || !info.IsDir() {
			missing = append(missing, d)
		}
	}
	if len(missing) == 0 {
		return CheckResult{Status: StatusPass, Message: fmt.Sprintf("all %d output dirs present", len(outputDirs))}
	}
	if len(missing) == len(outputDirs) {
		return CheckResult{Status: StatusFail, Message: fmt.Sprintf("all %d output dirs missing", len(outputDirs))}
	}
	return CheckResult{Status: StatusWarn, Message: fmt.Sprintf("%d/%d output dirs missing", len(missing), len(outputDirs))}
}

// ---------------------------------------------------------------------------
// Data checks
// ---------------------------------------------------------------------------

func (c *Checker) checkDataFiles(ctx context.Context) CheckResult {
	dataDir := filepath.Join(c.projectRoot, "data")
	if _, err := os.Stat(dataDir); err != nil {
		return CheckResult{Status: StatusFail, Message: "data/ directory not found"}
	}

	csvCount := 0
	jsonCount := 0
	_ = filepath.WalkDir(dataDir, func(path string, d os.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return nil
		}
		ext := strings.ToLower(filepath.Ext(d.Name()))
		switch ext {
		case ".csv":
			csvCount++
		case ".json":
			jsonCount++
		}
		return nil
	})

	total := csvCount + jsonCount
	if total == 0 {
		return CheckResult{Status: StatusWarn, Message: "no CSV or JSON data files in data/"}
	}
	return CheckResult{Status: StatusPass, Message: fmt.Sprintf("%d CSV, %d JSON files", csvCount, jsonCount)}
}

func (c *Checker) checkAPIKeys(ctx context.Context) CheckResult {
	envPath := filepath.Join(c.projectRoot, ".env")
	f, err := os.Open(envPath)
	if err != nil {
		return CheckResult{Status: StatusWarn, Message: ".env not found (using sample data only)"}
	}
	defer f.Close()

	keys := make(map[string]bool)
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) == 2 && strings.TrimSpace(parts[1]) != "" {
			keys[strings.TrimSpace(parts[0])] = true
		}
	}

	// ANTHROPIC_API_KEY is always required
	if !keys["ANTHROPIC_API_KEY"] {
		return CheckResult{Status: StatusFail, Message: "ANTHROPIC_API_KEY not set in .env"}
	}

	// Check profile-specific keys based on active profile
	cfgPath := filepath.Join(c.projectRoot, "config.json")
	cfgData, _ := os.ReadFile(cfgPath)
	var raw map[string]interface{}
	_ = json.Unmarshal(cfgData, &raw)

	profilePath, _ := raw["activeProfile"].(string)
	warnings := []string{}

	if strings.Contains(profilePath, "futures") {
		if !keys["DATABENTO_API_KEY"] {
			warnings = append(warnings, "DATABENTO_API_KEY (needed for futures)")
		}
	}

	if len(warnings) > 0 {
		return CheckResult{Status: StatusWarn, Message: fmt.Sprintf("optional missing: %s", strings.Join(warnings, "; "))}
	}
	return CheckResult{Status: StatusPass, Message: fmt.Sprintf("%d keys configured", len(keys))}
}

// ---------------------------------------------------------------------------
// Runtime checks
// ---------------------------------------------------------------------------

func (c *Checker) checkStaleSessions(ctx context.Context) CheckResult {
	// Check if the "sigma-quant" tmux session exists
	out, err := exec.CommandContext(ctx, "tmux", "list-sessions", "-F", "#{session_name}").CombinedOutput()
	if err != nil {
		// tmux not running or no sessions -- that is fine
		return CheckResult{Status: StatusPass, Message: "no tmux sessions active"}
	}

	lines := strings.Split(strings.TrimSpace(string(out)), "\n")
	sessionFound := false
	for _, line := range lines {
		if strings.TrimSpace(line) == "sigma-quant" {
			sessionFound = true
			break
		}
	}

	if !sessionFound {
		return CheckResult{Status: StatusPass, Message: "no sigma-quant session found"}
	}

	// Session exists -- check if any panes are running a worker process
	panesOut, err := exec.CommandContext(ctx, "tmux", "list-panes", "-t", "sigma-quant", "-F", "#{pane_current_command}").CombinedOutput()
	if err != nil {
		return CheckResult{Status: StatusWarn, Message: "sigma-quant session exists but cannot inspect panes"}
	}

	paneCommands := strings.Split(strings.TrimSpace(string(panesOut)), "\n")
	activeWorkers := 0
	for _, cmd := range paneCommands {
		cmd = strings.TrimSpace(cmd)
		// Consider a worker active if the pane is running claude or python
		if cmd != "" && cmd != "bash" && cmd != "zsh" && cmd != "sh" {
			activeWorkers++
		}
	}

	if activeWorkers == 0 {
		return CheckResult{Status: StatusWarn, Message: "sigma-quant session exists but no workers running (stale?)"}
	}
	return CheckResult{Status: StatusPass, Message: fmt.Sprintf("sigma-quant session active with %d worker(s)", activeWorkers)}
}
