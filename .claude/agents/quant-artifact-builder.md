---
name: quant-artifact-builder
description: "Build complete strategy package with all artifacts"
version: "1.0.0"
parent_worker: optimizer
max_duration: 2m
parallelizable: false
---

# Quant Artifact Builder Agent

## Purpose
Assembles the complete strategy package containing all artifacts: source code, configurations, backtest results, optimization reports, and documentation. Creates a self-contained, deployable strategy directory that can be immediately used in production or shared with the team.

## Skills Used
- `/quant-parameter-optimization` - For optimization report formatting
- `/documentation` - For generating strategy documentation
- `/trading-strategies` - For strategy code packaging

## MCP Tools
- `sequential_thinking` - Plan artifact assembly

## Input
```python
{
    "strategy_class": str,
    "strategy_name": str,
    "source_files": [str],           # Paths to strategy code files
    "optimization_outputs": {
        "grid_results": str,         # Path to grid_results.json
        "perturbation_results": str, # Path to perturbation_results.json
        "mfe_analysis": str,         # Path to mfe_analysis.json
        "russian_doll_config": str,  # Path to russian_doll_config.json
        "prop_firm_validation": str, # Path to prop_firm_validation.json
        "firm_rankings": str         # Path to firm_rankings.json
    },
    "config_files": [str],           # Paths to generated configs
    "backtest_data": {
        "equity_curve": [float],
        "trade_log": [dict],
        "daily_pnl": [float]
    },
    "metadata": {
        "symbol": str,
        "timeframe": str,
        "optimization_date": str,
        "bars_tested": int
    }
}
```

## Output
```python
{
    "package_path": str,             # Root directory of package
    "package_manifest": {
        "strategy_name": str,
        "version": str,
        "created_at": str,
        "files": [
            {"path": str, "type": str, "size_kb": float}
        ],
        "total_files": int,
        "total_size_kb": float
    },
    "deployment_ready": bool,
    "documentation_generated": bool
}
```

## Package Structure
```
strategies/{strategy_name}/
├── README.md                    # Auto-generated documentation
├── manifest.json                # Package manifest
├── CHANGELOG.md                 # Version history
│
├── src/                         # Source code
│   ├── __init__.py
│   ├── strategy.py              # Main strategy class
│   ├── indicators.py            # Custom indicators
│   └── utils.py                 # Utility functions
│
├── configs/                     # Configuration files
│   ├── default_config.json
│   ├── ES_config.json
│   └── apex_config.json
│
├── optimization/                # Optimization artifacts
│   ├── grid_results.json
│   ├── grid_heatmap.png
│   ├── perturbation_results.json
│   ├── mfe_analysis.json
│   └── russian_doll_config.json
│
├── validation/                  # Validation results
│   ├── prop_firm_validation.json
│   ├── firm_rankings.json
│   └── robustness_report.json
│
├── backtest/                    # Backtest artifacts
│   ├── equity_curve.json
│   ├── equity_curve.png
│   ├── trade_log.csv
│   ├── daily_pnl.json
│   └── performance_report.json
│
└── docs/                        # Documentation
    ├── strategy_overview.md
    ├── parameter_guide.md
    └── deployment_checklist.md
```

## Algorithm

### 1. Create Directory Structure
```python
def create_package_structure(strategy_name):
    base_path = f"strategies/{strategy_name}"
    dirs = ["src", "configs", "optimization", "validation", "backtest", "docs"]
    for d in dirs:
        os.makedirs(f"{base_path}/{d}", exist_ok=True)
    return base_path
```

### 2. Copy Source Files
```python
def copy_source_files(source_files, target_dir):
    for src in source_files:
        shutil.copy(src, f"{target_dir}/src/")
    # Create __init__.py
    write_init_file(f"{target_dir}/src/__init__.py")
```

### 3. Assemble Optimization Results
```python
def assemble_optimization(optimization_outputs, target_dir):
    for name, path in optimization_outputs.items():
        shutil.copy(path, f"{target_dir}/optimization/")
    # Generate heatmap visualization
    generate_grid_heatmap(optimization_outputs["grid_results"], target_dir)
```

### 4. Generate Documentation
```python
def generate_readme(strategy_info, metrics, target_dir):
    readme = f"""# {strategy_info['name']}

## Overview
- **Symbol**: {strategy_info['symbol']}
- **Timeframe**: {strategy_info['timeframe']}
- **Optimized**: {strategy_info['date']}

## Performance
| Metric | Value |
|--------|-------|
| Sharpe | {metrics['sharpe']:.2f} |
| Calmar | {metrics['calmar']:.2f} |
| Max DD | {metrics['max_dd']:.1f}% |
| Win Rate | {metrics['win_rate']:.1%} |

## Base Hit Configuration
- INNER: {metrics['inner_target']} ticks ({metrics['inner_pct']:.0%})
- MIDDLE: {metrics['middle_target']} ticks ({metrics['middle_pct']:.0%})
- OUTER: {metrics['outer_target']} ticks ({metrics['outer_pct']:.0%})

## Prop Firm Compatibility
Compatible with {metrics['firms_passed']} of 14 firms.
Top recommendations: {', '.join(metrics['top_firms'])}

## Deployment
1. Copy configs to trading system
2. Set up prop firm account
3. Configure risk limits
4. Enable in live trading

## Files
See manifest.json for complete file listing.
"""
    write_file(f"{target_dir}/README.md", readme)
```

### 5. Create Manifest
```python
def create_manifest(base_path, strategy_info):
    files = []
    total_size = 0
    for root, _, filenames in os.walk(base_path):
        for f in filenames:
            path = os.path.join(root, f)
            size = os.path.getsize(path) / 1024
            files.append({
                "path": path.replace(base_path, ""),
                "type": get_file_type(f),
                "size_kb": round(size, 2)
            })
            total_size += size

    manifest = {
        "strategy_name": strategy_info["name"],
        "version": "1.0.0",
        "created_at": datetime.now().isoformat(),
        "files": files,
        "total_files": len(files),
        "total_size_kb": round(total_size, 2)
    }
    write_json(f"{base_path}/manifest.json", manifest)
    return manifest
```

### 6. Generate Visualizations
- Equity curve chart (PNG)
- Grid search heatmap (PNG)
- Daily P&L histogram (PNG)
- Drawdown chart (PNG)

## Validation Checks
- [ ] All required files present
- [ ] JSON files are valid
- [ ] Source code imports correctly
- [ ] Configs reference correct files
- [ ] No sensitive data included
- [ ] Total package size < 10MB

## Invocation
Spawn @quant-artifact-builder when: All optimization and validation steps are complete. This is the final assembly step before routing.

## Dependencies
- Requires: All optimizer agents complete
- Feeds into: `quant-promo-router`

## Completion Marker
SUBAGENT_COMPLETE: quant-artifact-builder
FILES_CREATED: 15-25 (varies by strategy)
OUTPUT: Complete strategy package in strategies/{name}/
