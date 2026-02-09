#!/usr/bin/env python3
"""
generate-backlog.py - Backlog Generator for Quant Research Team
================================================================

⚠️  DEPRECATED - 2026-01-18 ⚠️
This script is deprecated. The Quant Team has moved from task-based
architecture (pre-generated backlogs) to mission-based architecture
(infinite autonomous discovery).

Workers now receive mission prompts from prompts/ and
communicate via queue directories in queues/.

See: quant-ralph.sh, tmux-quant-launcher.sh for the new architecture.

This file is kept for reference only.
================================================================

Generates pane-specific backlogs based on worker distribution preset.
Each pane gets tasks appropriate to its assigned worker type.

Usage:
    python generate-backlog.py                     # Use balanced distribution
    python generate-backlog.py --preset=research_heavy
    python generate-backlog.py --panes=8 --iterations=200
    python generate-backlog.py --regenerate        # Regenerate all backlogs
    python generate-backlog.py --pane=3            # Regenerate single pane

Presets:
    balanced       - 2 researchers, 1 converter, 2 backtesters, 1 optimizer
    research_heavy - 4 researchers, 1 converter, 1 backtester
    backtest_heavy - 1 researcher, 4 backtesters, 1 optimizer
    full_cycle     - 6 full-cycle workers (each does everything)
"""

import os
import sys
import json
import argparse
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configuration paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_FILE = PROJECT_ROOT / "config.json"
BACKLOGS_DIR = PROJECT_ROOT / "backlogs"
SCHEMA_DIR = PROJECT_ROOT / "schemas"


def load_config() -> Dict[str, Any]:
    """Load team configuration."""
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


