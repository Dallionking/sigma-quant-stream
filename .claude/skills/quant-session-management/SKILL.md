---
name: quant-session-management
description: "Session lifecycle management for quant workers"
version: "1.0.0"
triggers:
  - "when starting a quant session"
  - "when ending a session"
  - "when tracking session progress"
---

# Quant Session Management

## Purpose

Manages the lifecycle of quant worker sessions: startup, execution, distillation, and completion. Ensures proper session markers and pattern updates.

## When to Use

- At the start of every quant session
- When tracking session progress
- At session end for mandatory distillation

## Session Lifecycle

```
SESSION_START → EXECUTION_LOOP → DISTILLATION → SESSION_COMPLETE
     │              │                 │               │
   Read        Process items      Update         Output
  patterns      from queues      patterns       summary
```

## Session Protocol

### 1. SESSION_START

```bash
# Output at session start
SESSION_START: {worker-type}-{timestamp}
PATTERN_FILES_READ: what-works.md, what-fails.md
QUEUE_DEPTH: hypotheses=5, to-convert=3
```

### 2. Execution Loop

```bash
# For each task
TASK_START: {task-id}
SUBAGENT_SPAWN: @quant-{name}
SUBAGENT_COMPLETE: @quant-{name}
FILES_CREATED: 3
TASK_COMPLETE: {task-id}
```

### 3. DISTILLATION (Mandatory)

```bash
# At session end, ALWAYS invoke distiller
@sigma-distiller: Analyze this session and update pattern files

# Expected response
DISTILLATION_COMPLETE
PATTERNS_UPDATED: what-works.md (+2 entries)
```

### 4. SESSION_COMPLETE

```bash
SESSION_COMPLETE: {worker-type}-{timestamp}
DURATION: 45m
TASKS_COMPLETED: 8
STRATEGIES_PRODUCED: 2
HYPOTHESES_QUEUED: 5
```

## Implementation

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class SessionState:
    """Track session state."""
    worker_type: str
    start_time: datetime
    tasks_completed: int = 0
    files_created: int = 0
    strategies_produced: int = 0
    hypotheses_queued: int = 0
    patterns_read: list[str] = field(default_factory=list)
    distillation_complete: bool = False

class SessionManager:
    """Manage quant session lifecycle."""

    def __init__(self, worker_type: str):
        self.state = SessionState(
            worker_type=worker_type,
            start_time=datetime.now()
        )

    def start(self) -> str:
        """Output session start marker."""
        timestamp = self.state.start_time.isoformat()
        return f"""
SESSION_START: {self.state.worker_type}-{timestamp}
PATTERN_FILES_READ: {', '.join(self.state.patterns_read)}
"""

    def task_complete(self, task_id: str, files: int = 0):
        """Record task completion."""
        self.state.tasks_completed += 1
        self.state.files_created += files
        return f"TASK_COMPLETE: {task_id}"

    def request_distillation(self) -> str:
        """Request session distillation."""
        return """
@sigma-distiller: Analyze this session and update pattern files.
Output files: {files_created}
Strategies: {strategies_produced}
Update patterns and session summaries.
""".format(**vars(self.state))

    def complete(self) -> str:
        """Output session complete marker."""
        if not self.state.distillation_complete:
            raise ValueError("Cannot complete session without distillation!")

        duration = datetime.now() - self.state.start_time

        return f"""
SESSION_COMPLETE: {self.state.worker_type}-{self.state.start_time.isoformat()}
DURATION: {duration}
TASKS_COMPLETED: {self.state.tasks_completed}
FILES_CREATED: {self.state.files_created}
STRATEGIES_PRODUCED: {self.state.strategies_produced}
HYPOTHESES_QUEUED: {self.state.hypotheses_queued}
"""
```

## Session Summary Files

Each worker writes session summary:

```
stream-quant/session-summaries/
├── pane-0.md  # Researcher
├── pane-1.md  # Converter
├── pane-2.md  # Backtester
└── pane-3.md  # Optimizer
```

## Checkpoint Protocol

For crash recovery:

```python
def save_checkpoint(state: SessionState, pane: int):
    """Save checkpoint for crash recovery."""
    checkpoint = {
        'state': vars(state),
        'timestamp': datetime.now().isoformat(),
        'last_task': state.tasks_completed
    }

    path = f"stream-quant/checkpoints/pane-{pane}.json"
    with open(path, 'w') as f:
        json.dump(checkpoint, f)
```

## Mandatory Rules

1. **Always read patterns first** - Load what-works.md, what-fails.md
2. **Always run distillation** - No session ends without it
3. **Always output completion marker** - SESSION_COMPLETE required
4. **Save checkpoints** - For crash recovery

## Related Skills

- `quant-queue-coordination` - Queue management
- `quant-artifact-routing` - Output routing
