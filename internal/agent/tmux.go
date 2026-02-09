package agent

import (
	"fmt"
	"os/exec"
	"strings"
)

// TmuxClient wraps tmux shell commands.
type TmuxClient struct{}

// NewTmuxClient creates a new TmuxClient.
func NewTmuxClient() *TmuxClient {
	return &TmuxClient{}
}

// run executes a tmux command and returns combined output.
func (t *TmuxClient) run(args ...string) (string, error) {
	cmd := exec.Command("tmux", args...)
	out, err := cmd.CombinedOutput()
	return strings.TrimSpace(string(out)), err
}

// SessionExists checks if a tmux session with the given name exists.
func (t *TmuxClient) SessionExists(name string) bool {
	_, err := t.run("has-session", "-t", name)
	return err == nil
}

// CreateSession creates a new detached tmux session.
func (t *TmuxClient) CreateSession(name string) error {
	_, err := t.run("new-session", "-d", "-s", name)
	if err != nil {
		return fmt.Errorf("tmux new-session: %w", err)
	}
	return nil
}

// KillSession kills a tmux session by name.
func (t *TmuxClient) KillSession(name string) error {
	_, err := t.run("kill-session", "-t", name)
	if err != nil {
		return fmt.Errorf("tmux kill-session: %w", err)
	}
	return nil
}

// SplitPane splits a pane in the given session.
// If vertical is true, the split is vertical (-v); otherwise horizontal (-h).
func (t *TmuxClient) SplitPane(session string, vertical bool) error {
	flag := "-h"
	if vertical {
		flag = "-v"
	}
	_, err := t.run("split-window", flag, "-t", session)
	if err != nil {
		return fmt.Errorf("tmux split-window %s: %w", flag, err)
	}
	return nil
}

// SendKeys sends keystrokes to a specific pane in a session.
// The keys string is sent literally; pass "C-c" for Ctrl-C, etc.
// A trailing Enter is appended automatically unless the key is a control sequence.
func (t *TmuxClient) SendKeys(session string, pane int, keys string) error {
	target := fmt.Sprintf("%s:%d.%d", session, 0, pane)

	// Control sequences (like C-c) should not get an Enter appended.
	if isControlKey(keys) {
		_, err := t.run("send-keys", "-t", target, keys)
		return err
	}

	_, err := t.run("send-keys", "-t", target, keys, "Enter")
	return err
}

// CapturePane captures the visible content of a pane.
func (t *TmuxClient) CapturePane(session string, pane int) (string, error) {
	target := fmt.Sprintf("%s:%d.%d", session, 0, pane)
	out, err := t.run("capture-pane", "-p", "-t", target)
	if err != nil {
		return "", fmt.Errorf("tmux capture-pane: %w", err)
	}
	return out, nil
}

// ListSessions lists all tmux session names.
func (t *TmuxClient) ListSessions() ([]string, error) {
	out, err := t.run("list-sessions", "-F", "#{session_name}")
	if err != nil {
		// If no server is running, tmux exits non-zero.
		if strings.Contains(out, "no server running") || strings.Contains(err.Error(), "exit status") {
			return nil, nil
		}
		return nil, fmt.Errorf("tmux list-sessions: %w", err)
	}
	if out == "" {
		return nil, nil
	}
	return strings.Split(out, "\n"), nil
}

// CreateGridLayout creates a 2x2 grid layout with 4 panes in the session.
//
// Starting from pane 0 (created with the session):
//   1. Split pane 0 horizontally -> panes 0, 1 (left | right)
//   2. Select pane 0, split vertically -> panes 0, 2 (top-left, bottom-left)
//   3. Select pane 1, split vertically -> panes 1, 3 (top-right, bottom-right)
//   4. Apply tiled layout for even sizing.
func (t *TmuxClient) CreateGridLayout(session string) error {
	// First horizontal split: left | right
	if err := t.SplitPane(session, false); err != nil {
		return fmt.Errorf("grid split 1: %w", err)
	}

	// Select pane 0 and split vertically.
	if err := t.SelectPane(session, 0); err != nil {
		return fmt.Errorf("grid select pane 0: %w", err)
	}
	if err := t.SplitPane(session, true); err != nil {
		return fmt.Errorf("grid split 2: %w", err)
	}

	// Select pane that was originally the right side (now pane 2 after previous split
	// shifted indices). We use tiled layout at the end for reliable positioning.
	// Split once more to get 4 total panes.
	if err := t.SelectPane(session, 2); err != nil {
		return fmt.Errorf("grid select pane 2: %w", err)
	}
	if err := t.SplitPane(session, true); err != nil {
		return fmt.Errorf("grid split 3: %w", err)
	}

	// Apply tiled layout for an even 2x2 grid.
	target := fmt.Sprintf("%s:%d", session, 0)
	if _, err := t.run("select-layout", "-t", target, "tiled"); err != nil {
		return fmt.Errorf("tmux select-layout tiled: %w", err)
	}

	return nil
}

// SelectPane focuses a specific pane in the session.
func (t *TmuxClient) SelectPane(session string, pane int) error {
	target := fmt.Sprintf("%s:%d.%d", session, 0, pane)
	_, err := t.run("select-pane", "-t", target)
	if err != nil {
		return fmt.Errorf("tmux select-pane %s: %w", target, err)
	}
	return nil
}

// isControlKey returns true if the key string looks like a tmux control
// sequence (e.g., "C-c", "C-d").
func isControlKey(keys string) bool {
	return len(keys) >= 2 && keys[0] == 'C' && keys[1] == '-'
}