# Task templates by worker type - each includes description templates for specificity
TASK_TEMPLATES = {
    "researcher": [
        {
            "type": "research_new_indicator",
            "title_templates": [
                "Research {concept} indicator patterns for {symbol}",
                "Find and analyze {concept} strategies",
                "Investigate {concept} as trading signal",
                "Research {author}'s approach to {concept}",
            ],
            "description_templates": [
                "Use MCP tools to find academic papers and implementations of {concept}. Create a research summary in output/research-logs/{date}/ and a hypothesis JSON in output/hypotheses/. Focus on why the edge exists and who the counterparty is.",
                "Search for {concept} strategies using mcp_exa_web_search_exa and mcp_Ref_ref_search_documentation. Document findings with testable hypothesis including expected Sharpe ratio.",
            ],
            "concepts": [
                "RSI divergence", "VWAP", "volume profile", "order flow",
                "mean reversion", "momentum", "breakout", "volatility regime",
                "market microstructure", "support/resistance", "pivot points",
                "Fibonacci retracements", "Elliott wave", "Wyckoff", "ICT concepts",
            ],
            "authors": [
                "De Prado", "Chan", "Aronson", "Clenow", "Kaufman",
            ],
        },
        {
            "type": "research_book_paper",
            "title_templates": [
                "Distill key insights from {book}",
                "Extract trading rules from {book}",
                "Summarize {concept} from {book}",
            ],
            "description_templates": [
                "Read/search for content from '{book}' using MCP tools. Extract actionable trading rules and document in output/research-logs/{date}/. Include parameter recommendations and anti-overfitting considerations.",
            ],
            "books": [
                "Advances in Financial Machine Learning",
                "Trading and Exchanges",
                "Active Portfolio Management",
                "Quantitative Trading",
                "Evidence-Based Technical Analysis",
                "Machine Learning for Algorithmic Trading",
            ],
        },
        {
            "type": "research_framework",
            "title_templates": [
                "Implement {framework} for futures trading",
                "Research and document {framework}",
                "Create implementation plan for {framework}",
            ],
            "description_templates": [
                "Research {framework} implementation details. Create documentation in output/research-logs/ with code examples and parameter recommendations. Focus on practical implementation for futures trading.",
            ],
            "frameworks": [
                "triple barrier method",
                "meta-labeling",
                "fractional differentiation",
                "walk-forward optimization",
                "probability of backtest overfitting (PBO)",
                "combinatorial purged cross-validation",
                "feature importance with MDI/MDA/SFI",
            ],
        },
        {
            "type": "generate_hypothesis",
            "title_templates": [
                "Generate hypothesis for {market} trading",
                "Document hypothesis for {concept} strategy",
                "Create testable hypothesis for {concept}",
            ],
            "description_templates": [
                "Create a testable trading hypothesis for {market}. Output a hypothesis JSON to output/hypotheses/ with: hypothesis statement, counterparty analysis, edge source, expected Sharpe, and required indicators.",
            ],
            "markets": ["ES", "NQ", "YM", "RTY", "GC", "CL"],
        },
    ],
    "converter": [
        {
            "type": "convert_pinescript",
            "title_templates": [
                "Convert {indicator} from PineScript to Python",
                "Port TradingView {indicator} to Python",
                "Recreate {indicator} indicator in Python",
            ],
            "description_templates": [
                "Find {indicator} PineScript source using mcp_exa_web_search_exa. Convert to Python class in output/indicators/converted/{indicator_lower}/. Include: {indicator_lower}.py (class with calculate() and get_signal()), test_{indicator_lower}.py (unit tests), README.md (usage docs).",
            ],
            "indicators": [
                "SuperTrend", "MACD Histogram Divergence", "Volume Weighted RSI",
                "Squeeze Momentum", "Market Cipher", "Pivot Points Standard",
                "ATR Trailing Stop", "Donchian Channels", "Keltner Channels",
                "VWAP with Standard Deviation Bands", "Opening Range Breakout",
                "Order Block Detector", "Fair Value Gap Finder", "SMT Divergence",
            ],
        },
        {
            "type": "convert_indicator",
            "title_templates": [
                "Convert {source} {indicator} implementation",
                "Recreate {indicator} from {source} to Python",
            ],
            "description_templates": [
                "Find {indicator} implementation from {source}. Convert to Python using pandas/numpy. Save to output/indicators/converted/{indicator_lower}/ with full class implementation, tests, and documentation.",
            ],
            "sources": ["TradingView", "NinjaTrader", "MetaTrader", "QuantConnect"],
        },
    ],
    "backtester": [
        {
            "type": "backtest_strategy",
            "title_templates": [
                "Backtest {strategy} on {symbol}",
                "Run full backtest for {strategy}",
                "Validate {strategy} with costs and slippage",
            ],
            "description_templates": [
                "Backtest {strategy} strategy on {symbol} with: $2.50/side commission, 0.5 tick slippage, minimum 100 trades. Calculate Sharpe, max DD, win rate. Auto-reject if Sharpe>3.0 or win rate>80%. Save JSON results to output/backtests/{date}/.",
            ],
            "strategies": [
                "mean reversion", "momentum breakout", "gap fade",
                "VWAP bounce", "opening range breakout", "pivot reversal",
                "volatility contraction", "trend following", "counter-trend",
            ],
        },
        {
            "type": "backtest_walk_forward",
            "title_templates": [
                "Run walk-forward validation for {strategy}",
                "Test OOS performance of {strategy}",
                "Validate {strategy} generalization",
            ],
            "description_templates": [
                "Run 5-window walk-forward validation for {strategy}. Use 70/30 train/test split per window. Calculate OOS decay (reject if >50%). Save results with in-sample and out-of-sample metrics to output/backtests/{date}/.",
            ],
        },
        {
            "type": "combine_indicators",
            "title_templates": [
                "Test {indicator1} + {indicator2} combination",
                "Combine {indicator1} with {indicator2} for {symbol}",
            ],
            "description_templates": [
                "Test combining {indicator1} with {indicator2} as entry filter on {symbol}. Document hypothesis first. Run backtest with costs. Save results showing improvement vs single indicator to output/backtests/{date}/.",
            ],
            "indicators": [
                "RSI", "MACD", "VWAP", "ATR", "Bollinger Bands",
                "Stochastic", "CCI", "MFI", "OBV", "Volume Profile",
            ],
        },
    ],
    "optimizer": [
        {
            "type": "optimize_params",
            "title_templates": [
                "Optimize parameters for {strategy}",
                "Run grid search for {strategy} params",
                "Find optimal settings for {strategy}",
            ],
            "description_templates": [
                "Optimize {strategy} parameters using coarse grid search (e.g., [7,10,14,21,28] not [10,11,12...]). Test ±20% perturbation - reject knife-edge optima. Ensure range ratio <30%. Save optimization results with robustness analysis to output/strategies/optimizations/.",
            ],
        },
        {
            "type": "optimize_base_hit",
            "title_templates": [
                "Calculate Base Hit for {strategy}",
                "Optimize loss MFE cash exit for {strategy}",
                "Run Base Hit analysis on {strategy}",
            ],
            "description_templates": [
                "Analyze losing trades for {strategy} to find average Maximum Favorable Excursion (MFE). Set cash exit at loss MFE average. Calculate expected savings from converting losses to small wins. Save base_hit_config.json to output/strategies/{strategy}/.",
            ],
        },
    ],
    "prop_firm_validator": [
        {
            "type": "validate_prop_firm",
            "title_templates": [
                "Validate {strategy} against all 14 prop firms",
                "Test {strategy} prop firm compliance",
                "Run prop firm simulation for {strategy}",
            ],
            "description_templates": [
                "Simulate {strategy} against all 14 prop firms (TakeProfitTrader, TopStep, Apex 3.0, Tradeify, etc.). Check: daily loss limits, trailing drawdown, consistency rules. Mark deployment-ready if passes ≥3 firms. Save results to output/strategies/prop_firm_ready/.",
            ],
        },
        {
            "type": "deployment",
            "title_templates": [
                "Deploy {strategy} to production",
                "Package {strategy} for deployment",
            ],
            "description_templates": [
                "Package {strategy} for deployment. Create strategy class with signal generation, position sizing, and risk limits. Ensure passes all quality gates before marking complete.",
            ],
        },
    ],
    "knowledge_distiller": [
        {
            "type": "distill_knowledge",
            "title_templates": [
                "Distill learnings from {source}",
                "Create knowledge summary from {days} days of research",
                "Document patterns found in {area}",
            ],
            "description_templates": [
                "Analyze all outputs in output/ from {source}. Create daily summary in output/research-logs/daily/{date}-summary.md. Document: strategies tested, pass rate, top performers, rejections & learnings. Update what-works.md and what-fails.md in patterns/.",
            ],
            "sources": ["today's backtests", "rejected strategies", "research logs"],
            "areas": ["mean reversion", "momentum", "volatility", "prop firm rules"],
        },
    ],
    "full_cycle": [
        # Full cycle workers do everything - inherit from all types
    ],
}


