---
name: quant-queue-coordination
description: "Inter-worker queue coordination and file-based IPC"
version: "1.0.0"
triggers:
  - "when reading from queues"
  - "when writing to queues"
  - "when coordinating between workers"
---

# Quant Queue Coordination

## Purpose

Manages file-based inter-process communication (IPC) between quant workers. Ensures atomic operations and prevents race conditions.

## When to Use

- When pushing items to queues
- When claiming items from queues
- When coordinating between workers

## Queue Structure

```
stream-quant/queues/
├── hypotheses/          # Researcher → Backtester
├── to-convert/          # Researcher → Converter
├── to-backtest/         # Converter → Backtester
├── to-optimize/         # Backtester → Optimizer
├── completed/           # Archive
└── failed/              # Failed items
```

## Queue Item Schema

```json
{
  "id": "hyp-2026-01-26-001",
  "created_at": "2026-01-26T08:30:00Z",
  "created_by": "researcher-pane-0",
  "priority": "high",
  "status": "pending",
  "claimed_by": null,
  "claimed_at": null,
  "payload": {
    "title": "RSI Divergence",
    "hypothesis": "...",
    "markets": ["ES", "NQ"]
  }
}
```

## Atomic Operations

### Push (Write to Queue)

```python
import json
import os
import tempfile
import shutil
from datetime import datetime

def push_to_queue(queue_dir: str, item: dict) -> str:
    """
    Atomically push item to queue.

    Uses write-to-temp-then-move pattern for atomicity.
    """
    # Generate ID
    item_id = f"{item['type']}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
    item['id'] = item_id
    item['created_at'] = datetime.now().isoformat()
    item['status'] = 'pending'

    # Write to temp file first
    fd, temp_path = tempfile.mkstemp(suffix='.json', dir=queue_dir)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(item, f, indent=2)

        # Atomic move
        final_path = os.path.join(queue_dir, f"{item_id}.json")
        shutil.move(temp_path, final_path)

        return item_id
    except:
        os.unlink(temp_path)
        raise
```

### Claim (Take from Queue)

```python
def claim_item(queue_dir: str, worker_id: str) -> dict | None:
    """
    Atomically claim next available item.

    Uses rename for atomic claim.
    """
    items = sorted([
        f for f in os.listdir(queue_dir)
        if f.endswith('.json') and '.claimed' not in f
    ])

    if not items:
        return None

    # Try to claim (may race with other workers)
    for item_file in items:
        original_path = os.path.join(queue_dir, item_file)
        claimed_path = os.path.join(queue_dir, item_file.replace('.json', f'.claimed-{worker_id}.json'))

        try:
            # Atomic rename - fails if already claimed
            os.rename(original_path, claimed_path)

            with open(claimed_path) as f:
                item = json.load(f)

            item['status'] = 'in_progress'
            item['claimed_by'] = worker_id
            item['claimed_at'] = datetime.now().isoformat()

            return item
        except FileNotFoundError:
            # Someone else claimed it, try next
            continue

    return None
```

### Complete (Archive)

```python
def complete_item(queue_dir: str, item_id: str, success: bool = True):
    """Move completed item to archive."""

    # Find claimed file
    claimed_files = [f for f in os.listdir(queue_dir) if item_id in f and '.claimed' in f]

    if not claimed_files:
        raise ValueError(f"No claimed item found: {item_id}")

    source = os.path.join(queue_dir, claimed_files[0])

    # Determine destination
    dest_dir = 'completed' if success else 'failed'
    dest = os.path.join(queue_dir, '..', dest_dir, claimed_files[0].replace('.claimed', ''))

    shutil.move(source, dest)
```

## Priority Handling

```python
def get_next_item(queue_dir: str) -> str | None:
    """Get next item respecting priority."""

    items = []
    for f in os.listdir(queue_dir):
        if not f.endswith('.json') or '.claimed' in f:
            continue

        with open(os.path.join(queue_dir, f)) as file:
            item = json.load(file)
            items.append((f, item.get('priority', 'low')))

    # Sort by priority: high > medium > low
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    items.sort(key=lambda x: priority_order.get(x[1], 99))

    return items[0][0] if items else None
```

## Queue Flow

```
Researcher
    │
    ├──→ queues/hypotheses/ ──→ Backtester
    │
    └──→ queues/to-convert/ ──→ Converter ──→ queues/to-backtest/ ──→ Backtester
                                                                          │
                                                                          ▼
                                                              queues/to-optimize/
                                                                          │
                                                                          ▼
                                                                     Optimizer
                                                                          │
                                                                          ▼
                                                        output/strategies/{good|prop_firm_ready|rejected}
```

## Related Skills

- `quant-session-management` - Session lifecycle
- `quant-artifact-routing` - Output routing
