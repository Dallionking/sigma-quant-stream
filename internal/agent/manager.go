package agent

import (
	"context"
	"fmt"
	"path/filepath"
	"sync"
	"time"
)

// WorkerType enumerates the 4 worker types.
type WorkerType string

const (
	Researcher WorkerType = "researcher"
	Converter  WorkerType = "converter"
	Backtester WorkerType = "backtester"
	Optimizer  WorkerType = "optimizer"
)

// AllWorkerTypes returns all worker types in pipeline order.
func AllWorkerTypes() []WorkerType {
	return []WorkerType{Researcher, Converter, Backtester, Optimizer}
}

// WorkerState represents the current state of a worker.
type WorkerState int

const (
	StateStopped WorkerState = iota
	StateStarting
	StateRunning
	StateIdle
	StateStopping
	StateError
)

// String returns a human-readable label for the state.
func (s WorkerState) String() string {
	switch s {
	case StateStopped:
		return "stopped"
	case StateStarting:
		return "starting"
	case StateRunning:
		return "running"
	case StateIdle:
		return "idle"
	case StateStopping:
		return "stopping"
	case StateError:
		return "error"
	default:
		return "unknown"
	}
}

// paneForWorker maps a worker type to its pane index inside the 2x2 grid.
func paneForWorker(wt WorkerType) int {
	switch wt {
	case Researcher:
		return 0
	case Converter:
		return 1
	case Backtester:
		return 2
	case Optimizer:
		return 3
	default:
		return -1
	}
}

// RunningWorker tracks a live worker.
type RunningWorker struct {
	Type           WorkerType
	Pane           int
	State          WorkerState
	SessionsRun    int
	TasksCompleted int
	CurrentTask    string
	LastError      string
	StartedAt      time.Time
}

// Manager orchestrates all workers in a tmux session.
type Manager struct {
	mu           sync.RWMutex
	sessionName  string
	workers      map[WorkerType]*RunningWorker
	tmux         *TmuxClient
	basePath     string
	claudeBinary string
	promptsDir   string
	scriptsDir   string
	mode         string // "research" or "production"
}

// NewManager creates a new agent manager rooted at basePath.
func NewManager(basePath, sessionName string) *Manager {
	return &Manager{
		sessionName:  sessionName,
		workers:      make(map[WorkerType]*RunningWorker),
		tmux:         NewTmuxClient(),
		basePath:     basePath,
		claudeBinary: "claude",
		promptsDir:   filepath.Join(basePath, "prompts"),
		scriptsDir:   filepath.Join(basePath, "scripts"),
		mode:         "research",
	}
}

// SetMode configures the operational mode ("research" or "production").
func (m *Manager) SetMode(mode string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.mode = mode
}

// StartAll launches all 4 workers in tmux panes.
//
// 1. Creates a tmux session with the configured name.
// 2. Splits into a 2x2 grid (4 panes).
// 3. Sends the ralph loop command to each pane.
// 4. Tracks each worker as StateStarting -> StateRunning.
func (m *Manager) StartAll(ctx context.Context) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	// If session already exists, refuse to double-start.
	if m.tmux.SessionExists(m.sessionName) {
		return fmt.Errorf("tmux session %q already exists", m.sessionName)
	}

	// Create the session.
	if err := m.tmux.CreateSession(m.sessionName); err != nil {
		return fmt.Errorf("creating tmux session: %w", err)
	}

	// Build the 2x2 grid.
	if err := m.tmux.CreateGridLayout(m.sessionName); err != nil {
		// Best-effort cleanup.
		_ = m.tmux.KillSession(m.sessionName)
		return fmt.Errorf("creating grid layout: %w", err)
	}

	// Launch each worker.
	for _, wt := range AllWorkerTypes() {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		pane := paneForWorker(wt)
		if err := m.launchWorker(wt, pane); err != nil {
			return fmt.Errorf("launching worker %s in pane %d: %w", wt, pane, err)
		}
	}

	return nil
}