def generate_task_content(template: Dict[str, Any], config: Dict) -> Dict[str, str]:
    """Generate task title, description, and expected output from template."""
    import random
    from datetime import datetime

    title_template = random.choice(template["title_templates"])
    desc_templates = template.get("description_templates", ["Complete the assigned task."])
    desc_template = random.choice(desc_templates)

    # Substitute placeholders
    placeholders = {
        "date": datetime.now().strftime("%Y-%m-%d"),
    }

    if "{concept}" in title_template or "{concept}" in desc_template:
        placeholders["concept"] = random.choice(template.get("concepts", ["momentum"]))

    if "{symbol}" in title_template or "{symbol}" in desc_template:
        placeholders["symbol"] = random.choice(config["symbols"]["primary"])

    if "{author}" in title_template or "{author}" in desc_template:
        placeholders["author"] = random.choice(template.get("authors", ["De Prado"]))

    if "{book}" in title_template or "{book}" in desc_template:
        placeholders["book"] = random.choice(template.get("books", ["Quantitative Trading"]))

    if "{framework}" in title_template or "{framework}" in desc_template:
        placeholders["framework"] = random.choice(template.get("frameworks", ["walk-forward"]))

    if "{market}" in title_template or "{market}" in desc_template:
        placeholders["market"] = random.choice(config["symbols"]["primary"])

    if "{indicator}" in title_template or "{indicator}" in desc_template:
        indicator = random.choice(template.get("indicators", ["RSI"]))
        placeholders["indicator"] = indicator
        placeholders["indicator_lower"] = indicator.lower().replace(" ", "_")

    if "{source}" in title_template or "{source}" in desc_template:
        placeholders["source"] = random.choice(template.get("sources", ["TradingView"]))

    if "{strategy}" in title_template or "{strategy}" in desc_template:
        placeholders["strategy"] = random.choice(template.get("strategies", ["momentum"]))

    if "{indicator1}" in title_template or "{indicator1}" in desc_template:
        all_indicators = template.get("indicators", ["RSI", "MACD"])
        ind1 = random.choice(all_indicators)
        placeholders["indicator1"] = ind1
        remaining = [i for i in all_indicators if i != ind1]
        placeholders["indicator2"] = random.choice(remaining) if remaining else "VWAP"

    if "{days}" in title_template or "{days}" in desc_template:
        placeholders["days"] = str(random.choice([1, 3, 7]))

    if "{area}" in title_template or "{area}" in desc_template:
        placeholders["area"] = random.choice(template.get("areas", ["momentum"]))

    # Generate title and description
    title = title_template.format(**placeholders)
    description = desc_template.format(**placeholders)

    # Generate expected output path based on task type
    task_type = template["type"]
    expected_output = generate_expected_output(task_type, placeholders)

    return {
        "title": title,
        "description": description,
        "expectedOutput": expected_output,
    }


