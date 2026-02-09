package agent

import (
	"context"
	"strings"
	"sync"
	"time"
)

// WorkerUpdate represents a status change detected by the monitor.
type WorkerUpdate struct {
	Type        WorkerType
	State       WorkerState
	CurrentTask string
	Output      string
}

// Monitor polls worker panes for status updates by capturing tmux output
// and scanning for known markers.
type Monitor struct {
	manager    *Manager
	interval   time.Duration
	updates    chan WorkerUpdate
	cancelFunc context.CancelFunc
	wg         sync.WaitGroup

	// lastOutput tracks the last captured output per worker to detect
	// stale panes (no change for a long period).
	mu             sync.Mutex
	lastOutput     map[WorkerType]string
	lastChangeTime map[WorkerType]time.Time
}

// staleThreshold is how long a pane can remain unchanged before the monitor
// flags it as potentially dead.
const staleThreshold = 60 * time.Second

// NewMonitor creates a Monitor that polls at the given interval.
func NewMonitor(m *Manager, interval time.Duration) *Monitor {
	return &Monitor{
		manager:        m,
		interval:       interval,
		updates:        make(chan WorkerUpdate, 64),
		lastOutput:     make(map[WorkerType]string),
		lastChangeTime: make(map[WorkerType]time.Time),
	}
}

// Start begins monitoring in a background goroutine. The returned channel
// emits WorkerUpdate values as they are detected. Close the context or
// call Stop to halt monitoring.
func (mon *Monitor) Start(ctx context.Context) <-chan WorkerUpdate {
	ctx, mon.cancelFunc = context.WithCancel(ctx)

	mon.wg.Add(1)
	go func() {
		defer mon.wg.Done()
		defer close(mon.updates)

		ticker := time.NewTicker(mon.interval)
		defer ticker.Stop()

		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				mon.poll()
			}
		}
	}()

	return mon.updates
}

// Stop halts monitoring and waits for the goroutine to exit.
func (mon *Monitor) Stop() {
	if mon.cancelFunc != nil {
		mon.cancelFunc()
	}
	mon.wg.Wait()
}

// poll captures each pane and parses its output for status markers.
func (mon *Monitor) poll() {
	states := mon.manager.GetWorkerStates()
	sessionName := mon.manager.SessionName()

	if !mon.manager.tmux.SessionExists(sessionName) {
		return
	}

	for wt, w := range states {
		if w.State == StateStopped {
			continue
		}

		output, err := mon.manager.tmux.CapturePane(sessionName, w.Pane)
		if err != nil {
			continue
		}

		update := mon.parseOutput(wt, output)
		if update != nil {
			// Apply state change back to the manager.
			mon.applyUpdate(wt, update)

			// Non-blocking send.
			select {
			case mon.updates <- *update:
			default:
			}
		}

		// Track staleness.
		mon.trackStaleness(wt, output)
	}
}

// parseOutput scans pane content for known markers and returns a
// WorkerUpdate if a meaningful state change is detected.
func (mon *Monitor) parseOutput(wt WorkerType, output string) *WorkerUpdate {
	lines := strings.Split(output, "\n")

	// Walk backwards for the most recent markers.
	for i := len(lines) - 1; i >= 0; i-- {
		line := strings.TrimSpace(lines[i])

		switch {
		case strings.Contains(line, "SESSION_COMPLETE"):
			return &WorkerUpdate{
				Type:   wt,
				State:  StateIdle,
				Output: line,
			}

		case strings.Contains(line, "SESSION_START") || strings.Contains(line, "Starting session"):
			return &WorkerUpdate{
				Type:   wt,
				State:  StateRunning,
				Output: line,
			}

		case strings.Contains(line, "TASK_START"):
			task := extractAfterMarker(line, "TASK_START")
			return &WorkerUpdate{
				Type:        wt,
				State:       StateRunning,
				CurrentTask: task,
				Output:      line,
			}

		case strings.Contains(line, "RALPH_MISSION_COMPLETE"):
			return &WorkerUpdate{
				Type:   wt,
				State:  StateStopped,
				Output: line,
			}

		case strings.Contains(line, "Budget limit reached") || strings.Contains(line, "Budget exceeded"):
			return &WorkerUpdate{
				Type:   wt,
				State:  StateStopped,
				Output: line,
			}

		case strings.Contains(line, "[ERROR]"):
			return &WorkerUpdate{
				Type:   wt,
				State:  StateError,
				Output: line,
			}
		}
	}

	return nil
}

// trackStaleness records the last time output changed for a worker and
// emits an error update if the pane has been static beyond staleThreshold.
func (mon *Monitor) trackStaleness(wt WorkerType, output string) {
	mon.mu.Lock()
	defer mon.mu.Unlock()

	prev, exists := mon.lastOutput[wt]
	now := time.Now()

	if !exists || output != prev {
		mon.lastOutput[wt] = output
		mon.lastChangeTime[wt] = now
		return
	}

	lastChange, ok := mon.lastChangeTime[wt]
	if ok && now.Sub(lastChange) > staleThreshold {
		// Output has not changed -- worker may be stuck or dead.
		select {
		case mon.updates <- WorkerUpdate{
			Type:   wt,
			State:  StateError,
			Output: "no output change for " + now.Sub(lastChange).Round(time.Second).String(),
		}:
		default:
		}
	}
}

// applyUpdate writes the detected state change back into the Manager.
func (mon *Monitor) applyUpdate(wt WorkerType, upd *WorkerUpdate) {
	mon.manager.mu.Lock()
	defer mon.manager.mu.Unlock()

	w, ok := mon.manager.workers[wt]
	if !ok {
		return
	}

	w.State = upd.State
	if upd.CurrentTask != "" {
		w.CurrentTask = upd.CurrentTask
	}
	if upd.State == StateIdle {
		w.SessionsRun++
	}
	if upd.State == StateError {
		w.LastError = upd.Output
	}
}

// extractAfterMarker returns the text after a marker word on the same line.
func extractAfterMarker(line, marker string) string {
	idx := strings.Index(line, marker)
	if idx < 0 {
		return ""
	}
	rest := strings.TrimSpace(line[idx+len(marker):])
	// Strip leading colon/dash if present.
	rest = strings.TrimLeft(rest, ":- ")
	return rest
}
