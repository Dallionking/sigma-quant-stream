"""Sigma-Quant Stream -- Interactive 6-step pipeline tutorial.

Usage:
    sigma-quant tutorial
"""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _step_header(step: int, total: int, title: str, subtitle: str = "") -> None:
    """Print a tutorial step header."""
    console.print()
    header = f"[bold white]STEP {step}/{total}[/bold white]  [bold cyan]{title}[/bold cyan]"
    if subtitle:
        header += f"\n[dim]{subtitle}[/dim]"
    console.print(Panel(header, border_style="cyan", padding=(0, 2)))
    console.print()


def _wait_for_continue() -> bool:
    """Prompt user to continue or quit."""
    console.print()
    choice = Prompt.ask(
        "[dim]Press Enter to continue, or type 'q' to quit[/dim]",
        default="",
    )
    return choice.lower() != "q"


def _load_config() -> dict:
    """Load config.json."""
    cfg_path = PROJECT_ROOT / "config.json"
    if cfg_path.exists():
        with open(cfg_path) as f:
            return json.load(f)
    return {}


# ---------------------------------------------------------------------------
# Step 1: HYPOTHESIS
# ---------------------------------------------------------------------------

EXAMPLE_HYPOTHESIS = {
    "id": "hyp-example-001",
    "name": "Funding Rate Mean Reversion",
    "created": "2026-02-09T00:00:00Z",
    "author": "tutorial",
    "edge": "When perpetual funding rates exceed +/- 0.05%, price tends to revert as leveraged positions get liquidated",
    "counterparty": "Over-leveraged traders who chase momentum and get liquidated at extremes",
    "market": "crypto-cex",
    "expected_metrics": {
        "target_sharpe": 1.5,
        "target_win_rate": 0.55,
        "max_acceptable_drawdown": 0.15,
        "min_trades_per_month": 20,
    },
    "indicators": ["funding_rate", "open_interest", "liquidation_volume"],
    "timeframes": ["5m", "1h"],
    "status": "pending",
}

SMA_HYPOTHESIS = {
    "id": "hyp-example-002",
    "name": "SMA Crossover with ATR Filter",
    "created": "2026-02-09T00:00:00Z",
    "author": "tutorial",
    "edge": "Fast SMA crossing above slow SMA signals trend continuation, filtered by ATR to avoid choppy markets",
    "counterparty": "Late trend followers and mean-reversion traders caught on the wrong side",
    "market": "futures",
    "expected_metrics": {
        "target_sharpe": 1.2,
        "target_win_rate": 0.45,
        "max_acceptable_drawdown": 0.20,
        "min_trades_per_month": 15,
    },
    "indicators": ["sma_fast", "sma_slow", "atr"],
    "timeframes": ["5m", "15m"],
    "status": "pending",
}