def generate_expected_output(task_type: str, placeholders: Dict) -> str:
    """Generate expected output path based on task type."""
    date = placeholders.get("date", datetime.now().strftime("%Y-%m-%d"))
    
    output_paths = {
        "research_new_indicator": f"output/research-logs/{date}/",
        "research_book_paper": f"output/research-logs/{date}/",
        "research_framework": f"output/research-logs/{placeholders.get('framework', 'framework')}.md",
        "generate_hypothesis": f"output/hypotheses/hypothesis-{placeholders.get('market', 'ES').lower()}-001.json",
        "convert_pinescript": f"output/indicators/converted/{placeholders.get('indicator_lower', 'indicator')}/",
        "convert_indicator": f"output/indicators/converted/{placeholders.get('indicator_lower', 'indicator')}/",
        "backtest_strategy": f"output/backtests/{date}/",
        "backtest_walk_forward": f"output/backtests/{date}/",
        "combine_indicators": f"output/backtests/{date}/",
        "optimize_params": f"output/strategies/optimizations/",
        "optimize_base_hit": f"output/strategies/{placeholders.get('strategy', 'strategy')}/base_hit_config.json",
        "validate_prop_firm": f"output/strategies/prop_firm_ready/",
        "deployment": f"output/strategies/deployed/",
        "distill_knowledge": f"output/research-logs/daily/{date}-summary.md",
    }
    
    return output_paths.get(task_type, f"output/{task_type}/")


