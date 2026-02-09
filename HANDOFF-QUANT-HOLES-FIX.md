# Quant Team Holes Fix - Claude Code Handoff

> **Mission**: Fix the identified gaps in the Quant Team overnight research system to improve success rates from 18% to 70%+ on backtester and achieve 90%+ overall.

---

## Context

We built an autonomous Quant Research Team using the Ralph Wiggum Loop pattern - 6 Claude Code instances running in parallel via tmux, each with a specialized role (researcher, converter, backtester, optimizer, prop_firm_validator, knowledge_distiller).

**Current Issues**:
1. **Backtester 18% success rate** - Tasks require backtesting but no data/tools provided
2. **238 completions but only 58 files** - Completion detection too lenient
3. **Sub-agents not used** - 7 sub-agents defined but never invoked
4. **Skills not used** - 70+ skills available but not referenced in prompts
5. **No worker coordination** - No handoff between researcher → backtester → optimizer
6. **Token tracking shows $0** - CLI doesn't expose token counts

---

## Plan Reference

Full plan at: `.cursor/plans/quant_team_holes_fix_fa511f1f.plan.md`

Or use Taskmaster: `task-master list` to see generated tasks.

---

## Sub-Agents You Should Use

Invoke these when you need specialized expertise:

| Sub-Agent | Location | When to Use |
|-----------|----------|-------------|
| `@sigma-quant` | `.claude/agents/sigma-quant.md` | Statistical analysis, Base Hit methodology |
| `@sigma-researcher` | `.claude/agents/sigma-researcher.md` | Deep multi-source research |
| `@base-hit-optimizer` | `.claude/agents/base-hit-optimizer.md` | Loss MFE cash exit calculations |
| `@sigma-executor` | `.claude/agents/sigma-executor.md` | Pure implementation tasks |
| `@sigma-reviewer` | `.claude/agents/sigma-reviewer.md` | Code review before finalizing |

---

## Skills to Load

Read these skill files for implementation guidance:

| Skill | Path | Use For |
|-------|------|---------|
| `pine-converter` | `.claude/skills/pine-converter/skill.md` | PineScript → Python conversion |
| `strategy-research` | `.claude/skills/strategy-research/skill.md` | Backtest execution, optimizer usage |
| `tradebench-engine` | `.claude/skills/tradebench-engine/skill.md` | TradeBench simulation runs |
| `tradebench-metrics` | `.claude/skills/tradebench-metrics/skill.md` | Sharpe, Sortino, drawdown calcs |
| `quant-research` | `.claude/skills/quant-research/skill.md` | Research pipeline patterns |
| `trading-strategies` | `.claude/skills/trading-strategies/skill.md` | BaseStrategy class structure |

---

## MCP Tools Available

```
mcp_exa_web_search_exa           # Web research
mcp_exa_get_code_context_exa     # Find code examples
mcp_Ref_ref_search_documentation # Search official docs
mcp_Ref_ref_read_url             # Read documentation pages
```

---

## Files to Modify (Priority Order)

### CRITICAL - Fix Backtester

**File**: `stream-quant/prompts/backtester.md`

**Changes Needed**:
1. Add TradeBench integration instructions
2. Reference `strategy-research` skill for `backtest_runner.py` usage
3. Add sample data paths for offline mode
4. Include Python code snippets for proper backtest execution

**Key Content to Add**:
```markdown
## How to Actually Backtest

1. **Use TradeBench** (preferred):
   ```bash
   cd apps/tradebench/backend
   python -m tradebench.cli backtest --strategy strategy.py --data stream-quant/data/
   ```

2. **Use strategy_research scripts**:
   ```bash
   python apps/backend/scripts/strategy_research/backtest_runner.py \
     --strategy output/strategies/momentum.py \
     --firm apex \
     --walk-forward
   ```

3. **Sample Data Available**:
   - `stream-quant/data/ES_5min_sample.csv`
   - `stream-quant/data/NQ_5min_sample.csv`

## Sub-Agents to Invoke

- `@sigma-quant` for statistical validation
- `@base-hit-optimizer` for cash exit calculation after backtest
```

---

### CRITICAL - Tighten Completion Detection

**File**: `scripts/quant-team/quant-ralph.sh`

**Find this section** (around line 545):
```bash
if grep -qE "(QUANT_TASK_COMPLETE|Task.*complete|Successfully.*created|Output.*saved)" "$output_file"
```

**Add file verification after phrase detection**:
```bash
# After phrase detection success, verify file was actually created
if [[ "$completion_method" == "phrase_detection" ]]; then
    local output_dir="stream-quant/output"
    local recent_files=$(find "$output_dir" -type f -mmin -5 2>/dev/null | wc -l)
    local task_start_file="$CHECKPOINT_DIR/.task_start_$task_id"
    
    if [[ -f "$task_start_file" ]]; then
        local newer_files=$(find "$output_dir" -type f -newer "$task_start_file" 2>/dev/null | wc -l)
        if [[ "$newer_files" -eq 0 ]]; then
            log_warn "⚠️ Phrase detected but no new files created - not marking complete"
            success=false
            completion_detected=false
            continue  # Retry the task
        fi
    fi
fi
```

---

### HIGH - Add Sub-Agent References to All Prompts

Update each file in `stream-quant/prompts/`:

1. `researcher.md` - Add `@sigma-researcher` for deep research
2. `converter.md` - Add `pine-converter` skill reference
3. `optimizer.md` - Add `@base-hit-optimizer` agent
4. `prop_firm_validator.md` - Add `@sigma-risk` agent
5. `knowledge_distiller.md` - Add research-pipeline skill

