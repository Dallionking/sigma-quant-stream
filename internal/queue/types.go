package queue

import (
	"encoding/json"
	"time"
)

// Priority levels for queue items
type Priority string

const (
	PriorityHigh   Priority = "high"
	PriorityMedium Priority = "medium"
	PriorityLow    Priority = "low"
)

// Status of a queue item
type Status string

const (
	StatusPending    Status = "pending"
	StatusInProgress Status = "in_progress"
	StatusCompleted  Status = "completed"
	StatusFailed     Status = "failed"
)

// QueueName identifies the 4 queues
type QueueName string

const (
	QueueHypotheses QueueName = "hypotheses"
	QueueToConvert  QueueName = "to-convert"
	QueueToBacktest QueueName = "to-backtest"
	QueueToOptimize QueueName = "to-optimize"
)

// AllQueues returns all queue names in pipeline order
func AllQueues() []QueueName {
	return []QueueName{QueueHypotheses, QueueToConvert, QueueToBacktest, QueueToOptimize}
}

// QueueItem represents a single item in a queue
type QueueItem struct {
	ID        string          `json:"id"`
	CreatedAt time.Time       `json:"created_at"`
	CreatedBy string          `json:"created_by"`
	Priority  Priority        `json:"priority"`
	Status    Status          `json:"status"`
	ClaimedBy *string         `json:"claimed_by"`
	Payload   json.RawMessage `json:"payload"`
}

// QueueDepth summarizes the state of a single queue
type QueueDepth struct {
	Name    QueueName
	Pending int
	Claimed int
	Total   int
}

// EventType for queue changes
type EventType int

const (
	EventAdded EventType = iota
	EventClaimed
	EventCompleted
	EventFailed
	EventRemoved
)

// QueueEvent represents a change in a queue
type QueueEvent struct {
	Queue QueueName
	Type  EventType
	Item  *QueueItem
	Time  time.Time
}