def get_acceptance_criteria(task_type: str, config: Dict) -> List[Dict]:
    """Get acceptance criteria based on task type."""
    validation = config["validation"]["strategy"]

    criteria_map = {
        "research_new_indicator": [
            {"type": "file_exists", "path": "output/indicators/created/{indicator}.py"},
            {"type": "hypothesis_documented"},
            {"type": "no_mock_data", "provider": config["dataProviders"]["default"]},
        ],
        "research_book_paper": [
            {"type": "file_exists", "path": "output/research-logs/{date}-summary.md"},
        ],
        "research_framework": [
            {"type": "file_exists", "path": "output/research-logs/{framework}.md"},
            {"type": "hypothesis_documented"},
        ],
        "research_strategy_idea": [
            {"type": "hypothesis_documented"},
        ],
        "generate_hypothesis": [
            {"type": "hypothesis_documented"},
        ],
        "convert_pinescript": [
            {"type": "file_exists", "path": "output/indicators/converted/{indicator}.py"},
            {"type": "no_mock_data", "provider": config["dataProviders"]["default"]},
        ],
        "convert_indicator": [
            {"type": "file_exists", "path": "output/indicators/converted/{indicator}.py"},
        ],
        "backtest_strategy": [
            {"type": "backtest_passes"},
            {"type": "sharpe_range", "minSharpe": validation["minSharpe"], "maxSharpe": validation["maxSharpe"]},
            {"type": "min_trades", "minTrades": validation["minTrades"]},
            {"type": "max_win_rate", "maxWinRate": validation["maxWinRate"]},
            {"type": "no_mock_data", "provider": config["dataProviders"]["default"]},
        ],
        "backtest_walk_forward": [
            {"type": "backtest_passes"},
            {"type": "oos_decay", "maxDecay": validation["maxOosDecay"]},
            {"type": "min_trades", "minTrades": validation["minTrades"]},
        ],
        "combine_indicators": [
            {"type": "hypothesis_documented"},
            {"type": "backtest_passes"},
        ],
        "optimize_params": [
            {"type": "backtest_passes"},
            {"type": "oos_decay", "maxDecay": validation["maxOosDecay"]},
        ],
        "optimize_base_hit": [
            {"type": "base_hit_complete"},
            {"type": "file_exists", "path": "output/strategies/{strategy}/base_hit_config.json"},
        ],
        "validate_prop_firm": [
            {"type": "prop_firm_passes", "minFirmsPassing": config["validation"]["propFirmMinPassing"]},
        ],
        "deployment": [
            {"type": "file_exists", "path": "output/strategies/deployed/{strategy}.py"},
            {"type": "code_review_passed"},
        ],
        "distill_knowledge": [
            {"type": "file_exists", "path": "output/research-logs/{date}-distilled.md"},
        ],
    }

    return criteria_map.get(task_type, [])


# Parallel group assignments (from Ralphy pattern)
# Tasks in lower groups must complete before higher groups start
# This ensures proper pipeline ordering: research → backtest → optimize → validate
PARALLEL_GROUPS = {
    # Research tasks run first (group 0-1)
    "research_new_indicator": 0,
    "research_book_paper": 0,
    "research_framework": 0,
    "research_strategy_idea": 0,
    "generate_hypothesis": 1,
    # Conversion tasks run early (group 1)
    "convert_pinescript": 1,
    "convert_indicator": 1,
    # Backtesting runs after research (group 2)
    "backtest_strategy": 2,
    "backtest_walk_forward": 2,
    "combine_indicators": 2,
    # Optimization runs after backtesting (group 3)
    "optimize_params": 3,
    "optimize_base_hit": 3,
    # Validation runs after optimization (group 4)
    "validate_prop_firm": 4,
    "deployment": 5,
    # Knowledge distillation runs last (group 5)
    "distill_knowledge": 5,
}


def get_parallel_group(task_type: str) -> int:
    """Get the parallel group for a task type."""
    return PARALLEL_GROUPS.get(task_type, 2)  # Default to middle group