// StartWorker launches a single worker. The tmux session must already exist.
func (m *Manager) StartWorker(ctx context.Context, wt WorkerType) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if !m.tmux.SessionExists(m.sessionName) {
		return fmt.Errorf("tmux session %q does not exist; call StartAll first", m.sessionName)
	}

	// If already running, bail.
	if w, ok := m.workers[wt]; ok && w.State == StateRunning {
		return fmt.Errorf("worker %s is already running", wt)
	}

	pane := paneForWorker(wt)
	return m.launchWorker(wt, pane)
}

// launchWorker sends the ralph loop command to a pane and records state.
// Caller must hold m.mu.
func (m *Manager) launchWorker(wt WorkerType, pane int) error {
	m.workers[wt] = &RunningWorker{
		Type:      wt,
		Pane:      pane,
		State:     StateStarting,
		StartedAt: time.Now(),
	}

	// Build the command. We use the ralph loop script when available,
	// falling back to a direct claude invocation.
	cmd := m.buildWorkerCommand(wt, pane)

	if err := m.tmux.SendKeys(m.sessionName, pane, cmd); err != nil {
		m.workers[wt].State = StateError
		m.workers[wt].LastError = err.Error()
		return err
	}

	m.workers[wt].State = StateRunning
	return nil
}

// buildWorkerCommand returns the shell command to run in a pane.
func (m *Manager) buildWorkerCommand(wt WorkerType, pane int) string {
	ralphScript := filepath.Join(m.scriptsDir, "quant-ralph.sh")
	// Use the ralph loop: bash scripts/quant-ralph.sh <pane_id> <worker_type> <mode>
	return fmt.Sprintf("bash %s %d %s %s", ralphScript, pane, string(wt), m.mode)
}

// StopAll gracefully stops all workers then kills the tmux session.
//
// 1. Sends Ctrl-C to every pane.
// 2. Waits up to 10 seconds for graceful shutdown.
// 3. Kills the tmux session if any worker has not stopped.
func (m *Manager) StopAll() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if !m.tmux.SessionExists(m.sessionName) {
		// Nothing to stop.
		m.clearWorkers()
		return nil
	}

	// Mark all as stopping and send Ctrl-C.
	for wt, w := range m.workers {
		w.State = StateStopping
		_ = m.tmux.SendKeys(m.sessionName, w.Pane, "C-c")
		_ = wt // satisfy linter
	}

	// Wait up to 10 seconds for graceful exit.
	deadline := time.Now().Add(10 * time.Second)
	for time.Now().Before(deadline) {
		if !m.tmux.SessionExists(m.sessionName) {
			m.clearWorkers()
			return nil
		}
		time.Sleep(500 * time.Millisecond)
	}

	// Force kill.
	err := m.tmux.KillSession(m.sessionName)
	m.clearWorkers()
	return err
}

// StopWorker stops a single worker by sending Ctrl-C to its pane.
func (m *Manager) StopWorker(wt WorkerType) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	w, ok := m.workers[wt]
	if !ok {
		return fmt.Errorf("worker %s is not tracked", wt)
	}

	w.State = StateStopping
	if err := m.tmux.SendKeys(m.sessionName, w.Pane, "C-c"); err != nil {
		return fmt.Errorf("sending Ctrl-C to pane %d: %w", w.Pane, err)
	}

	// Give a moment for the signal to propagate, then mark stopped.
	go func() {
		time.Sleep(5 * time.Second)
		m.mu.Lock()
		defer m.mu.Unlock()
		if w.State == StateStopping {
			w.State = StateStopped
		}
	}()

	return nil
}

// GetWorkerStates returns a snapshot of all tracked workers.
func (m *Manager) GetWorkerStates() map[WorkerType]*RunningWorker {
	m.mu.RLock()
	defer m.mu.RUnlock()

	out := make(map[WorkerType]*RunningWorker, len(m.workers))
	for k, v := range m.workers {
		// Return a copy so callers don't race.
		cp := *v
		out[k] = &cp
	}
	return out
}

// IsRunning checks if the tmux session is active.
func (m *Manager) IsRunning() bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.tmux.SessionExists(m.sessionName)
}

// SessionName returns the tmux session name.
func (m *Manager) SessionName() string {
	return m.sessionName
}

// clearWorkers resets every tracked worker to stopped. Caller must hold m.mu.
func (m *Manager) clearWorkers() {
	for _, w := range m.workers {
		w.State = StateStopped
	}
}
