"""Sigma-Quant Stream -- Interactive onboarding (6 steps).

Usage:
    sigma-quant init             # Standard onboarding
    sigma-quant init --explain   # With educational annotations
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _step_header(step: int, total: int, title: str) -> None:
    """Print a step header."""
    console.print()
    console.print(Panel(
        f"[bold white]STEP {step}/{total}[/bold white]  [cyan]{title}[/cyan]",
        border_style="cyan",
        padding=(0, 2),
    ))
    console.print()


def _explain_panel(text: str, explain: bool) -> None:
    """Show an educational panel if --explain is active."""
    if not explain:
        return
    console.print(Panel(
        text,
        title="[dim]Learn More[/dim]",
        border_style="dim cyan",
        padding=(1, 2),
    ))
    console.print()


def _write_env(env_vars: dict[str, str]) -> None:
    """Write or update .env file with the given variables."""
    env_path = PROJECT_ROOT / ".env"
    existing: dict[str, str] = {}

    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()

    existing.update(env_vars)

    lines = ["# Sigma-Quant Stream Environment Configuration", ""]
    for k, v in sorted(existing.items()):
        lines.append(f"{k}={v}")
    lines.append("")

    env_path.write_text("\n".join(lines))


def _update_config(updates: dict[str, Any]) -> dict:
    """Update config.json with new values. Returns the updated config."""
    cfg_path = PROJECT_ROOT / "config.json"
    config: dict = {}
    if cfg_path.exists():
        with open(cfg_path) as f:
            config = json.load(f)

    def _deep_merge(base: dict, overlay: dict) -> dict:
        for k, v in overlay.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                _deep_merge(base[k], v)
            else:
                base[k] = v
        return base

    config = _deep_merge(config, updates)

    with open(cfg_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    return config


def _ensure_directories() -> None:
    """Ensure all required directories exist."""
    dirs = [
        "queues/hypotheses",
        "queues/to-convert",
        "queues/to-backtest",
        "queues/to-optimize",
        "output/strategies/good",
        "output/strategies/under_review",
        "output/strategies/rejected",
        "output/strategies/prop_firm_ready",
        "output/backtests",
        "output/research-logs",
        "output/indicators/converted",
        "output/indicators/created",
        "output/combinations",
        "data",
        "session-summaries",
        "checkpoints",
    ]
    for d in dirs:
        (PROJECT_ROOT / d).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Step 1: Welcome
# ---------------------------------------------------------------------------

def _step_welcome(explain: bool) -> str:
    """Choose path: Developer or Trader. Returns 'developer' or 'trader'."""
    _step_header(1, 6, "WELCOME")

    console.print(
        "[bold]Welcome to Sigma-Quant Stream[/bold] -- the autonomous strategy research factory.\n"
    )

    _explain_panel(
        "Sigma-Quant Stream discovers and validates trading strategies using\n"
        "Claude Code agent swarms. It runs 4 specialized workers in parallel:\n\n"
        "  [cyan]Researcher[/cyan]   - Discovers new trading ideas from research\n"
        "  [cyan]Converter[/cyan]    - Converts ideas into executable strategies\n"
        "  [cyan]Backtester[/cyan]   - Validates strategies against historical data\n"
        "  [cyan]Optimizer[/cyan]    - Walk-forward optimization + anti-overfitting\n\n"
        "Strategies that pass all gates get exported to Freqtrade for paper trading.",
        explain,
    )

    console.print("Choose your path:\n")
    console.print("  [bold cyan][1][/bold cyan] Developer  -- I want to write strategy code and customize the pipeline")
    console.print("  [bold cyan][2][/bold cyan] Trader     -- I want to configure strategies from templates\n")

    choice = Prompt.ask(
        "Select path",
        choices=["1", "2"],
        default="2",
    )

    path = "developer" if choice == "1" else "trader"
    console.print(f"\n[green]Selected:[/green] {path.title()} path")
    return path


# ---------------------------------------------------------------------------
# Step 2: Market Selection
# ---------------------------------------------------------------------------

def _step_market_selection(explain: bool) -> list[str]:
    """Choose markets. Returns list of market profile IDs."""
    _step_header(2, 6, "MARKET SELECTION")

    _explain_panel(
        "Each market has different characteristics:\n\n"
        "  [cyan]Futures[/cyan]     - CME contracts (ES, NQ, YM, GC). Lower fees,\n"
        "                regulated, prop firm compatible. Requires Databento API key.\n\n"
        "  [cyan]Crypto CEX[/cyan]  - Centralized exchange perps (Binance, Bybit).\n"
        "                24/7 trading, funding rates, higher leverage. Free OHLCV data.\n\n"
        "  [cyan]Crypto DEX[/cyan]  - Hyperliquid on-chain CLOB. Fully decentralized,\n"
        "                builder codes, vault flow signals. Free data via API.\n\n"
        "Choosing multiple markets runs separate research pipelines for each.",
        explain,
    )

    console.print("Select markets to research:\n")
    console.print("  [bold cyan][1][/bold cyan] CME Futures (ES, NQ, YM, GC)")
    console.print("  [bold cyan][2][/bold cyan] Crypto CEX (Binance, Bybit, OKX)")
    console.print("  [bold cyan][3][/bold cyan] Crypto DEX (Hyperliquid)")
    console.print("  [bold cyan][4][/bold cyan] All of the above\n")

    choice = Prompt.ask(
        "Select markets",
        choices=["1", "2", "3", "4"],
        default="1",
    )

    market_map = {
        "1": ["futures"],
        "2": ["crypto-cex"],
        "3": ["crypto-dex-hyperliquid"],
        "4": ["futures", "crypto-cex", "crypto-dex-hyperliquid"],
    }

    selected = market_map[choice]
    names = [m.replace("-", " ").title() for m in selected]
    console.print(f"\n[green]Selected:[/green] {', '.join(names)}")
    return selected


# ---------------------------------------------------------------------------
# Step 3: API Keys
# ---------------------------------------------------------------------------

def _step_api_keys(markets: list[str], explain: bool) -> dict[str, str]:
    """Prompt for API keys based on market selection. Returns env vars dict."""
    _step_header(3, 6, "API KEYS")

    _explain_panel(
        "API keys are stored in your local .env file and never committed to git.\n\n"
        "  [cyan]Databento[/cyan]  - Required for futures. Get a key at https://databento.com\n"
        "                Sample data is available without a key for testing.\n\n"
        "  [cyan]Exchange keys[/cyan] - Optional for crypto. CCXT can fetch free OHLCV\n"
        "                data without authentication for most exchanges.\n\n"
        "  [cyan]Hyperliquid[/cyan] - Optional. Public API works without auth.\n"
        "                Wallet address needed only for live trading.",
        explain,
    )

    env_vars: dict[str, str] = {}

    if "futures" in markets:
        console.print("[bold]Futures Data (Databento)[/bold]\n")
        api_key = Prompt.ask(
            "Databento API key (press Enter to skip for sample data)",
            default="",
        )
        if api_key:
            env_vars["DATABENTO_API_KEY"] = api_key
            console.print("[green]Databento API key saved.[/green]")
        else:
            console.print("[yellow]Skipped -- will use sample data for backtesting.[/yellow]")
        console.print()

    if "crypto-cex" in markets:
        console.print("[bold]Crypto CEX (Exchange Keys)[/bold]\n")
        console.print("[dim]Optional -- free OHLCV data available without keys.[/dim]")
        add_keys = Confirm.ask("Add exchange API keys?", default=False)
        if add_keys:
            exchange = Prompt.ask(
                "Exchange",
                choices=["binance", "bybit", "okx"],
                default="binance",
            )
            api_key = Prompt.ask(f"{exchange.title()} API key", default="")
            secret = Prompt.ask(f"{exchange.title()} secret", default="")
            if api_key:
                env_vars[f"{exchange.upper()}_API_KEY"] = api_key
            if secret:
                env_vars[f"{exchange.upper()}_SECRET"] = secret
            if api_key:
                console.print(f"[green]{exchange.title()} keys saved.[/green]")
        else:
            console.print("[yellow]Skipped -- using public OHLCV data.[/yellow]")
        console.print()

    if "crypto-dex-hyperliquid" in markets:
        console.print("[bold]Crypto DEX (Hyperliquid)[/bold]\n")
        console.print("[dim]Optional -- public API works without authentication.[/dim]")
        wallet = Prompt.ask(
            "Hyperliquid wallet address (press Enter to skip)",
            default="",
        )
        if wallet:
            env_vars["HYPERLIQUID_WALLET"] = wallet
            console.print("[green]Hyperliquid wallet saved.[/green]")
        else:
            console.print("[yellow]Skipped -- using public API.[/yellow]")
        console.print()

    if env_vars:
        _write_env(env_vars)
        console.print(f"[green]Saved {len(env_vars)} key(s) to .env[/green]")
    else:
        console.print("[dim]No API keys configured. You can add them later in .env[/dim]")

    return env_vars


# ---------------------------------------------------------------------------
# Step 4: Data Download
# ---------------------------------------------------------------------------

def _step_data_download(markets: list[str], env_vars: dict[str, str], explain: bool) -> None:
    """Download historical data for selected markets."""
    _step_header(4, 6, "DATA DOWNLOAD")

    _explain_panel(
        "Historical data is needed for backtesting strategies.\n\n"
        "  [cyan]Futures[/cyan]  - Databento provides tick-level data. We download\n"
        "             5-minute OHLCV bars for backtesting (costs ~$0.01/symbol/day).\n"
        "             Sample data included for free testing.\n\n"
        "  [cyan]Crypto[/cyan]  - CCXT fetches free OHLCV from exchanges.\n"
        "             No API key needed for historical candle data.\n\n"
        "  Data is stored in the data/ directory as CSV files.",
        explain,
    )

    download_script = PROJECT_ROOT / "scripts" / "download-data.py"
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(exist_ok=True)

    # Check if sample data already exists
    existing_files = list(data_dir.glob("*.csv")) if data_dir.is_dir() else []
    if existing_files:
        console.print(f"[dim]Found {len(existing_files)} existing data file(s) in data/[/dim]")
        skip = Confirm.ask("Skip data download?", default=True)
        if skip:
            console.print("[green]Using existing data.[/green]")
            return

    if not download_script.exists():
        console.print("[yellow]Download script not found. Skipping data download.[/yellow]")
        console.print(f"[dim]Expected at: {download_script}[/dim]")
        console.print("You can download data later with: [cyan]sigma-quant data download[/cyan]")
        return

    symbols_to_download: list[tuple[str, str, str]] = []  # (provider, symbol, exchange)

    for market in markets:
        profile_path = PROJECT_ROOT / "profiles" / f"{market}.json"
        if not profile_path.exists():
            continue

        with open(profile_path) as f:
            profile = json.load(f)

        adapter = profile.get("dataProvider", {}).get("adapter", "ccxt")
        exchange = profile.get("dataProvider", {}).get("exchange", "binance")
        pinned = profile.get("symbols", {}).get("pinned", [])

        for sym in pinned[:4]:  # Limit to 4 symbols per market for initial download
            symbols_to_download.append((adapter, sym, exchange))

    if not symbols_to_download:
        console.print("[yellow]No symbols configured for download.[/yellow]")
        return

    console.print(f"Downloading {len(symbols_to_download)} symbol(s)...\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        task = progress.add_task("Downloading...", total=len(symbols_to_download))

        for adapter, sym, exchange in symbols_to_download:
            progress.update(task, description=f"Downloading {sym} ({adapter})...")

            cmd = [
                sys.executable, str(download_script),
                "--provider", adapter,
                "--symbol", sym,
                "--timeframe", "5m",
                "--bars", "5000",
            ]
            if adapter in ("ccxt", "hyperliquid"):
                cmd += ["--exchange", exchange]

            env = os.environ.copy()
            for k, v in env_vars.items():
                env[k] = v

            try:
                subprocess.run(
                    cmd,
                    cwd=str(PROJECT_ROOT),
                    env=env,
                    capture_output=True,
                    timeout=120,
                )
            except subprocess.TimeoutExpired:
                console.print(f"[yellow]Timeout downloading {sym}. Skipping.[/yellow]")

            progress.advance(task)

    # Check results
    new_files = list(data_dir.glob("*.csv"))
    console.print(f"\n[green]Data download complete. {len(new_files)} file(s) in data/[/green]")


# ---------------------------------------------------------------------------
# Step 5: Configuration
# ---------------------------------------------------------------------------

def _step_configuration(
    path: str,
    markets: list[str],
    explain: bool,
) -> None:
    """Auto-generate config.json based on selections."""
    _step_header(5, 6, "CONFIGURATION")

    _explain_panel(
        "config.json is the central configuration file that controls:\n\n"
        "  [cyan]Active profile[/cyan]   - Which market to research\n"
        "  [cyan]Workers[/cyan]          - How many parallel agents to run\n"
        "  [cyan]Validation gates[/cyan] - Minimum Sharpe, max drawdown, min trades\n"
        "  [cyan]Cost model[/cyan]       - Commission and slippage assumptions\n"
        "  [cyan]Budget cap[/cyan]       - Maximum Claude API spend per session\n\n"
        "You can always change these later with [cyan]sigma-quant config set[/cyan].",
        explain,
    )

    # Set active profile to first selected market
    active_profile = f"profiles/{markets[0]}.json"

    # Ask about mode
    console.print("Select research mode:\n")
    console.print("  [bold cyan][1][/bold cyan] Research   -- Conservative budget ($50), sample data OK")
    console.print("  [bold cyan][2][/bold cyan] Production -- Higher budget ($100), live data preferred\n")

    mode_choice = Prompt.ask("Select mode", choices=["1", "2"], default="1")
    mode = "research" if mode_choice == "1" else "production"

    # Ask about worker count
    pane_count = IntPrompt.ask(
        "Number of parallel workers",
        default=4,
    )
    pane_count = max(1, min(pane_count, 8))

    updates = {
        "activeProfile": active_profile,
        "defaults": {
            "panes": pane_count,
            "mode": mode,
        },
    }

    config = _update_config(updates)
    _ensure_directories()

    console.print(f"\n[green]Configuration saved.[/green]")
    console.print(f"  Active profile: [cyan]{active_profile}[/cyan]")
    console.print(f"  Mode:           [cyan]{mode}[/cyan]")
    console.print(f"  Workers:        [cyan]{pane_count}[/cyan]")


# ---------------------------------------------------------------------------
# Step 6: Health Check
# ---------------------------------------------------------------------------

def _step_health_check(explain: bool) -> None:
    """Run health check to verify setup."""
    _step_header(6, 6, "HEALTH CHECK")

    _explain_panel(
        "The health check verifies:\n\n"
        "  [cyan]Python version[/cyan]  - 3.11+ required for modern features\n"
        "  [cyan]Dependencies[/cyan]    - pandas, pandas_ta, ccxt, typer, rich\n"
        "  [cyan]CLI tools[/cyan]       - Claude Code CLI, tmux\n"
        "  [cyan]Configuration[/cyan]   - .env file, config.json, queue directories\n\n"
        "Any failures shown in red should be fixed before running workers.",
        explain,
    )

    from cli.health import run_health_check
    failures = run_health_check()

    console.print()
    if failures == 0:
        console.print(Panel(
            "[bold green]All checks passed.[/bold green]\n\n"
            "You are ready to start discovering strategies.\n\n"
            "Next steps:\n"
            "  [cyan]sigma-quant tutorial[/cyan]  -- Learn the pipeline step by step\n"
            "  [cyan]sigma-quant start[/cyan]     -- Launch all workers\n"
            "  [cyan]sigma-quant status[/cyan]    -- View the dashboard",
            title="Setup Complete",
            border_style="green",
        ))
    else:
        console.print(Panel(
            f"[bold yellow]{failures} check(s) failed.[/bold yellow]\n\n"
            "Fix the issues above, then run:\n"
            "  [cyan]sigma-quant health[/cyan]  -- Re-run health check\n\n"
            "You can still use most features. Failed checks are informational\n"
            "and may not block your chosen workflow.",
            title="Setup Complete (with warnings)",
            border_style="yellow",
        ))


# ---------------------------------------------------------------------------
# Main Entry
# ---------------------------------------------------------------------------

def run_onboarding(explain: bool = False) -> None:
    """Run the full 6-step onboarding flow."""
    console.print()
    console.print(Panel(
        "[bold cyan]Sigma-Quant Stream[/bold cyan]\n"
        "[dim]Autonomous Strategy Research Factory[/dim]\n\n"
        "This wizard will set up your research environment in 6 steps.",
        border_style="cyan",
        padding=(1, 2),
    ))

    if explain:
        console.print("[dim]Running in --explain mode: educational annotations enabled.[/dim]")

    # Step 1: Welcome / path selection
    path = _step_welcome(explain)

    # Step 2: Market selection
    markets = _step_market_selection(explain)

    # Step 3: API keys
    env_vars = _step_api_keys(markets, explain)

    # Step 4: Data download
    _step_data_download(markets, env_vars, explain)

    # Step 5: Configuration
    _step_configuration(path, markets, explain)

    # Step 6: Health check
    _step_health_check(explain)