def generate_tasks_for_worker(
    worker_type: str,
    pane_id: int,
    num_tasks: int,
    config: Dict,
) -> List[Dict]:
    """Generate tasks for a specific worker type."""
    tasks = []

    # Get templates for this worker type
    if worker_type == "full_cycle":
        # Full cycle gets tasks from all types
        all_templates = []
        for wtype, templates in TASK_TEMPLATES.items():
            if wtype != "full_cycle":
                all_templates.extend(templates)
        templates = all_templates
    else:
        templates = TASK_TEMPLATES.get(worker_type, [])

    if not templates:
        return tasks

    # Generate tasks
    for i in range(num_tasks):
        template = random.choice(templates)
        task_type = template["type"]

        task_id = f"{task_type.split('_')[0]}-{i+1:03d}"
        
        # Generate title, description, and expected output
        task_content = generate_task_content(template, config)

        task = {
            "id": task_id,
            "type": task_type,
            "status": "pending",
            "priority": random.randint(1, 5) if i > 0 else 1,  # First task is always priority 1
            "parallel_group": get_parallel_group(task_type),  # Ralphy-style parallel groups
            "title": task_content["title"],
            "description": task_content["description"],
            "expectedOutput": task_content["expectedOutput"],
            "acceptanceCriteria": get_acceptance_criteria(task_type, config),
        }

        # Add hypothesis placeholder for strategy-related tasks
        if task_type in ["research_strategy_idea", "generate_hypothesis", "backtest_strategy"]:
            task["hypothesis"] = ""  # Worker must fill this in

        tasks.append(task)

    # Sort tasks by parallel_group to ensure proper ordering
    tasks.sort(key=lambda t: (t["parallel_group"], t["priority"]))

    return tasks


def get_pane_assignments(
    num_panes: int,
    preset: str,
    config: Dict,
) -> List[Dict[str, Any]]:
    """Get worker assignments for each pane based on preset."""
    distribution = config["workers"]["distribution"].get(preset, {})

    assignments = []
    pane_num = 1

    for worker_type, count in distribution.items():
        for _ in range(count):
            if pane_num > num_panes:
                break
            assignments.append({
                "pane": pane_num,
                "workerType": worker_type,
            })
            pane_num += 1

    # Fill remaining panes with researchers if preset doesn't cover all
    while pane_num <= num_panes:
        assignments.append({
            "pane": pane_num,
            "workerType": "researcher",
        })
        pane_num += 1

    return assignments


