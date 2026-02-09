# Quant Team Mission Architecture - Claude Code Handoff

> **Mission**: Transform the Quant Team from task-based execution to mission-based autonomous discovery with a layered context engine.

---

## Claude Code Execution Prompt

Copy the entire block below and paste into Claude Code:

```
Execute the Quant Team Mission Architecture plan. This is a major refactor from task-based to mission-based autonomous research.

## Context Files to Read First
- Plan: `.cursor/plans/quant_team_mission_architecture_89af5175.plan.md`
- Holes Analysis: `.cursor/plans/quant_team_holes_fix_fa511f1f.plan.md`
- Current Ralph Loop: `scripts/quant-team/quant-ralph.sh`
- Current Prompts: `stream-quant/prompts/*.md`
- Existing Sub-Agents: `.claude/agents/sigma-*.md`, `.claude/agents/base-hit-optimizer.md`
- Existing Skills: `.claude/skills/*/skill.md`

## Your Mission
Transform the overnight Quant Research Team from a finite task executor (50 pre-generated tasks per worker) into an infinite mission-based discovery system where 4 main agents:
1. Run fresh Claude sessions each iteration (true Ralph Loop)
2. Communicate via shared queue directories
3. Learn from each other via pattern files
4. Use sub-agents to offload context-heavy work
5. Call @sigma-distiller at session end for knowledge synthesis

## Sub-Agents You Will Create/Use
| Sub-Agent | Purpose | Invoke When |
|-----------|---------|-------------|
| @sigma-distiller | Knowledge synthesis (NEW) | End of every session |
| @sigma-researcher | Deep multi-source research | Complex research needed |
| @sigma-quant | Statistical validation | Hypothesis validation |
| @base-hit-optimizer | Loss MFE cash exit | Strategy optimization |
| @sigma-risk | Prop firm validation | Before marking strategy ready |
| @sigma-executor | Clean code implementation | Converting indicators |

## Skills You Will Create/Reference
| Skill | Location | Used By |
|-------|----------|---------|
| knowledge-synthesis (NEW) | `.claude/skills/knowledge-synthesis/skill.md` | @sigma-distiller |
| pattern-analysis (NEW) | `.claude/skills/pattern-analysis/skill.md` | @sigma-distiller |
| prop-firm-rules (NEW) | `.claude/skills/prop-firm-rules/skill.md` | @sigma-risk, Optimizer |
| pine-converter | `.claude/skills/pine-converter/skill.md` | Converter |
| strategy-research | `.claude/skills/strategy-research/skill.md` | Researcher, Backtester |
| tradebench-engine | `.claude/skills/tradebench-engine/skill.md` | Backtester |

## Implementation Phases (Execute in Order)

### Phase 1: Foundation (Create These First)
1. Create `@sigma-distiller` sub-agent:
   - File: `.claude/agents/sigma-distiller.md`
   - Purpose: Knowledge synthesis at session end
   - Skills it uses: knowledge-synthesis, pattern-analysis

2. Create queue directories:
   - `stream-quant/queues/to-convert/.gitkeep`
   - `stream-quant/queues/to-backtest/.gitkeep`
   - `stream-quant/queues/hypotheses/.gitkeep`
   - `stream-quant/queues/to-optimize/.gitkeep`

3. Create pattern files:
   - `stream-quant/patterns/what-works.md` - Start with header template
   - `stream-quant/patterns/what-fails.md` - Start with header template
   - `stream-quant/patterns/indicator-combos.md`
   - `stream-quant/patterns/prop-firm-gotchas.md`

4. Create sample data for offline backtesting:
   - `stream-quant/data/ES_5min_sample.csv` - 1000 rows OHLCV
   - `stream-quant/data/NQ_5min_sample.csv` - 1000 rows OHLCV
   - `stream-quant/data/README.md` - Format documentation

### Phase 2: Create New Skills
1. `knowledge-synthesis` skill:
   - File: `.claude/skills/knowledge-synthesis/skill.md`
   - Content: How to extract insights, avoid duplicates, timestamp entries

2. `pattern-analysis` skill:
   - File: `.claude/skills/pattern-analysis/skill.md`
   - Content: Templates for what-works.md and what-fails.md entries

3. `prop-firm-rules` skill:
   - File: `.claude/skills/prop-firm-rules/skill.md`
   - Content: All 14 prop firm rules (Apex, Topstep, FTMO, etc.)
   - Include: daily loss limits, trailing DD, consistency rules, payout rules

### Phase 3: Rewrite Main Agent Mission Prompts
Each prompt must include:
- Standing mission (not specific tasks)
- Sub-agents they can invoke
- Skills to reference
- Queues to check/populate
- Session-end protocol (call @sigma-distiller)
- Completion marker: SESSION_COMPLETE

1. Researcher (`stream-quant/prompts/researcher.md`):
   - Mission: Hunt for trading edges
   - Sources: TradingView, academic papers, quant blogs
   - Check: patterns/what-works.md, patterns/what-fails.md
   - Output to: queues/hypotheses/, queues/to-convert/
   - Sub-agents: @sigma-researcher, @sigma-quant
   - End with: @sigma-distiller

2. Converter (`stream-quant/prompts/converter.md`):
   - Mission: Convert PineScript indicators to Python
   - Direct source: https://www.tradingview.com/scripts/ (use Firecrawl/Exa)
   - Check: queues/to-convert/
   - Output to: output/indicators/converted/, queues/to-backtest/
   - Sub-agents: @sigma-executor
   - Skill: pine-converter
   - End with: @sigma-distiller

3. Backtester (`stream-quant/prompts/backtester.md`):
   - Mission: Validate strategy hypotheses
   - Check: queues/hypotheses/, queues/to-backtest/
   - Data: stream-quant/data/*.csv OR Databento if available
   - Use TradeBench: `apps/tradebench/backend/`
   - Reject overfit: Sharpe >3, win rate >80%
   - Output to: queues/to-optimize/ OR output/strategies/rejected/
   - Sub-agents: @sigma-quant, @base-hit-optimizer
   - Skill: tradebench-engine, strategy-research
   - End with: @sigma-distiller

4. Optimizer (`stream-quant/prompts/optimizer.md`):
   - Mission: Optimize parameters + prop firm validation
   - Check: queues/to-optimize/
   - Parameter optimization: coarse grid, perturbation test
   - Cash exit: @base-hit-optimizer for Loss MFE
   - Validation: @sigma-risk for all 14 prop firms
   - Output to: output/strategies/prop_firm_ready/ OR output/strategies/GOOD/
   - Sub-agents: @base-hit-optimizer, @sigma-risk
   - Skill: prop-firm-rules
   - End with: @sigma-distiller

### Phase 4: Update Ralph Loop Script
File: `scripts/quant-team/quant-ralph.sh`

Key changes:
1. Fresh session bash loop (not single invocation):
```bash
while true; do
    MISSION_PROMPT="$(cat $PROMPTS_DIR/$WORKER_TYPE.md)
    
