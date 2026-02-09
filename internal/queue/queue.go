package queue

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// Queue manages a single queue directory
type Queue struct {
	name QueueName
	dir  string
}

// NewQueue creates a new Queue for the given name and directory.
// It ensures the directory and its completed/failed subdirectories exist.
func NewQueue(name QueueName, dir string) *Queue {
	_ = os.MkdirAll(dir, 0o755)
	_ = os.MkdirAll(filepath.Join(dir, "completed"), 0o755)
	_ = os.MkdirAll(filepath.Join(dir, "failed"), 0o755)
	return &Queue{name: name, dir: dir}
}

// List returns all items in the queue, sorted by priority then timestamp.
// Only reads .json files from the top-level queue directory (not subdirs).
func (q *Queue) List() ([]QueueItem, error) {
	entries, err := os.ReadDir(q.dir)
	if err != nil {
		return nil, fmt.Errorf("read queue dir %s: %w", q.dir, err)
	}

	var items []QueueItem
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		name := entry.Name()
		if !strings.HasSuffix(name, ".json") {
			continue
		}

		item, err := q.readItemFile(filepath.Join(q.dir, name))
		if err != nil {
			continue // skip malformed files
		}
		items = append(items, *item)
	}

	sort.Slice(items, func(i, j int) bool {
		pi := priorityRank(items[i].Priority)
		pj := priorityRank(items[j].Priority)
		if pi != pj {
			return pi < pj // lower rank = higher priority
		}
		return items[i].CreatedAt.Before(items[j].CreatedAt)
	})

	return items, nil
}

// Count returns the depth summary for this queue.
func (q *Queue) Count() (QueueDepth, error) {
	items, err := q.List()
	if err != nil {
		return QueueDepth{Name: q.name}, err
	}

	depth := QueueDepth{
		Name:  q.name,
		Total: len(items),
	}
	for _, item := range items {
		switch item.Status {
		case StatusPending:
			depth.Pending++
		case StatusInProgress:
			depth.Claimed++
		}
	}
	return depth, nil
}

// Get retrieves a single item by ID. Searches all .json files in the queue
// directory for a matching ID.
func (q *Queue) Get(id string) (*QueueItem, error) {
	// Try direct filename first (most common case)
	directPath := filepath.Join(q.dir, id+".json")
	if item, err := q.readItemFile(directPath); err == nil && item.ID == id {
		return item, nil
	}

	// Fall back to scanning all files (handles claimed suffix)
	entries, err := os.ReadDir(q.dir)
	if err != nil {
		return nil, fmt.Errorf("read queue dir %s: %w", q.dir, err)
	}

	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") {
			continue
		}
		item, err := q.readItemFile(filepath.Join(q.dir, entry.Name()))
		if err != nil {
			continue
		}
		if item.ID == id {
			return item, nil
		}
	}

	return nil, fmt.Errorf("item %s not found in queue %s", id, q.name)
}

// Push adds a new item atomically by writing to a temp file then renaming.
func (q *Queue) Push(item QueueItem) error {
	data, err := json.MarshalIndent(item, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal item: %w", err)
	}

	// Write to temp file in the same directory for atomic rename
	tmpFile, err := os.CreateTemp(q.dir, ".tmp-*.json")
	if err != nil {
		return fmt.Errorf("create temp file: %w", err)
	}
	tmpPath := tmpFile.Name()

	if _, err := tmpFile.Write(data); err != nil {
		tmpFile.Close()
		os.Remove(tmpPath)
		return fmt.Errorf("write temp file: %w", err)
	}
	if err := tmpFile.Close(); err != nil {
		os.Remove(tmpPath)
		return fmt.Errorf("close temp file: %w", err)
	}

	finalPath := filepath.Join(q.dir, item.ID+".json")
	if err := os.Rename(tmpPath, finalPath); err != nil {
		os.Remove(tmpPath)
		return fmt.Errorf("rename to final path: %w", err)
	}

	return nil
}

