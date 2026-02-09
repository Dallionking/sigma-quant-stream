---
name: quant-artifact-routing
description: "Routing and organizing output artifacts by status and quality"
version: "1.0.0"
triggers:
  - "when routing strategy artifacts"
  - "when organizing output files"
  - "when determining strategy destination"
---

# Quant Artifact Routing

## Purpose

Routes strategy artifacts to the correct output directory based on validation results. Ensures consistent organization of all outputs.

## When to Use

- After strategy validation completes
- After backtest results are ready
- After prop firm compliance testing

## Output Structure

```
stream-quant/output/
├── strategies/
│   ├── good/                    # Passes validation, not yet prop firm tested
│   ├── under_review/            # Marginal results, needs investigation
│   ├── rejected/                # Failed validation
│   └── prop_firm_ready/         # Passes >= 3 prop firms
├── indicators/
│   ├── converted/               # Pine → Python conversions
│   └── created/                 # Original indicators
├── backtests/
│   └── YYYY-MM-DD/             # Daily backtest results
├── hypotheses/
│   └── archive/                 # Tested hypotheses
└── research-logs/
    └── daily/                   # Daily research notes
```

## Routing Rules

### Strategy Routing

| Condition | Destination | Criteria |
|-----------|-------------|----------|
| Critical red flags | `rejected/` | Sharpe>3, WR>80%, etc. |
| OOS decay > 50% | `rejected/` | Doesn't generalize |
| OOS decay 30-50% | `under_review/` | Marginal |
| Passes validation | `good/` | OOS Sharpe>1, no flags |
| >= 3 prop firms | `prop_firm_ready/` | Production ready |

### Implementation

```python
from dataclasses import dataclass
from enum import Enum
import shutil
import os

class StrategyStatus(Enum):
    REJECTED = "rejected"
    UNDER_REVIEW = "under_review"
    GOOD = "good"
    PROP_FIRM_READY = "prop_firm_ready"

@dataclass
class RoutingDecision:
    """Routing decision for a strategy."""
    status: StrategyStatus
    destination: str
    reason: str

def determine_routing(
    metrics: dict,
    red_flags: list,
    prop_firm_results: dict = None
) -> RoutingDecision:
    """
    Determine where to route a strategy.
    """

    # Check for critical red flags
    critical_flags = [f for f in red_flags if f.severity == 'critical' and f.detected]
    if critical_flags:
        return RoutingDecision(
            status=StrategyStatus.REJECTED,
            destination="output/strategies/rejected/",
            reason=f"Critical flags: {[f.name for f in critical_flags]}"
        )

    # Check OOS decay
    decay = metrics.get('oos_decay', 0)
    if decay > 0.50:
        return RoutingDecision(
            status=StrategyStatus.REJECTED,
            destination="output/strategies/rejected/",
            reason=f"OOS decay {decay:.0%} > 50%"
        )

    if decay > 0.30:
        return RoutingDecision(
            status=StrategyStatus.UNDER_REVIEW,
            destination="output/strategies/under_review/",
            reason=f"OOS decay {decay:.0%} marginal (30-50%)"
        )

    # Check prop firm compliance
    if prop_firm_results:
        firms_passed = prop_firm_results.get('firms_passed', 0)
        if firms_passed >= 3:
            return RoutingDecision(
                status=StrategyStatus.PROP_FIRM_READY,
                destination="output/strategies/prop_firm_ready/",
                reason=f"Passes {firms_passed} prop firms"
            )

    # Default: good
    return RoutingDecision(
        status=StrategyStatus.GOOD,
        destination="output/strategies/good/",
        reason="Passes validation, pending prop firm test"
    )

def route_strategy(
    strategy_name: str,
    artifacts: dict,
    decision: RoutingDecision,
    base_path: str = "stream-quant"
):
    """
    Route strategy artifacts to destination.
    """
    dest_dir = os.path.join(base_path, decision.destination, strategy_name)
    os.makedirs(dest_dir, exist_ok=True)

    # Standard artifact structure
    files_to_write = {
        'strategy.py': artifacts.get('strategy_code'),
        'backtest.json': artifacts.get('backtest_results'),
        'optimization.json': artifacts.get('optimization_results'),
        'base_hit.json': artifacts.get('base_hit_config'),
        'prop_firms.json': artifacts.get('prop_firm_results'),
        'README.md': generate_readme(strategy_name, artifacts, decision)
    }

    for filename, content in files_to_write.items():
        if content:
            path = os.path.join(dest_dir, filename)
            with open(path, 'w') as f:
                if isinstance(content, dict):
                    import json
                    json.dump(content, f, indent=2)
                else:
                    f.write(content)

    return dest_dir

def generate_readme(
    strategy_name: str,
    artifacts: dict,
    decision: RoutingDecision
) -> str:
    """Generate README for strategy."""

    metrics = artifacts.get('backtest_results', {})

    return f"""# {strategy_name}

## Status: {decision.status.value.upper()}

**Reason**: {decision.reason}

## Performance Metrics

| Metric | In-Sample | Out-of-Sample |
|--------|-----------|---------------|
| Sharpe | {metrics.get('is_sharpe', 'N/A')} | {metrics.get('oos_sharpe', 'N/A')} |
| Max DD | {metrics.get('is_max_dd', 'N/A')} | {metrics.get('oos_max_dd', 'N/A')} |
| Win Rate | {metrics.get('is_win_rate', 'N/A')} | {metrics.get('oos_win_rate', 'N/A')} |
| Trades | {metrics.get('is_trades', 'N/A')} | {metrics.get('oos_trades', 'N/A')} |

## Files

- `strategy.py` - Strategy implementation
- `backtest.json` - Full backtest results
- `optimization.json` - Parameter optimization results
- `base_hit.json` - Cash exit configuration
- `prop_firms.json` - Prop firm compliance results
"""
```

## Artifact Checklist

Every `prop_firm_ready/` strategy must have:

- [ ] `strategy.py` - Working strategy code
- [ ] `backtest.json` - WFO backtest results
- [ ] `optimization.json` - Coarse grid optimization
- [ ] `base_hit.json` - Loss MFE cash exit config
- [ ] `prop_firms.json` - All 14 firm results
- [ ] `README.md` - Documentation

## Related Skills

- `quant-session-management` - Session lifecycle
- `quant-queue-coordination` - Queue management