## Previous Session
$(tail -30 stream-quant/session-summaries/pane-$PANE_ID.md)

## Shared Knowledge  
$(cat stream-quant/patterns/what-works.md | tail -20)

Begin your mission. Output SESSION_COMPLETE when done."

    timeout 2400 claude --dangerously-skip-permissions -p "$MISSION_PROMPT" 2>&1 | tee "$OUTPUT_FILE"
    
    parse_session_result "$OUTPUT_FILE"
    ((ITERATION++))
    sleep 5
done
```

2. Tighten completion detection (require file creation):
```bash
if grep -q "SESSION_COMPLETE" "$OUTPUT_FILE"; then
    local new_files=$(find "$OUTPUT_DIR" -type f -newer "$start_time_file" 2>/dev/null | wc -l)
    if [[ "$new_files" -eq 0 ]]; then
        log_warn "Session complete but no files created"
        echo "NO_OUTPUT_FILES" >> "$SESSION_SUMMARY"
    fi
fi
```

3. Add failure categorization:
```bash
categorize_failure() {
    local output_file="$1"
    if grep -qi "rate.?limit" "$output_file"; then echo "rate_limit"
    elif grep -qi "no data\|missing" "$output_file"; then echo "data_missing"
    elif grep -qi "timeout" "$output_file"; then echo "timeout"
    else echo "unknown"; fi
}
```

4. Add output validation:
```bash
validate_output() {
    local file="$1"
    if [[ "$file" == *.py ]]; then python3 -m py_compile "$file" 2>/dev/null || return 1; fi
    if [[ "$file" == *.json ]]; then jq empty "$file" 2>/dev/null || return 1; fi
    return 0
}
```

5. Add cost estimation:
```bash
ESTIMATED_COST_PER_ITERATION=0.042
TOTAL_COST=$(echo "$TOTAL_COST + $ESTIMATED_COST_PER_ITERATION" | bc)
```

### Phase 5: Update Tmux Launcher
File: `scripts/quant-team/tmux-quant-launcher.sh`

Changes:
1. Reduce from 6 panes to 4:
   - Pane 1: Researcher
   - Pane 2: Converter
   - Pane 3: Backtester
   - Pane 4: Optimizer

2. Export API keys:
```bash
tmux set-environment -t quant-team DATABENTO_API_KEY "$DATABENTO_API_KEY"
tmux set-environment -t quant-team ANTHROPIC_API_KEY "$ANTHROPIC_API_KEY"
```

3. Add mode flag to spawn script:
```bash
# spawn-quant-team.sh
MODE="${1:---mode=research}"  # Default to research mode
if [[ "$MODE" == "--mode=production" ]]; then
    TIMEOUT=3600; DATA_SOURCE="databento"
