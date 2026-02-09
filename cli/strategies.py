"""Sigma-Quant Stream -- Strategy listing."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

STRATEGY_DIRS = {
    "prop_firm_ready": ("Prop Firm Ready", "bold green"),
    "good": ("Good", "green"),
    "under_review": ("Under Review", "yellow"),
    "rejected": ("Rejected", "red"),
}


def _load_strategy(path: Path) -> dict | None:
    """Load a strategy JSON file."""
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _extract_metrics(data: dict) -> dict:
    """Extract key metrics from a strategy file, handling varying schemas."""
    metrics = data.get("metrics", data.get("performance", data.get("results", {})))

    def _get(primary_key: str, *fallbacks: str):
        """Try multiple keys across metrics and top-level data."""
        for key in (primary_key, *fallbacks):
            val = metrics.get(key)
            if val is not None:
                return val
            val = data.get(key)
            if val is not None:
                return val
        return None

    sharpe = _get("sharpe_ratio", "sharpe")
    win_rate = _get("win_rate", "winRate", "win_pct")
    max_dd = _get("max_drawdown", "maxDrawdown", "max_dd", "drawdown")
    trades = _get("total_trades", "trades", "trade_count", "num_trades")
    grade = data.get("grade", data.get("rating", "N/A"))
    profit_factor = _get("profit_factor", "profitFactor")

    # Prop firm compliance
    prop_firms_passed: list[str] = []
    compliance = data.get("compliance", data.get("propFirmResults", {}))
    if isinstance(compliance, dict):
        for firm, result in compliance.items():
            if isinstance(result, dict) and result.get("passed", False):
                prop_firms_passed.append(firm)
            elif isinstance(result, bool) and result:
                prop_firms_passed.append(firm)
    elif isinstance(compliance, list):
        for item in compliance:
            if isinstance(item, dict) and item.get("passed", False):
                prop_firms_passed.append(item.get("firm", item.get("name", "")))

    return {
        "sharpe": sharpe if sharpe is not None else "N/A",
        "win_rate": win_rate if win_rate is not None else "N/A",
        "max_dd": max_dd if max_dd is not None else "N/A",
        "trades": trades if trades is not None else "N/A",
        "grade": grade,
        "profit_factor": profit_factor if profit_factor is not None else "N/A",
        "prop_firms_passed": prop_firms_passed,
    }


def _format_sharpe(val: object) -> str:
    if isinstance(val, (int, float)):
        if val >= 1.5:
            style = "green"
        elif val >= 1.0:
            style = "yellow"
        else:
            style = "red"
        return f"[{style}]{val:.2f}[/{style}]"
    return str(val)


def _format_win_rate(val: object) -> str:
    if isinstance(val, (int, float)):
        pct = val * 100 if val <= 1 else val
        if pct >= 55:
            style = "green"
        elif pct >= 45:
            style = "yellow"
        else:
            style = "red"
        return f"[{style}]{pct:.1f}%[/{style}]"
    return str(val)


def _format_max_dd(val: object) -> str:
    if isinstance(val, (int, float)):
        pct = abs(val) * 100 if abs(val) <= 1 else abs(val)
        if pct <= 15:
            style = "green"
        elif pct <= 25:
            style = "yellow"
        else:
            style = "red"
        return f"[{style}]{pct:.1f}%[/{style}]"
    return str(val)


def _format_trades(val: object) -> str:
    if isinstance(val, (int, float)):
        count = int(val)
        if count >= 200:
            style = "green"
        elif count >= 100:
            style = "yellow"
        else:
            style = "red"
        return f"[{style}]{count}[/{style}]"
    return str(val)


def _format_grade(val: str) -> str:
    grade_colors = {
        "A+": "bold green",
        "A": "green",
        "B+": "cyan",
        "B": "cyan",
        "C+": "yellow",
        "C": "yellow",
        "D": "red",
        "F": "bold red",
    }
    style = grade_colors.get(str(val).upper(), "white")
    return f"[{style}]{val}[/{style}]"


def _format_prop_firms(firms: list[str]) -> str:
    count = len(firms)
    if count == 0:
        return "[dim]0[/dim]"
    elif count >= 5:
        return f"[bold green]{count}[/bold green]"
    elif count >= 3:
        return f"[green]{count}[/green]"
    else:
        return f"[yellow]{count}[/yellow]"


def list_strategies(grade_filter: str | None = None) -> None:
    """List all discovered strategies with metrics."""
    base = PROJECT_ROOT / "output" / "strategies"

    if not base.is_dir():
        console.print(Panel(
            "[yellow]No output/strategies/ directory found.[/yellow]\n\n"
            "Run the research pipeline to discover strategies, or\n"
            "try [cyan]sigma-quant tutorial[/cyan] to learn the workflow.",
            title="No Strategies",
            border_style="yellow",
        ))
        return

    table = Table(
        title="Discovered Strategies",
        show_header=True,
        header_style="bold cyan",
        show_lines=True,
        border_style="dim",
    )
    table.add_column("Name", style="white", min_width=20, max_width=35)
    table.add_column("Grade", justify="center", min_width=6)
    table.add_column("Category", min_width=16)
    table.add_column("Sharpe", justify="right", min_width=8)
    table.add_column("Win Rate", justify="right", min_width=9)
    table.add_column("Max DD", justify="right", min_width=8)
    table.add_column("Trades", justify="right", min_width=7)
    table.add_column("Prop Firms", justify="right", min_width=10)

    total = 0
    dirs_to_scan = list(STRATEGY_DIRS.items())

    if grade_filter:
        key = grade_filter.lower().replace(" ", "_")
        if key in STRATEGY_DIRS:
            dirs_to_scan = [(key, STRATEGY_DIRS[key])]
        else:
            console.print(f"[red]Unknown grade filter: {grade_filter}[/red]")
            console.print(f"Available: {', '.join(STRATEGY_DIRS.keys())}")
            return

    for dir_name, (display_name, style) in dirs_to_scan:
        dir_path = base / dir_name
        if not dir_path.is_dir():
            continue

        for file_path in sorted(dir_path.glob("*.json")):
            data = _load_strategy(file_path)
            if not data:
                continue

            m = _extract_metrics(data)
            name = data.get("name", data.get("strategy_name", file_path.stem))

            table.add_row(
                name,
                _format_grade(m["grade"]),
                f"[{style}]{display_name}[/{style}]",
                _format_sharpe(m["sharpe"]),
                _format_win_rate(m["win_rate"]),
                _format_max_dd(m["max_dd"]),
                _format_trades(m["trades"]),
                _format_prop_firms(m["prop_firms_passed"]),
            )
            total += 1

    if total == 0:
        console.print("[dim]No strategies found in output/strategies/.[/dim]")
        console.print("Run [cyan]sigma-quant tutorial[/cyan] to get started.")
    else:
        console.print(table)

        # Summary panel
        counts = {}
        for dir_name in STRATEGY_DIRS:
            d = base / dir_name
            if d.is_dir():
                counts[dir_name] = sum(1 for f in d.glob("*.json"))
            else:
                counts[dir_name] = 0

        summary_parts = []
        for dir_name, (display_name, style) in STRATEGY_DIRS.items():
            c = counts.get(dir_name, 0)
            if c > 0:
                summary_parts.append(f"[{style}]{display_name}: {c}[/{style}]")

        console.print(f"\n  {total} strategies total  |  {' | '.join(summary_parts)}")