**Template to add to each prompt**:
```markdown
## Sub-Agents Available

When a task requires specialized expertise beyond your role, invoke:

| Agent | Command | Use When |
|-------|---------|----------|
| @sigma-quant | Deep statistical analysis needed |
| @sigma-researcher | Multi-source research required |
| @base-hit-optimizer | Cash exit optimization |

## Skills to Reference

Load these skill files for detailed guidance:
- `.claude/skills/[relevant-skill]/skill.md`
```

---

### HIGH - Create Sample Data

**Create**: `stream-quant/data/ES_5min_sample.csv`

Generate 1000 rows of realistic ES futures data:
```csv
timestamp,open,high,low,close,volume
2024-01-02 09:30:00,4750.00,4752.50,4749.25,4751.75,12500
2024-01-02 09:35:00,4751.75,4754.00,4751.00,4753.25,8750
...
```

You can use Python to generate this:
```python
import pandas as pd
import numpy as np

# Generate realistic futures data
dates = pd.date_range('2024-01-02 09:30', periods=1000, freq='5min')
price = 4750 + np.cumsum(np.random.randn(1000) * 2)
# ... (generate OHLCV)
```

---

### HIGH - Export API Keys to Tmux

**File**: `scripts/quant-team/spawn-quant-team.sh` or `tmux-quant-launcher.sh`

**Add after tmux session creation**:
```bash
# Export API keys to tmux environment
if [[ -n "$DATABENTO_API_KEY" ]]; then
    tmux set-environment -t quant-team DATABENTO_API_KEY "$DATABENTO_API_KEY"
fi
if [[ -n "$OPENAI_API_KEY" ]]; then
    tmux set-environment -t quant-team OPENAI_API_KEY "$OPENAI_API_KEY"
fi
```

---

### MEDIUM - Create Worker Queue System

**Create directory**: `stream-quant/queues/`

**Create files**:
- `ready-for-backtest.json` - Researcher outputs go here
- `ready-for-optimization.json` - Backtester outputs go here
- `ready-for-validation.json` - Optimizer outputs go here

**Queue file format**:
```json
{
  "queue_name": "ready-for-backtest",
  "items": [
    {
      "id": "hypothesis-001",
      "source_worker": "researcher",
      "source_pane": 1,
      "created_at": "2026-01-18T12:00:00Z",
      "artifact_path": "output/research/hypothesis-001.json",
      "priority": 1
    }
  ]
}
```

**Update worker prompts to**:
1. CHECK their input queue at task start
2. PUSH to output queue on completion

---

### MEDIUM - Add Cost Estimation

**File**: `scripts/quant-team/quant-ralph.sh`

**Add near the top**:
```bash
# Cost estimation (Claude Code CLI doesn't expose actual tokens)
ESTIMATED_COST_PER_TASK=0.042  # ~4K input + 2K output tokens average
TOTAL_COST=0.0
```

**Add after successful task completion**:
```bash
TOTAL_COST=$(echo "$TOTAL_COST + $ESTIMATED_COST_PER_TASK" | bc)
echo "ESTIMATED_COST: \$$TOTAL_COST" >> "$STATUS_FILE"
```

---

### MEDIUM - Add Failure Categorization

**File**: `scripts/quant-team/quant-ralph.sh`

**Add function**:
```bash
categorize_failure() {
    local output_file="$1"
    
    if grep -qi "rate.?limit\|too.?many.?requests\|quota" "$output_file"; then
        echo "rate_limit"
    elif grep -qi "no data\|data not found\|file not found" "$output_file"; then
        echo "data_missing"
    elif grep -qi "timeout\|timed out\|took too long" "$output_file"; then
        echo "timeout"
    elif grep -qi "permission\|unauthorized\|forbidden" "$output_file"; then
        echo "permission"
    elif grep -qi "syntax error\|invalid\|parse error" "$output_file"; then
        echo "code_error"
    else
        echo "unknown"
    fi
}
```

**Use in failure logging**:
```bash
local failure_type=$(categorize_failure "$output_file")
log_error "Task failed: $task_id - Type: $failure_type"
```

---

## Execution Order

1. **Read the skills first** - Load `strategy-research` and `tradebench-engine` skills
2. **Fix backtester.md** - This is the root cause of 18% success
3. **Tighten completion detection** - Prevents false positives
4. **Add sub-agent references** - Enables skill delegation
5. **Create sample data** - Enables offline backtesting
6. **Create queue system** - Enables worker coordination
7. **Add cost estimation** - Enables budget tracking
8. **Test with single pane** before full deploy

---

## Testing the Fixes

After making changes:

```bash
# Test single backtester pane
cd /Users/dallionking/SSS\ Projects/SigmaQuantStream
./scripts/quant-team/quant-ralph.sh \
  --pane-id=1 \
  --worker-type=backtester \
  --iterations=3 \
  --worktree=.
```

Watch for:
- [ ] TradeBench or backtest_runner.py being invoked
- [ ] Actual files created in `stream-quant/output/backtests/`
- [ ] Sub-agent invocations visible in output
- [ ] Completion only on file creation

---

## Success Criteria

| Metric | Before | Target |
|--------|--------|--------|
| Backtester success | 18% | 70%+ |
| Overall success | 79% | 90%+ |
| Files per completion | 24% | 80%+ |
| Cost tracking | $0 | Accurate |
| Worker coordination | None | Full pipeline |

---

## Questions?

If unclear on any task:
1. Read the relevant skill file in `.claude/skills/`
2. Check the sub-agent definition in `.claude/agents/`
3. Reference the full plan at `.cursor/plans/quant_team_holes_fix_fa511f1f.plan.md`

**Begin with the backtester prompt fix - it's the highest impact change.**
