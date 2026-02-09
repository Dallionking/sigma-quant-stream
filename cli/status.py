"""Sigma-Quant Stream -- Status dashboard."""

from __future__ import annotations

import datetime
import json
import subprocess
import time
from pathlib import Path

from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_config() -> dict:
    cfg_path = PROJECT_ROOT / "config.json"
    if cfg_path.exists():
        with open(cfg_path) as f:
            return json.load(f)
    return {}


def _get_worker_types(config: dict) -> list[str]:
    return config.get("workers", {}).get("types", [
        "researcher", "converter", "backtester", "optimizer",
    ])


def _check_tmux_running() -> dict[str, bool]:
    """Check which workers are running in tmux."""
    results: dict[str, bool] = {}
    workers = ["researcher", "converter", "backtester", "optimizer"]

    # Check main session
    try:
        result = subprocess.run(
            ["tmux", "list-panes", "-t", "sigma-quant", "-F", "#{pane_title}:#{pane_pid}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            pane_info = result.stdout.strip()
            for line in pane_info.splitlines():
                for worker in workers:
                    if worker in line.lower():
                        results[worker] = True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # Check if session exists at all
    if not results:
        try:
            result = subprocess.run(
                ["tmux", "has-session", "-t", "sigma-quant"],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                for worker in workers:
                    results.setdefault(worker, True)
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

    # Check individual worker sessions
    for worker in workers:
        if worker not in results:
            try:
                result = subprocess.run(
                    ["tmux", "has-session", "-t", f"quant-{worker}"],
                    capture_output=True, timeout=5,
                )
                if result.returncode == 0:
                    results[worker] = True
            except (subprocess.SubprocessError, FileNotFoundError):
                pass

    return results


def _count_files(directory: Path) -> int:
    """Count files (not dirs) in a directory."""
    if not directory.is_dir():
        return 0
    return sum(1 for f in directory.iterdir() if f.is_file())


def _count_strategies() -> dict[str, int]:
    """Count strategies by grade."""
    base = PROJECT_ROOT / "output" / "strategies"
    categories = ["good", "under_review", "rejected", "prop_firm_ready"]
    counts: dict[str, int] = {}
    for cat in categories:
        counts[cat] = _count_files(base / cat)
    return counts


def _load_cost_tracker() -> dict | None:
    """Load cost tracker data if available."""
    ct_path = PROJECT_ROOT / "cost-tracker.json"
    if ct_path.exists():
        try:
            with open(ct_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _load_recent_summaries(limit: int = 5) -> list[dict]:
    """Load recent session summaries."""
    summaries_dir = PROJECT_ROOT / "session-summaries"
    results: list[dict] = []

    if not summaries_dir.is_dir():
        return results

    # Collect all summary files sorted by modification time (newest first)
    files = sorted(
        [f for f in summaries_dir.iterdir() if f.is_file() and f.suffix in (".md", ".json", ".txt")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for f in files[:limit]:
        mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
        content = ""
        try:
            raw = f.read_text(errors="replace")
            # Extract first meaningful line
            for line in raw.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("{"):
                    content = line[:80]
                    break
            if not content and raw.strip():
                content = raw.strip()[:80]
        except OSError:
            content = "(unreadable)"

        results.append({
            "file": f.name,
            "time": mtime.strftime("%Y-%m-%d %H:%M"),
            "preview": content,
        })

    return results


def build_worker_table(config: dict) -> Table:
    """Build the worker status table."""
    table = Table(
        title="Workers",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("Worker", style="white", min_width=12)
    table.add_column("Status", min_width=10)
    table.add_column("Pane", justify="center", min_width=6)

    workers = _get_worker_types(config)
    tmux_status = _check_tmux_running()
    layout = config.get("workers", {}).get("layout", {})

    running_count = 0
    for i, worker in enumerate(workers):
        pane_key = f"pane_{i}"
        pane_label = pane_key
        for k, v in layout.items():
            if v == worker:
                pane_label = k
                break

        running = tmux_status.get(worker, False)
        if running:
            running_count += 1
        status_text = "[green bold]running[/green bold]" if running else "[dim]stopped[/dim]"
        table.add_row(worker, status_text, pane_label)

    table.caption = f"{running_count}/{len(workers)} active"
    return table


def build_queue_table(config: dict) -> Table:
    """Build the queue depths table."""
    table = Table(
        title="Queues",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("Queue", style="white", min_width=14)
    table.add_column("Items", justify="right", min_width=6)
    table.add_column("Status", min_width=8)

    queues = config.get("queues", {
        "hypotheses": "queues/hypotheses/",
        "toConvert": "queues/to-convert/",
        "toBacktest": "queues/to-backtest/",
        "toOptimize": "queues/to-optimize/",
    })

    total_items = 0
    for name, rel_path in queues.items():
        full_path = PROJECT_ROOT / rel_path
        count = _count_files(full_path)
        total_items += count

        if count == 0:
            count_str = "[dim]0[/dim]"
            status_str = "[dim]empty[/dim]"
        elif count <= 3:
            count_str = f"[green]{count}[/green]"
            status_str = "[green]ready[/green]"
        elif count <= 10:
            count_str = f"[yellow]{count}[/yellow]"
            status_str = "[yellow]queued[/yellow]"
        else:
            count_str = f"[red bold]{count}[/red bold]"
            status_str = "[red]backlog[/red]"

        table.add_row(name, count_str, status_str)

    table.caption = f"{total_items} total items"
    return table


def build_strategy_table() -> Table:
    """Build the strategy counts table."""
    table = Table(
        title="Strategies",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("Grade", style="white", min_width=16)
    table.add_column("Count", justify="right", min_width=6)
    table.add_column("Bar", min_width=12)

    counts = _count_strategies()
    grade_styles = {
        "prop_firm_ready": "bold green",
        "good": "green",
        "under_review": "yellow",
        "rejected": "red",
    }

    max_count = max(counts.values()) if counts.values() else 1
    total = sum(counts.values())

    for grade, count in counts.items():
        style = grade_styles.get(grade, "white")
        display_name = grade.replace("_", " ").title()

        # Visual bar
        bar_len = int((count / max_count) * 10) if max_count > 0 else 0
        bar_char = "=" * bar_len
        bar_empty = "." * (10 - bar_len)
        bar_str = f"[{style}]{bar_char}[/{style}][dim]{bar_empty}[/dim]"

        table.add_row(
            f"[{style}]{display_name}[/{style}]",
            str(count),
            bar_str,
        )

    table.caption = f"{total} total strategies"
    return table


def build_cost_panel() -> Panel | None:
    """Build cost tracker panel if data exists."""
    data = _load_cost_tracker()
    if not data:
        return None

    total = data.get("totalCost", data.get("total_cost", 0))
    sessions = data.get("sessionCount", data.get("session_count", 0))
    budget = data.get("budgetCap", data.get("budget_cap", 50.0))

    pct = (total / budget * 100) if budget > 0 else 0
    bar_width = 20
    bar_filled = min(int(pct / (100 / bar_width)), bar_width)
    bar_empty = bar_width - bar_filled

    if pct < 60:
        bar_color = "green"
    elif pct < 85:
        bar_color = "yellow"
    else:
        bar_color = "red"

    text = (
        f"  [{bar_color}]{'=' * bar_filled}[/{bar_color}]"
        f"[dim]{'.' * bar_empty}[/dim]"
        f"  ${total:.2f} / ${budget:.2f} ({pct:.0f}%)\n\n"
        f"  Sessions: {sessions}"
    )

    if sessions > 0:
        avg = total / sessions
        text += f"  |  Avg/session: ${avg:.2f}"

    return Panel(text, title="Cost Tracker", border_style="cyan")


def build_activity_panel() -> Panel | None:
    """Build recent activity panel from session summaries."""
    summaries = _load_recent_summaries(limit=5)
    if not summaries:
        return None

    lines: list[str] = []
    for s in summaries:
        lines.append(f"  [dim]{s['time']}[/dim]  {s['file']}")
        if s["preview"]:
            lines.append(f"    [dim]{s['preview']}[/dim]")

    return Panel(
        "\n".join(lines) if lines else "[dim]No recent activity[/dim]",
        title="Recent Activity",
        border_style="cyan",
    )


def build_dashboard() -> Group:
    """Build the complete dashboard as a renderable group."""
    config = _load_config()

    worker_table = build_worker_table(config)
    queue_table = build_queue_table(config)
    strategy_table = build_strategy_table()
    cost_panel = build_cost_panel()
    activity_panel = build_activity_panel()

    profile = config.get("activeProfile", "unknown")
    mode = config.get("defaults", {}).get("mode", "research")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    header = Text()
    header.append("Sigma-Quant Stream", style="bold cyan")
    header.append(" -- Status Dashboard\n", style="dim")
    header.append(f"Profile: {profile}  |  Mode: {mode}  |  {now}", style="dim")

    renderables: list = [
        Panel(header, border_style="cyan"),
        worker_table,
        queue_table,
        strategy_table,
    ]

    if cost_panel:
        renderables.append(cost_panel)
    if activity_panel:
        renderables.append(activity_panel)

    return Group(*renderables)


def show_status(watch: bool = False) -> None:
    """Display the full status dashboard."""
    if watch:
        from rich.live import Live

        console.print("[dim]Live mode -- refreshing every 5s. Press Ctrl+C to exit.[/dim]\n")
        try:
            with Live(build_dashboard(), console=console, refresh_per_second=0.2) as live:
                while True:
                    time.sleep(5)
                    live.update(build_dashboard())
        except KeyboardInterrupt:
            console.print("\n[dim]Stopped.[/dim]")
    else:
        console.print(build_dashboard())