def generate_backlog(
    pane_id: int,
    worker_type: str,
    target_iterations: int,
    config: Dict,
    seed_tasks: List[Dict] = None,
) -> Dict[str, Any]:
    """Generate a complete backlog for a pane."""
    # Calculate tasks per iteration (roughly 1 task per 2 iterations on average)
    num_tasks = max(10, target_iterations // 2)

    tasks = generate_tasks_for_worker(worker_type, pane_id, num_tasks, config)

    # Add seed tasks if provided (for first pane of type)
    if seed_tasks:
        for i, seed in enumerate(seed_tasks):
            seed_task = {
                "id": f"seed-{i+1:03d}",
                "type": seed.get("type", "research_strategy_idea"),
                "passes": False,
                "priority": seed.get("priority", 1),
                "title": seed.get("title", "Seed task"),
                "acceptanceCriteria": get_acceptance_criteria(seed.get("type", "research_strategy_idea"), config),
            }
            tasks.insert(i, seed_task)

    backlog = {
        "meta": {
            "paneId": pane_id,
            "workerType": worker_type,
            "targetIterations": target_iterations,
            "completedIterations": 0,
            "strategiesValidated": 0,
            "strategiesRejected": 0,
            "createdAt": datetime.now().isoformat(),
            "lastUpdatedAt": datetime.now().isoformat(),
            "status": "active",
        },
        "tasks": tasks,
    }

    return backlog


def save_backlog(backlog: Dict[str, Any]) -> Path:
    """Save backlog to file."""
    BACKLOGS_DIR.mkdir(parents=True, exist_ok=True)

    pane_id = backlog["meta"]["paneId"]
    worker_type = backlog["meta"]["workerType"]

    filename = f"pane-{pane_id}-{worker_type}.json"
    filepath = BACKLOGS_DIR / filename

    with open(filepath, 'w') as f:
        json.dump(backlog, f, indent=2)

    return filepath


def generate_all_backlogs(
    num_panes: int,
    iterations: int,
    preset: str,
    config: Dict,
    regenerate: bool = False,
) -> List[Path]:
    """Generate backlogs for all panes."""
    assignments = get_pane_assignments(num_panes, preset, config)
    generated = []

    # Get seed tasks from config (only for first researcher)
    seed_tasks = config.get("research", {}).get("seedTasks", [])
    first_researcher_done = False

    for assignment in assignments:
        pane_id = assignment["pane"]
        worker_type = assignment["workerType"]

        # Check if backlog already exists
        existing = BACKLOGS_DIR / f"pane-{pane_id}-{worker_type}.json"
        if existing.exists() and not regenerate:
            print(f"Skipping pane {pane_id} ({worker_type}) - backlog exists")
            generated.append(existing)
            continue

        # Add seed tasks to first researcher only
        pane_seeds = None
        if worker_type == "researcher" and not first_researcher_done:
            pane_seeds = seed_tasks
            first_researcher_done = True

        backlog = generate_backlog(
            pane_id=pane_id,
            worker_type=worker_type,
            target_iterations=iterations,
            config=config,
            seed_tasks=pane_seeds,
        )

        filepath = save_backlog(backlog)
        generated.append(filepath)
        print(f"Generated: {filepath.name} ({len(backlog['tasks'])} tasks)")

    return generated


def main():
    parser = argparse.ArgumentParser(
        description="Generate backlogs for Quant Research Team"
    )

    parser.add_argument(
        "--preset",
        choices=["balanced", "research_heavy", "backtest_heavy", "full_cycle"],
        default="balanced",
        help="Worker distribution preset"
    )
    parser.add_argument(
        "--panes",
        type=int,
        default=None,
        help="Number of panes (default: from config)"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Target iterations per pane (default: from config)"
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate existing backlogs"
    )
    parser.add_argument(
        "--pane",
        type=int,
        help="Regenerate only this pane"
    )
    parser.add_argument(
        "--worker",
        choices=["researcher", "converter", "backtester", "optimizer",
                 "prop_firm_validator", "knowledge_distiller", "full_cycle"],
        help="Worker type (required with --pane)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing backlogs"
    )

    args = parser.parse_args()

    # Set random seed if specified
    if args.seed:
        random.seed(args.seed)

    config = load_config()

    # Get defaults from config
    num_panes = args.panes or config["defaults"]["panes"]
    iterations = args.iterations or config["defaults"]["iterations"]

    if args.list:
        # List existing backlogs
        if not BACKLOGS_DIR.exists():
            print("No backlogs directory found")
            return

        backlogs = list(BACKLOGS_DIR.glob("pane-*.json"))
        if not backlogs:
            print("No backlogs found")
            return

        print(f"\nExisting backlogs in {BACKLOGS_DIR}:")
        print("-" * 60)

        for path in sorted(backlogs):
            with open(path) as f:
                data = json.load(f)
            meta = data["meta"]
            print(f"  Pane {meta['paneId']:2d} | {meta['workerType']:<20} | "
                  f"{len(data['tasks']):3d} tasks | {meta['status']}")

        return

    if args.pane:
        # Regenerate single pane
        if not args.worker:
            print("Error: --worker required with --pane")
            sys.exit(1)

        backlog = generate_backlog(
            pane_id=args.pane,
            worker_type=args.worker,
            target_iterations=iterations,
            config=config,
        )

        filepath = save_backlog(backlog)

        if args.json:
            print(json.dumps(backlog, indent=2))
        else:
            print(f"Generated: {filepath}")
            print(f"  Worker: {args.worker}")
            print(f"  Tasks: {len(backlog['tasks'])}")
            print(f"  Iterations: {iterations}")

        return

    # Generate all backlogs
    print(f"Generating backlogs for {num_panes} panes using '{args.preset}' preset")
    print(f"Target iterations: {iterations}")
    print()

    generated = generate_all_backlogs(
        num_panes=num_panes,
        iterations=iterations,
        preset=args.preset,
        config=config,
        regenerate=args.regenerate,
    )

    print()
    print(f"Generated {len(generated)} backlogs in {BACKLOGS_DIR}")

    if args.json:
        result = {
            "preset": args.preset,
            "panes": num_panes,
            "iterations": iterations,
            "backlogs": [str(p) for p in generated],
        }
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
