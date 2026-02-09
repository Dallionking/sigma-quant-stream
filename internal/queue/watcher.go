package queue

import (
	"context"
	"fmt"
	"path/filepath"
	"strings"
	"time"

	"github.com/fsnotify/fsnotify"
)

// Watcher monitors all queue directories for changes
type Watcher struct {
	queues    map[QueueName]*Queue
	watcher   *fsnotify.Watcher
	events    chan QueueEvent
	debounce  time.Duration
	rootDir   string
}

// NewWatcher creates a watcher for the given queue directories.
// It initializes Queue instances for all four pipeline queues and sets up
// fsnotify watches on each directory.
func NewWatcher(queuesRoot string) (*Watcher, error) {
	fsw, err := fsnotify.NewWatcher()
	if err != nil {
		return nil, fmt.Errorf("create fsnotify watcher: %w", err)
	}

	queues := make(map[QueueName]*Queue)
	for _, name := range AllQueues() {
		dir := filepath.Join(queuesRoot, string(name))
		q := NewQueue(name, dir)
		queues[name] = q

		if err := fsw.Add(dir); err != nil {
			fsw.Close()
			return nil, fmt.Errorf("watch directory %s: %w", dir, err)
		}
	}

	return &Watcher{
		queues:   queues,
		watcher:  fsw,
		events:   make(chan QueueEvent, 64),
		debounce: 100 * time.Millisecond,
		rootDir:  queuesRoot,
	}, nil
}

// Watch starts watching and returns a channel of queue events.
// Cancelling the context stops watching. The returned channel is closed
// when the context is cancelled or the watcher encounters a fatal error.
func (w *Watcher) Watch(ctx context.Context) <-chan QueueEvent {
	out := make(chan QueueEvent, 64)

	go func() {
		defer close(out)

		// Debounce timer to coalesce rapid filesystem events
		var debounceTimer *time.Timer
		var pendingEvents []fsnotify.Event

		resetDebounce := func() {
			if debounceTimer != nil {
				debounceTimer.Stop()
			}
			debounceTimer = time.NewTimer(w.debounce)
		}

		processPending := func() {
			// Deduplicate by directory -- we only need to re-scan each
			// affected queue once per debounce window
			seen := make(map[QueueName]bool)
			for _, ev := range pendingEvents {
				qName := w.dirToQueueName(ev.Name)
				if qName == "" || seen[QueueName(qName)] {
					continue
				}
				seen[QueueName(qName)] = true

				eventType := w.classifyEvent(ev)
				queueEvent := QueueEvent{
					Queue: QueueName(qName),
					Type:  eventType,
					Time:  time.Now(),
				}

				// Try to load the item for create/rename events
				if eventType == EventAdded || eventType == EventClaimed {
					if q, ok := w.queues[QueueName(qName)]; ok {
						id := w.extractID(ev.Name)
						if id != "" {
							if item, err := q.Get(id); err == nil {
								queueEvent.Item = item
							}
						}
					}
				}

				select {
				case out <- queueEvent:
				case <-ctx.Done():
					return
				}
			}
			pendingEvents = pendingEvents[:0]
		}

		// Initialize a stopped timer
		debounceTimer = time.NewTimer(0)
		if !debounceTimer.Stop() {
			<-debounceTimer.C
		}

		for {
			select {
			case <-ctx.Done():
				return

			case event, ok := <-w.watcher.Events:
				if !ok {
					return
				}
				// Skip temp files used for atomic writes
				if strings.Contains(filepath.Base(event.Name), ".tmp-") {
					continue
				}
				// Only care about JSON files
				if !strings.HasSuffix(event.Name, ".json") {
					continue
				}
				pendingEvents = append(pendingEvents, event)
				resetDebounce()

			case <-debounceTimer.C:
				if len(pendingEvents) > 0 {
					processPending()
				}

			case err, ok := <-w.watcher.Errors:
				if !ok {
					return
				}
				// Log errors but keep watching
				_ = err
			}
		}
	}()

	return out
}

// GetAllDepths returns current depth of all queues. This is a synchronous
// call that reads all queue directories immediately.
func (w *Watcher) GetAllDepths() ([]QueueDepth, error) {
	depths := make([]QueueDepth, 0, len(AllQueues()))
	for _, name := range AllQueues() {
		q, ok := w.queues[name]
		if !ok {
			continue
		}
		depth, err := q.Count()
		if err != nil {
			return nil, fmt.Errorf("count queue %s: %w", name, err)
		}
		depths = append(depths, depth)
	}
	return depths, nil
}

// GetQueue returns the Queue instance for a specific queue name.
func (w *Watcher) GetQueue(name QueueName) (*Queue, bool) {
	q, ok := w.queues[name]
	return q, ok
}

// Close stops watching and cleans up resources.
func (w *Watcher) Close() error {
	return w.watcher.Close()
}

// dirToQueueName maps a file path to its parent queue name.
func (w *Watcher) dirToQueueName(filePath string) string {
	dir := filepath.Dir(filePath)
	base := filepath.Base(dir)

	// Check if this is a top-level queue directory
	for _, name := range AllQueues() {
		if base == string(name) {
			return string(name)
		}
	}
	return ""
}

// classifyEvent determines the QueueEvent type from an fsnotify event.
func (w *Watcher) classifyEvent(ev fsnotify.Event) EventType {
	name := filepath.Base(ev.Name)

	switch {
	case ev.Has(fsnotify.Create):
		if strings.Contains(name, ".claimed-") {
			return EventClaimed
		}
		return EventAdded
	case ev.Has(fsnotify.Rename) || ev.Has(fsnotify.Remove):
		return EventRemoved
	case ev.Has(fsnotify.Write):
		if strings.Contains(name, ".claimed-") {
			return EventClaimed
		}
		return EventAdded
	default:
		return EventAdded
	}
}

// extractID pulls the item ID from a queue filename.
// Handles both "id.json" and "id.claimed-worker.json" formats.
func (w *Watcher) extractID(filePath string) string {
	base := filepath.Base(filePath)
	base = strings.TrimSuffix(base, ".json")

	// Handle claimed suffix: "id.claimed-worker"
	if idx := strings.Index(base, ".claimed-"); idx != -1 {
		return base[:idx]
	}

	return base
}