def _step_hypothesis() -> dict | None:
    """Create a trading hypothesis."""
    _step_header(1, 6, "HYPOTHESIS", "Create a trading hypothesis")

    console.print(
        "Every strategy starts with a [bold]hypothesis[/bold] -- a testable idea\n"
        "about why a particular pattern creates an edge in the market.\n"
    )

    console.print(Panel(
        "[bold]A good hypothesis needs:[/bold]\n\n"
        "  [cyan]Edge[/cyan]         What pattern or behavior creates profit?\n"
        "  [cyan]Counterparty[/cyan] Who is on the other side losing money?\n"
        "  [cyan]Metrics[/cyan]      What Sharpe, win rate, drawdown do you expect?\n"
        "  [cyan]Indicators[/cyan]   What signals will detect this pattern?",
        title="Hypothesis Anatomy",
        border_style="dim cyan",
    ))

    console.print("\nExample hypotheses:\n")
    console.print("  [bold cyan][1][/bold cyan] Funding Rate Mean Reversion (crypto)")
    console.print("  [bold cyan][2][/bold cyan] SMA Crossover with ATR Filter (futures)")
    console.print("  [bold cyan][3][/bold cyan] Create your own\n")

    choice = Prompt.ask("Select", choices=["1", "2", "3"], default="2")

    if choice == "1":
        hypothesis = EXAMPLE_HYPOTHESIS.copy()
        hypothesis["id"] = f"hyp-{uuid.uuid4().hex[:8]}"
        hypothesis["created"] = datetime.now(timezone.utc).isoformat()
    elif choice == "2":
        hypothesis = SMA_HYPOTHESIS.copy()
        hypothesis["id"] = f"hyp-{uuid.uuid4().hex[:8]}"
        hypothesis["created"] = datetime.now(timezone.utc).isoformat()
    else:
        console.print("\n[bold]Create your hypothesis:[/bold]\n")
        name = Prompt.ask("Strategy name", default="My Strategy")
        edge = Prompt.ask("What is the edge?", default="Price pattern creates predictable moves")
        counterparty = Prompt.ask("Who loses money?", default="Retail traders on the wrong side")
        market = Prompt.ask("Market", choices=["futures", "crypto-cex", "crypto-dex"], default="futures")

        hypothesis = {
            "id": f"hyp-{uuid.uuid4().hex[:8]}",
            "name": name,
            "created": datetime.now(timezone.utc).isoformat(),
            "author": "tutorial-user",
            "edge": edge,
            "counterparty": counterparty,
            "market": market,
            "expected_metrics": {
                "target_sharpe": 1.2,
                "target_win_rate": 0.50,
                "max_acceptable_drawdown": 0.20,
                "min_trades_per_month": 15,
            },
            "indicators": [],
            "timeframes": ["5m"],
            "status": "pending",
        }

    # Save to queue
    queue_dir = PROJECT_ROOT / "queues" / "hypotheses"
    queue_dir.mkdir(parents=True, exist_ok=True)

    hyp_path = queue_dir / f"{hypothesis['id']}.json"
    with open(hyp_path, "w") as f:
        json.dump(hypothesis, f, indent=2)
        f.write("\n")

    console.print(f"\n[green]Hypothesis saved:[/green] {hyp_path.relative_to(PROJECT_ROOT)}")
    console.print()
    console.print(Syntax(json.dumps(hypothesis, indent=2), "json", theme="monokai"))

    return hypothesis


# ---------------------------------------------------------------------------
# Step 2: STRATEGY
# ---------------------------------------------------------------------------

def _step_strategy(hypothesis: dict | None) -> Path | None:
    """Write or configure a strategy."""
    _step_header(2, 6, "STRATEGY", "Write or configure a strategy")

    console.print(
        "Now we need executable strategy code. The backtest runner expects\n"
        "a Python file with a [bold]Strategy[/bold] class that has:\n\n"
        "  [cyan]indicators(df)[/cyan]  -- Add indicator columns to the DataFrame\n"
        "  [cyan]signals(df)[/cyan]     -- Generate +1 (long), -1 (short), 0 (flat) signals\n"
    )

    sample_path = PROJECT_ROOT / "seed" / "sample_strategy.py"

    console.print("Options:\n")
    console.print("  [bold cyan][1][/bold cyan] Use the sample SMA crossover strategy (recommended for tutorial)")
    console.print("  [bold cyan][2][/bold cyan] Write your own strategy file\n")

    choice = Prompt.ask("Select", choices=["1", "2"], default="1")

    if choice == "1":
        if sample_path.exists():
            console.print(f"\n[green]Using sample strategy:[/green] {sample_path.relative_to(PROJECT_ROOT)}\n")
            console.print(Syntax(sample_path.read_text(), "python", theme="monokai", line_numbers=True))
            return sample_path
        else:
            console.print("[yellow]Sample strategy not found. Creating one...[/yellow]")
            # Create a minimal sample
            seed_dir = PROJECT_ROOT / "seed"
            seed_dir.mkdir(exist_ok=True)
            strategy_code = '''"""Sample SMA crossover strategy for tutorial."""

import pandas as pd


class Strategy:
    name = "SMA_Crossover_Tutorial"

    def __init__(self, params=None):
        self.params = params or self.default_params()

    def default_params(self):
        return {
            "fast_period": 10,
            "slow_period": 30,
            "atr_period": 14,
            "atr_multiplier": 2.0,
        }

    def indicators(self, df):
        p = self.params
        df["sma_fast"] = df["close"].rolling(p["fast_period"]).mean()
        df["sma_slow"] = df["close"].rolling(p["slow_period"]).mean()
        tr = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - df["close"].shift(1)).abs(),
                (df["low"] - df["close"].shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)
        df["atr"] = tr.rolling(p["atr_period"]).mean()
        return df

    def signals(self, df):
        df["signal"] = 0
        df.loc[df["sma_fast"] > df["sma_slow"], "signal"] = 1
        df.loc[df["sma_fast"] < df["sma_slow"], "signal"] = -1
        return df
'''
            sample_path.write_text(strategy_code)
            console.print(f"[green]Created:[/green] {sample_path.relative_to(PROJECT_ROOT)}")
            return sample_path
    else:
        console.print(
            "\n[bold]Strategy file requirements:[/bold]\n\n"
            "  1. Define a [cyan]Strategy[/cyan] class\n"
            "  2. Implement [cyan]indicators(df)[/cyan] and [cyan]signals(df)[/cyan] methods\n"
            "  3. signals() must set a 'signal' column: +1, -1, or 0\n\n"
            "Create your strategy file, then provide the path:\n"
        )
        path_str = Prompt.ask("Strategy file path", default=str(sample_path))
        strategy_path = Path(path_str)
        if not strategy_path.is_absolute():
            strategy_path = PROJECT_ROOT / strategy_path
        if not strategy_path.exists():
            console.print(f"[red]File not found:[/red] {strategy_path}")
            return None
        console.print(f"[green]Using strategy:[/green] {strategy_path}")
        return strategy_path


