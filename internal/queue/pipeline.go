package queue

import (
	"fmt"
	"path/filepath"
)

// Pipeline provides a high-level view of the full pipeline
type Pipeline struct {
	queues map[QueueName]*Queue
}

// NewPipeline creates a Pipeline with Queue instances for all four
// pipeline stages, rooted at queuesRoot.
func NewPipeline(queuesRoot string) *Pipeline {
	queues := make(map[QueueName]*Queue)
	for _, name := range AllQueues() {
		dir := filepath.Join(queuesRoot, string(name))
		queues[name] = NewQueue(name, dir)
	}
	return &Pipeline{queues: queues}
}

// GetPipelineStatus returns depths for all queues in pipeline order.
func (p *Pipeline) GetPipelineStatus() ([]QueueDepth, error) {
	depths := make([]QueueDepth, 0, len(AllQueues()))
	for _, name := range AllQueues() {
		q, ok := p.queues[name]
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

// GetTotalItems returns total items across all queues (pending + claimed).
func (p *Pipeline) GetTotalItems() (int, error) {
	total := 0
	for _, name := range AllQueues() {
		q, ok := p.queues[name]
		if !ok {
			continue
		}
		depth, err := q.Count()
		if err != nil {
			return 0, fmt.Errorf("count queue %s: %w", name, err)
		}
		total += depth.Total
	}
	return total, nil
}

// GetQueue returns the Queue for a given name.
func (p *Pipeline) GetQueue(name QueueName) (*Queue, bool) {
	q, ok := p.queues[name]
	return q, ok
}