else
    TIMEOUT=1800; DATA_SOURCE="sample"
fi
```

### Phase 6: Update Existing Sub-Agents
Add skill references to each:
- `.claude/agents/sigma-researcher.md` - Add strategy-research skill
- `.claude/agents/sigma-quant.md` - Add tradebench-engine skill
- `.claude/agents/base-hit-optimizer.md` - Add pattern-analysis skill
- `.claude/agents/sigma-risk.md` - Add prop-firm-rules skill

### Phase 7: Cleanup
Delete/archive deprecated files:
- `stream-quant/prompts/prop_firm_validator.md` (built into Optimizer)
- `stream-quant/prompts/knowledge_distiller.md` (now @sigma-distiller)
- `scripts/quant-team/generate-backlog.py` (no longer needed)
- `stream-quant/backlogs/*.json` (archive to stream-quant/backlogs/_archived/)

## Validation Checklist
Before marking complete, verify:
- [ ] @sigma-distiller created and invocable
- [ ] All 3 new skills created
- [ ] Queue directories exist with .gitkeep
- [ ] Pattern files have header templates
- [ ] Sample data files have 1000+ rows each
- [ ] All 4 mission prompts reference sub-agents and skills
- [ ] quant-ralph.sh has fresh session while loop
- [ ] Completion detection requires file creation
- [ ] Failure categorization function exists
- [ ] Output validation function exists
- [ ] Cost estimation logs to status file
- [ ] Tmux launcher reduced to 4 panes
- [ ] API keys exported to tmux environment
- [ ] Mode flag (research/production) works

## Expected Outcomes
| Metric | Before | Target |
|--------|--------|--------|
| Architecture | Task-based | Mission-based |
| Backtester Success | 18% | 70%+ |
| Overnight Runs | Stops at 50 tasks | Runs until stopped |
| Sub-Agents Used | 0 | 6 |
| Files per Completion | 24% | 80%+ |

Start by using /sigma-planner to create a detailed implementation plan, then execute each phase in order.
```

---

## Quick Reference

### Directory Structure After Implementation
```
stream-quant/
├── prompts/
│   ├── researcher.md      # Mission-based (rewritten)
│   ├── converter.md       # Mission-based (rewritten)
│   ├── backtester.md      # Mission-based (rewritten)
│   └── optimizer.md       # Mission-based (rewritten)
├── queues/
│   ├── to-convert/        # Researcher -> Converter
│   ├── to-backtest/       # Converter -> Backtester
│   ├── hypotheses/        # Researcher -> Backtester
│   └── to-optimize/       # Backtester -> Optimizer
├── patterns/
│   ├── what-works.md      # Validated approaches
│   ├── what-fails.md      # Documented failures
│   ├── indicator-combos.md
│   └── prop-firm-gotchas.md
├── session-summaries/
│   ├── pane-1.md          # Researcher history
│   ├── pane-2.md          # Converter history
│   ├── pane-3.md          # Backtester history
│   └── pane-4.md          # Optimizer history
├── data/
│   ├── ES_5min_sample.csv
│   ├── NQ_5min_sample.csv
│   └── README.md
└── output/
    ├── indicators/converted/
    ├── strategies/prop_firm_ready/
    ├── strategies/GOOD/
    └── strategies/rejected/
```

### Sub-Agent Invocation Examples
```bash
# In main agent prompt:
"When you need deep research, invoke @sigma-researcher"
"Before marking strategy ready, invoke @sigma-risk for prop firm validation"
"At session end, invoke @sigma-distiller with your session summary"
```