// Claim marks an item as claimed by a worker. The file is renamed to include
// a `.claimed-{worker}` suffix before the .json extension, and the item's
// status and ClaimedBy fields are updated.
func (q *Queue) Claim(id string, claimedBy string) error {
	srcPath := filepath.Join(q.dir, id+".json")
	item, err := q.readItemFile(srcPath)
	if err != nil {
		return fmt.Errorf("read item %s: %w", id, err)
	}

	if item.Status != StatusPending {
		return fmt.Errorf("item %s is not pending (status: %s)", id, item.Status)
	}

	item.Status = StatusInProgress
	item.ClaimedBy = &claimedBy

	data, err := json.MarshalIndent(item, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal claimed item: %w", err)
	}

	// Write updated content to the original file first
	if err := os.WriteFile(srcPath, data, 0o644); err != nil {
		return fmt.Errorf("write claimed item: %w", err)
	}

	// Rename with claimed suffix
	dstPath := filepath.Join(q.dir, fmt.Sprintf("%s.claimed-%s.json", id, claimedBy))
	if err := os.Rename(srcPath, dstPath); err != nil {
		return fmt.Errorf("rename to claimed: %w", err)
	}

	return nil
}

// Complete marks an item as completed and moves it to the completed/ subdir.
func (q *Queue) Complete(id string) error {
	srcPath, err := q.findItemFile(id)
	if err != nil {
		return err
	}

	item, err := q.readItemFile(srcPath)
	if err != nil {
		return fmt.Errorf("read item %s: %w", id, err)
	}

	item.Status = StatusCompleted

	data, err := json.MarshalIndent(item, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal completed item: %w", err)
	}

	dstPath := filepath.Join(q.dir, "completed", id+".json")
	if err := os.WriteFile(dstPath, data, 0o644); err != nil {
		return fmt.Errorf("write completed item: %w", err)
	}

	if err := os.Remove(srcPath); err != nil {
		return fmt.Errorf("remove original item: %w", err)
	}

	return nil
}

// Fail marks an item as failed and moves it to the failed/ subdir.
// The reason is stored in the item's payload under a "failure_reason" key.
func (q *Queue) Fail(id string, reason string) error {
	srcPath, err := q.findItemFile(id)
	if err != nil {
		return err
	}

	item, err := q.readItemFile(srcPath)
	if err != nil {
		return fmt.Errorf("read item %s: %w", id, err)
	}

	item.Status = StatusFailed

	// Embed failure reason into a wrapper around the existing payload
	wrapper := map[string]json.RawMessage{
		"original_payload": item.Payload,
	}
	reasonBytes, _ := json.Marshal(reason)
	wrapper["failure_reason"] = reasonBytes
	wrappedPayload, err := json.Marshal(wrapper)
	if err != nil {
		return fmt.Errorf("marshal failure wrapper: %w", err)
	}
	item.Payload = wrappedPayload

	data, err := json.MarshalIndent(item, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal failed item: %w", err)
	}

	dstPath := filepath.Join(q.dir, "failed", id+".json")
	if err := os.WriteFile(dstPath, data, 0o644); err != nil {
		return fmt.Errorf("write failed item: %w", err)
	}

	if err := os.Remove(srcPath); err != nil {
		return fmt.Errorf("remove original item: %w", err)
	}

	return nil
}

// readItemFile reads and parses a single queue item from a JSON file.
func (q *Queue) readItemFile(path string) (*QueueItem, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var item QueueItem
	if err := json.Unmarshal(data, &item); err != nil {
		return nil, err
	}
	return &item, nil
}

// findItemFile locates the file for an item by ID, handling claimed suffixes.
func (q *Queue) findItemFile(id string) (string, error) {
	// Try direct path first
	direct := filepath.Join(q.dir, id+".json")
	if _, err := os.Stat(direct); err == nil {
		return direct, nil
	}

	// Scan for claimed files
	entries, err := os.ReadDir(q.dir)
	if err != nil {
		return "", fmt.Errorf("read queue dir %s: %w", q.dir, err)
	}

	prefix := id + ".claimed-"
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		if strings.HasPrefix(entry.Name(), prefix) && strings.HasSuffix(entry.Name(), ".json") {
			return filepath.Join(q.dir, entry.Name()), nil
		}
	}

	return "", fmt.Errorf("item %s not found in queue %s", id, q.name)
}

// priorityRank maps priority to a sortable integer (lower = higher priority).
func priorityRank(p Priority) int {
	switch p {
	case PriorityHigh:
		return 0
	case PriorityMedium:
		return 1
	case PriorityLow:
		return 2
	default:
		return 3
	}
}