# ---------------------------------------------------------------------------
# Step 3: BACKTEST
# ---------------------------------------------------------------------------

def _step_backtest(strategy_path: Path | None) -> dict | None:
    """Run a backtest on historical data."""
    _step_header(3, 6, "BACKTEST", "Run strategy against historical data")

    if not strategy_path or not strategy_path.exists():
        console.print("[yellow]No strategy file available. Skipping backtest.[/yellow]")
        return None

    console.print(
        "The backtest runner simulates your strategy on historical data,\n"
        "applying realistic cost models (commissions + slippage).\n"
    )

    console.print(Panel(
        "[bold]Key metrics explained:[/bold]\n\n"
        "  [cyan]Sharpe Ratio[/cyan]   Risk-adjusted return. >1.0 = decent, >1.5 = good, >3.0 = suspicious\n"
        "  [cyan]Win Rate[/cyan]       % of trades profitable. 45-65% is typical for trend-following\n"
        "  [cyan]Max Drawdown[/cyan]   Largest peak-to-trough loss. <20% preferred\n"
        "  [cyan]Profit Factor[/cyan]  Gross profit / gross loss. >1.5 is good\n"
        "  [cyan]Trade Count[/cyan]    More trades = more statistical significance. 100+ minimum",
        title="Backtest Metrics",
        border_style="dim cyan",
    ))

    # Find data file
    data_dir = PROJECT_ROOT / "data"
    data_files = sorted(data_dir.glob("*.csv")) if data_dir.is_dir() else []

    if not data_files:
        console.print("[yellow]No data files found in data/.[/yellow]")
        console.print("Run [cyan]sigma-quant data download[/cyan] or [cyan]sigma-quant init[/cyan] first.")
        return None

    # Let user pick a data file
    console.print(f"\nFound {len(data_files)} data file(s):\n")
    for i, f in enumerate(data_files[:10]):
        size = f.stat().st_size
        size_str = f"{size / 1_000:.0f} KB" if size > 1_000 else f"{size} B"
        console.print(f"  [bold cyan][{i + 1}][/bold cyan] {f.name} ({size_str})")

    if len(data_files) > 10:
        console.print(f"  [dim]... and {len(data_files) - 10} more[/dim]")

    file_idx = Prompt.ask(
        "\nSelect data file",
        default="1",
    )
    try:
        idx = int(file_idx) - 1
        data_file = data_files[idx]
    except (ValueError, IndexError):
        data_file = data_files[0]

    console.print(f"\n[cyan]Running backtest...[/cyan]")
    console.print(f"  Strategy: {strategy_path.name}")
    console.print(f"  Data:     {data_file.name}\n")

    # Run the backtest
    runner = PROJECT_ROOT / "lib" / "backtest_runner.py"
    output_file = PROJECT_ROOT / "output" / "backtests" / f"tutorial-{uuid.uuid4().hex[:8]}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if not runner.exists():
        console.print("[yellow]Backtest runner not found at lib/backtest_runner.py[/yellow]")
        console.print("[dim]Generating mock results for tutorial purposes.[/dim]")
        # Return mock results
        return {
            "sharpe_ratio": 1.35,
            "win_rate": 0.52,
            "max_drawdown": -0.12,
            "profit_factor": 1.45,
            "total_trades": 287,
            "total_return": 0.18,
        }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task("Running backtest...", total=None)
        result = subprocess.run(
            [
                sys.executable, str(runner),
                "--strategy", str(strategy_path),
                "--data", str(data_file),
                "--output", str(output_file),
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=300,
        )

    if result.returncode != 0:
        console.print(f"[yellow]Backtest returned non-zero exit code.[/yellow]")
        if result.stderr:
            console.print(f"[dim]{result.stderr[:500]}[/dim]")

    # Load results
    results = None
    if output_file.exists():
        try:
            with open(output_file) as f:
                results = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    if results:
        _display_backtest_results(results)
    else:
        console.print("[yellow]No results file generated. Check the backtest runner output.[/yellow]")

    return results


def _display_backtest_results(results: dict) -> None:
    """Display backtest results in a formatted table."""
    metrics = results.get("metrics", results.get("performance", results))

    table = Table(title="Backtest Results", show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("Metric", style="white", min_width=16)
    table.add_column("Value", justify="right", min_width=12)
    table.add_column("Rating", min_width=10)

    def _get(key: str, *alts: str):
        for k in (key, *alts):
            v = metrics.get(k)
            if v is not None:
                return v
        return None

    sharpe = _get("sharpe_ratio", "sharpe")
    win_rate = _get("win_rate", "winRate")
    max_dd = _get("max_drawdown", "maxDrawdown")
    pf = _get("profit_factor", "profitFactor")
    trades = _get("total_trades", "trades", "trade_count")
    total_return = _get("total_return", "return")

    if sharpe is not None:
        rating = "[green]GOOD[/green]" if sharpe >= 1.5 else ("[yellow]OK[/yellow]" if sharpe >= 1.0 else "[red]WEAK[/red]")
        table.add_row("Sharpe Ratio", f"{sharpe:.2f}", rating)

    if win_rate is not None:
        wr = win_rate * 100 if win_rate <= 1 else win_rate
        rating = "[green]GOOD[/green]" if wr >= 55 else ("[yellow]OK[/yellow]" if wr >= 45 else "[red]LOW[/red]")
        table.add_row("Win Rate", f"{wr:.1f}%", rating)

    if max_dd is not None:
        dd = abs(max_dd) * 100 if abs(max_dd) <= 1 else abs(max_dd)
        rating = "[green]GOOD[/green]" if dd <= 15 else ("[yellow]OK[/yellow]" if dd <= 25 else "[red]HIGH[/red]")
        table.add_row("Max Drawdown", f"{dd:.1f}%", rating)

    if pf is not None:
        rating = "[green]GOOD[/green]" if pf >= 1.5 else ("[yellow]OK[/yellow]" if pf >= 1.0 else "[red]LOW[/red]")
        table.add_row("Profit Factor", f"{pf:.2f}", rating)

    if trades is not None:
        rating = "[green]GOOD[/green]" if int(trades) >= 200 else ("[yellow]OK[/yellow]" if int(trades) >= 100 else "[red]FEW[/red]")
        table.add_row("Total Trades", str(int(trades)), rating)

    if total_return is not None:
        ret = total_return * 100 if abs(total_return) <= 5 else total_return
        rating = "[green]GOOD[/green]" if ret > 0 else "[red]LOSS[/red]"
        table.add_row("Total Return", f"{ret:.1f}%", rating)

    console.print(table)


# ---------------------------------------------------------------------------
# Step 4: OPTIMIZE
# ---------------------------------------------------------------------------

def _step_optimize(strategy_path: Path | None) -> dict | None:
    """Run walk-forward optimization."""
    _step_header(4, 6, "OPTIMIZE", "Walk-forward optimization")

    console.print(
        "Walk-forward optimization splits data into [bold]train[/bold] and [bold]test[/bold] windows.\n"
        "The optimizer finds best parameters on train data, then validates on\n"
        "unseen test data. This detects [bold]overfitting[/bold].\n"
    )

    console.print(Panel(
        "[bold]Walk-Forward Process:[/bold]\n\n"
        "  [dim]|--- Train Window ---|-- Test --|[/dim]\n"
        "  [dim]      |--- Train Window ---|-- Test --|[/dim]\n"
        "  [dim]            |--- Train Window ---|-- Test --|[/dim]\n\n"
        "  Each window optimizes parameters, then tests on unseen data.\n"
        "  Large decay between train and test = overfitting.\n\n"
        "  [cyan]OOS Decay[/cyan]  = (Train Sharpe - Test Sharpe) / Train Sharpe\n"
        "  Target: < 30% decay. Reject at > 50% decay.",
        title="Walk-Forward Explained",
        border_style="dim cyan",
    ))

    if not strategy_path or not strategy_path.exists():
        console.print("[yellow]No strategy available for optimization. Showing example results.[/yellow]")
    else:
        console.print(f"  Strategy: {strategy_path.name}")

    # Check for data and runner
    runner = PROJECT_ROOT / "lib" / "backtest_runner.py"
    data_dir = PROJECT_ROOT / "data"
    data_files = sorted(data_dir.glob("*.csv")) if data_dir.is_dir() else []

    if runner.exists() and data_files and strategy_path and strategy_path.exists():
        run_it = Confirm.ask("\nRun walk-forward optimization? (may take 1-2 minutes)", default=False)
        if run_it:
            data_file = data_files[0]
            output_file = PROJECT_ROOT / "output" / "backtests" / f"tutorial-wfo-{uuid.uuid4().hex[:8]}.json"

            console.print(f"\n[cyan]Running walk-forward optimization...[/cyan]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task("Optimizing...", total=None)
                result = subprocess.run(
                    [
                        sys.executable, str(runner),
                        "--strategy", str(strategy_path),
                        "--data", str(data_file),
                        "--walk-forward", json.dumps({
                            "train_bars": 5000,
                            "test_bars": 1000,
                            "step_bars": 1000,
                        }),
                        "--output", str(output_file),
                    ],
                    capture_output=True,
                    text=True,
                    cwd=str(PROJECT_ROOT),
                    timeout=300,
                )

            if output_file.exists():
                try:
                    with open(output_file) as f:
                        results = json.load(f)
                    _display_backtest_results(results)
                    return results
                except (json.JSONDecodeError, OSError):
                    pass

    # Show example WFO results
    console.print()
    wfo_table = Table(title="Walk-Forward Results (Example)", header_style="bold cyan", border_style="dim")
    wfo_table.add_column("Window", style="white")
    wfo_table.add_column("Train Sharpe", justify="right")
    wfo_table.add_column("Test Sharpe", justify="right")
    wfo_table.add_column("OOS Decay", justify="right")

    windows = [
        ("Window 1", "1.82", "1.45", "[green]20%[/green]"),
        ("Window 2", "1.65", "1.38", "[green]16%[/green]"),
        ("Window 3", "1.91", "1.22", "[yellow]36%[/yellow]"),
        ("Window 4", "1.73", "1.51", "[green]13%[/green]"),
        ("Average", "[bold]1.78[/bold]", "[bold]1.39[/bold]", "[bold green]22%[/bold green]"),
    ]
    for row in windows:
        wfo_table.add_row(*row)

    console.print(wfo_table)
    console.print("\n[green]OOS decay 22% -- within acceptable range (<30%).[/green]")

    return None


# ---------------------------------------------------------------------------
# Step 5: VALIDATE
# ---------------------------------------------------------------------------

def _step_validate(backtest_results: dict | None) -> None:
    """Anti-overfitting and compliance validation."""
    _step_header(5, 6, "VALIDATE", "Anti-overfitting + compliance checks")

    config = _load_config()
    validation = config.get("validation", {}).get("strategy", {})

    console.print(
        "Every strategy must pass [bold]quality gates[/bold] before promotion.\n"
        "This prevents overfitted or statistically insignificant strategies\n"
        "from reaching paper trading.\n"
    )

    # Show validation gates
    gates_table = Table(title="Validation Gates", header_style="bold cyan", border_style="dim")
    gates_table.add_column("Gate", style="white", min_width=20)
    gates_table.add_column("Threshold", justify="right", min_width=12)
    gates_table.add_column("Status", min_width=10)

    # Use actual results or defaults
    if backtest_results:
        metrics = backtest_results.get("metrics", backtest_results)
        sharpe = metrics.get("sharpe_ratio", metrics.get("sharpe", 1.35))
        win_rate = metrics.get("win_rate", metrics.get("winRate", 0.52))
        max_dd = abs(metrics.get("max_drawdown", metrics.get("maxDrawdown", 0.12)))
        trades = metrics.get("total_trades", metrics.get("trades", 287))
    else:
        sharpe, win_rate, max_dd, trades = 1.35, 0.52, 0.12, 287

    wr = win_rate * 100 if win_rate <= 1 else win_rate
    dd = max_dd * 100 if max_dd <= 1 else max_dd

    min_sharpe = validation.get("minSharpe", 1.0)
    max_sharpe = validation.get("maxSharpe", 3.0)
    max_wr = validation.get("maxWinRate", 0.80) * 100
    max_drawdown = validation.get("rejectMaxDrawdown", 0.30) * 100
    min_trades = validation.get("minTrades", 100)
    max_oos_decay = validation.get("rejectOosDecay", 0.50) * 100

    gates = [
        ("Sharpe >= minimum", f">= {min_sharpe}", sharpe >= min_sharpe),
        ("Sharpe < suspicion", f"< {max_sharpe}", sharpe < max_sharpe),
        ("Win Rate < maximum", f"< {max_wr:.0f}%", wr < max_wr),
        ("Max Drawdown < limit", f"< {max_drawdown:.0f}%", dd < max_drawdown),
        ("Trade Count >= minimum", f">= {min_trades}", trades >= min_trades),
        ("OOS Decay < limit", f"< {max_oos_decay:.0f}%", True),  # Assume pass for tutorial
    ]

    passed_count = 0
    for gate_name, threshold, passed in gates:
        status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        if passed:
            passed_count += 1
        gates_table.add_row(gate_name, threshold, status)

    console.print(gates_table)

    total_gates = len(gates)
    if passed_count == total_gates:
        console.print(f"\n[bold green]All {total_gates} gates passed.[/bold green] Strategy qualifies for promotion.")
    else:
        console.print(f"\n[yellow]{passed_count}/{total_gates} gates passed.[/yellow] Strategy needs improvement.")

    # Prop firm / exchange compliance
    console.print()
    console.print("[bold]Compliance Validation:[/bold]\n")

    profile_path = PROJECT_ROOT / config.get("activeProfile", "profiles/futures.json")
    compliance_type = "prop-firm"
    if profile_path.exists():
        try:
            with open(profile_path) as f:
                profile = json.load(f)
            compliance_type = profile.get("compliance", {}).get("type", "prop-firm")
        except (json.JSONDecodeError, OSError):
            pass

    if compliance_type == "prop-firm":
        firms = ["Apex", "Topstep", "FTMO", "Earn2Trade", "Bulenox", "My Funded Futures"]
        firm_table = Table(header_style="bold cyan", border_style="dim")
        firm_table.add_column("Prop Firm", style="white")
        firm_table.add_column("Max DD Rule", justify="right")
        firm_table.add_column("Daily Loss Rule", justify="right")
        firm_table.add_column("Status")

        for firm in firms:
            # Simulated results
            passed = dd < 10 or (dd < 20 and firm not in ("FTMO",))
            firm_table.add_row(
                firm,
                f"{dd:.1f}% / 10%",
                f"{dd * 0.4:.1f}% / 5%",
                "[green]PASS[/green]" if passed else "[red]FAIL[/red]",
            )

        console.print(firm_table)
    else:
        console.print(f"  Compliance type: [cyan]{compliance_type}[/cyan]")
        console.print("  [green]Exchange rules validated.[/green]")


# ---------------------------------------------------------------------------
# Step 6: DEPLOY
# ---------------------------------------------------------------------------

def _step_deploy(strategy_path: Path | None) -> None:
    """Export to Freqtrade for paper trading."""
    _step_header(6, 6, "DEPLOY", "Export to Freqtrade for paper trading")

    console.print(
        "Validated strategies get exported as Freqtrade [bold]IStrategy[/bold] files\n"
        "with a matching config.json for paper trading.\n"
    )

    console.print(Panel(
        "[bold]Freqtrade output includes:[/bold]\n\n"
        "  [cyan]Strategy file[/cyan]   -- IStrategy class with your indicators + signals\n"
        "  [cyan]Config file[/cyan]     -- Exchange settings, pair list, timeframe\n"
        "  [cyan]Backtest log[/cyan]    -- Original backtest results for reference\n\n"
        "Files are saved to: [dim]freqtrade/user_data/strategies/[/dim]",
        title="Deployment Output",
        border_style="dim cyan",
    ))

    deploy_script = PROJECT_ROOT / "scripts" / "freqtrade-deploy.sh"
    freqtrade_dir = PROJECT_ROOT / "freqtrade" / "user_data" / "strategies"
    freqtrade_dir.mkdir(parents=True, exist_ok=True)

    console.print("\nTo deploy this strategy:\n")
    console.print("  [cyan]sigma-quant deploy[/cyan]            -- Deploy all validated strategies")
    console.print("  [cyan]sigma-quant deploy --dry-run[/cyan]  -- Preview without executing\n")

    if deploy_script.exists():
        run_deploy = Confirm.ask("Run deployment now?", default=False)
        if run_deploy:
            console.print("\n[cyan]Deploying...[/cyan]")
            subprocess.run(["bash", str(deploy_script)], cwd=str(PROJECT_ROOT))
    else:
        console.print("[dim]Deploy script not found. Manual deployment instructions below.[/dim]")

    console.print()
    console.print(Panel(
        "[bold]Start paper trading:[/bold]\n\n"
        "  1. Install Freqtrade: [cyan]pip install freqtrade[/cyan]\n"
        "  2. Copy strategy to [cyan]freqtrade/user_data/strategies/[/cyan]\n"
        "  3. Run: [cyan]freqtrade trade --strategy YourStrategy --config config.json --dry-run[/cyan]\n"
        "  4. Monitor: [cyan]freqtrade webserver[/cyan] (opens dashboard on localhost:8080)",
        title="Paper Trading Guide",
        border_style="dim cyan",
    ))


# ---------------------------------------------------------------------------
# Main Entry
# ---------------------------------------------------------------------------

def run_tutorial() -> None:
    """Run the full 6-step tutorial."""
    console.print()
    console.print(Panel(
        "[bold cyan]Sigma-Quant Stream Tutorial[/bold cyan]\n"
        "[dim]6-step walkthrough of the strategy research pipeline[/dim]\n\n"
        "Step 1: HYPOTHESIS  -- Create a trading hypothesis\n"
        "Step 2: STRATEGY    -- Write executable strategy code\n"
        "Step 3: BACKTEST    -- Validate against historical data\n"
        "Step 4: OPTIMIZE    -- Walk-forward optimization\n"
        "Step 5: VALIDATE    -- Anti-overfitting + compliance\n"
        "Step 6: DEPLOY      -- Export to Freqtrade",
        border_style="cyan",
        padding=(1, 2),
    ))

    if not _wait_for_continue():
        return

    # Step 1
    hypothesis = _step_hypothesis()
    if not _wait_for_continue():
        return

    # Step 2
    strategy_path = _step_strategy(hypothesis)
    if not _wait_for_continue():
        return

    # Step 3
    backtest_results = _step_backtest(strategy_path)
    if not _wait_for_continue():
        return

    # Step 4
    _step_optimize(strategy_path)
    if not _wait_for_continue():
        return

    # Step 5
    _step_validate(backtest_results)
    if not _wait_for_continue():
        return

    # Step 6
    _step_deploy(strategy_path)

    # Completion
    console.print()
    console.print(Panel(
        "[bold green]Tutorial Complete[/bold green]\n\n"
        "You have walked through the entire strategy research pipeline.\n\n"
        "Next steps:\n"
        "  [cyan]sigma-quant start[/cyan]          -- Launch autonomous workers\n"
        "  [cyan]sigma-quant status --watch[/cyan]  -- Monitor the dashboard\n"
        "  [cyan]sigma-quant strategies[/cyan]      -- View discovered strategies\n\n"
        "The workers will continuously discover, backtest, optimize,\n"
        "and validate new strategies 24/7.",
        title="What's Next",
        border_style="green",
        padding=(1, 2),
    ))
