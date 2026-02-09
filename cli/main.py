"""Sigma-Quant Stream — Autonomous Strategy Research Factory CLI."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

app = typer.Typer(
    name="sigma-quant",
    help="[bold cyan]Sigma-Quant Stream[/bold cyan] -- Autonomous Strategy Research Factory",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

data_app = typer.Typer(
    name="data",
    help="[bold]Data management[/bold] -- download and inspect market data.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

config_app = typer.Typer(
    name="config",
    help="[bold]Configuration[/bold] -- view and manage settings.",
    rich_markup_mode="rich",
    invoke_without_command=True,
)

app.add_typer(data_app, name="data")
app.add_typer(config_app, name="config")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    """Load config.json from project root."""
    cfg_path = PROJECT_ROOT / "config.json"
    if not cfg_path.exists():
        console.print("[red]config.json not found at project root.[/red]")
        raise typer.Exit(code=1)
    with open(cfg_path) as f:
        return json.load(f)


def _load_active_profile() -> dict:
    """Load the active market profile."""
    config = _load_config()
    profile_path = PROJECT_ROOT / config.get("activeProfile", "profiles/futures.json")
    if not profile_path.exists():
        console.print(f"[red]Active profile not found:[/red] {profile_path}")
        raise typer.Exit(code=1)
    with open(profile_path) as f:
        return json.load(f)


def _tmux_session_exists(session_name: str) -> bool:
    """Check if a tmux session exists."""
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------
@app.command()
def init(
    explain: bool = typer.Option(False, "--explain", help="Show educational annotations during setup."),
) -> None:
    """[green]Interactive onboarding[/green] -- set up your research environment."""
    from cli.onboarding import run_onboarding
    run_onboarding(explain=explain)


# ---------------------------------------------------------------------------
# setup-claude
# ---------------------------------------------------------------------------
@app.command("setup-claude")
def setup_claude() -> None:
    """[green]Configure Claude Code[/green] for agent teams."""
    from cli.setup_claude import run_setup_claude
    run_setup_claude()


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------
@app.command()
def health() -> None:
    """[green]System health check[/green] -- verify all dependencies and configuration."""
    from cli.health import run_health_check
    failures = run_health_check()
    raise typer.Exit(code=1 if failures > 0 else 0)


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------
VALID_WORKERS = ["researcher", "converter", "backtester", "optimizer"]
TMUX_SESSION = "sigma-quant"


@app.command()
def start(
    worker: Optional[str] = typer.Argument(
        None,
        help="Specific worker to start (researcher, converter, backtester, optimizer). Omit for all.",
    ),
) -> None:
    """[green]Launch workers[/green] -- start the Ralph loop in tmux."""
    # 1. Check tmux
    if not shutil.which("tmux"):
        console.print(Panel(
            "[red bold]tmux is not installed.[/red bold]\n\n"
            "Install with:\n"
            "  [cyan]brew install tmux[/cyan]   (macOS)\n"
            "  [cyan]sudo apt install tmux[/cyan] (Linux)",
            title="Missing Dependency",
            border_style="red",
        ))
        raise typer.Exit(code=1)

    config = _load_config()
    worker_types = config.get("workers", {}).get("types", VALID_WORKERS)

    if worker:
        # Start a single worker
        if worker not in worker_types:
            console.print(f"[red]Unknown worker:[/red] {worker}")
            console.print(f"Valid workers: {', '.join(worker_types)}")
            raise typer.Exit(code=1)

        _start_single_worker(worker, config)
    else:
        # Start all workers in tmux session
        _start_all_workers(worker_types, config)


def _start_single_worker(worker: str, config: dict) -> None:
    """Start a single worker in its own tmux session."""
    session_name = f"quant-{worker}"

    if _tmux_session_exists(session_name):
        console.print(f"[yellow]Session '{session_name}' already running.[/yellow]")
        console.print(f"Attach with: [cyan]tmux attach -t {session_name}[/cyan]")
        return

    prompt_path = PROJECT_ROOT / config.get("workers", {}).get("prompts", {}).get(
        worker, f"prompts/{worker}.md"
    )

    ralph_script = PROJECT_ROOT / "scripts" / "quant-ralph.sh"

    if ralph_script.exists() and prompt_path.exists():
        subprocess.run([
            "tmux", "new-session", "-d", "-s", session_name, "-n", worker,
            "bash", str(ralph_script), worker,
        ], cwd=str(PROJECT_ROOT))
    else:
        subprocess.run([
            "tmux", "new-session", "-d", "-s", session_name, "-n", worker,
        ])

    console.print(f"[green]Started worker:[/green] {worker}")
    console.print(f"Attach with: [cyan]tmux attach -t {session_name}[/cyan]")


def _start_all_workers(worker_types: list[str], config: dict) -> None:
    """Start all workers in a single tmux session with multiple panes."""
    # Check for existing launcher script first
    launcher = PROJECT_ROOT / "scripts" / "tmux-quant-launcher.sh"

    if _tmux_session_exists(TMUX_SESSION):
        console.print(f"[yellow]Session '{TMUX_SESSION}' already running.[/yellow]")
        console.print(f"Attach with: [cyan]tmux attach -t {TMUX_SESSION}[/cyan]")
        console.print(f"Stop with:   [cyan]sigma-quant stop[/cyan]")
        return

    if launcher.exists():
        console.print("[cyan]Launching all workers via tmux-quant-launcher.sh...[/cyan]")
        subprocess.run(["bash", str(launcher)], cwd=str(PROJECT_ROOT))
    else:
        # Manual tmux session creation
        console.print("[cyan]Creating tmux session with 5 panes...[/cyan]")

        ralph_script = PROJECT_ROOT / "scripts" / "quant-ralph.sh"
        has_ralph = ralph_script.exists()

        # Create session with first worker
        first_worker = worker_types[0]
        if has_ralph:
            subprocess.run([
                "tmux", "new-session", "-d", "-s", TMUX_SESSION,
                "-n", "workers",
                "bash", str(ralph_script), first_worker,
            ], cwd=str(PROJECT_ROOT))
        else:
            subprocess.run([
                "tmux", "new-session", "-d", "-s", TMUX_SESSION,
                "-n", "workers",
            ], cwd=str(PROJECT_ROOT))

        # Split panes for remaining workers
        for i, worker_name in enumerate(worker_types[1:], 1):
            split_cmd = [
                "tmux", "split-window", "-t", f"{TMUX_SESSION}:workers",
            ]
            if has_ralph:
                split_cmd += ["bash", str(ralph_script), worker_name]
            subprocess.run(split_cmd, cwd=str(PROJECT_ROOT))

        # Pane 5: status dashboard
        subprocess.run([
            "tmux", "split-window", "-t", f"{TMUX_SESSION}:workers",
            sys.executable, "-m", "cli.main", "status", "--watch",
        ], cwd=str(PROJECT_ROOT))

        # Tile all panes evenly
        subprocess.run([
            "tmux", "select-layout", "-t", f"{TMUX_SESSION}:workers", "tiled",
        ])

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task("Waiting for workers to initialize...", total=None)
        time.sleep(2)

    console.print()
    console.print(Panel(
        f"[green bold]All {len(worker_types)} workers launched.[/green bold]\n\n"
        f"Attach:  [cyan]tmux attach -t {TMUX_SESSION}[/cyan]\n"
        f"Status:  [cyan]sigma-quant status --watch[/cyan]\n"
        f"Stop:    [cyan]sigma-quant stop[/cyan]",
        title="Workers Running",
        border_style="green",
    ))


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------
@app.command()
def stop(
    force: bool = typer.Option(False, "--force", "-f", help="Force kill without graceful shutdown."),
) -> None:
    """[red]Graceful shutdown[/red] -- stop all workers."""
    sessions_found = False

    # Check for main session
    if _tmux_session_exists(TMUX_SESSION):
        sessions_found = True
        if force:
            subprocess.run(["tmux", "kill-session", "-t", TMUX_SESSION], capture_output=True)
            console.print(f"[red]Force-killed session:[/red] {TMUX_SESSION}")
        else:
            console.print("[yellow]Sending graceful shutdown to workers...[/yellow]")
            # Send SIGTERM to each pane
            try:
                result = subprocess.run(
                    ["tmux", "list-panes", "-t", TMUX_SESSION, "-F", "#{pane_pid}"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    pids = [p.strip() for p in result.stdout.strip().splitlines() if p.strip()]
                    for pid in pids:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                        except (OSError, ValueError):
                            pass

                    # Wait briefly for graceful shutdown
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        transient=True,
                    ) as progress:
                        progress.add_task("Waiting for graceful shutdown...", total=None)
                        time.sleep(3)
            except (subprocess.SubprocessError, FileNotFoundError):
                pass

            # Kill the session
            subprocess.run(["tmux", "kill-session", "-t", TMUX_SESSION], capture_output=True)
            console.print(f"[green]Stopped session:[/green] {TMUX_SESSION}")

    # Check for individual worker sessions
    for w in VALID_WORKERS:
        session_name = f"quant-{w}"
        if _tmux_session_exists(session_name):
            sessions_found = True
            subprocess.run(["tmux", "kill-session", "-t", session_name], capture_output=True)
            console.print(f"[green]Stopped session:[/green] {session_name}")

    if not sessions_found:
        console.print("[dim]No active quant sessions found.[/dim]")
    else:
        console.print("[green]All workers stopped.[/green]")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------
@app.command()
def status(
    watch: bool = typer.Option(False, "--watch", "-w", help="Live-updating dashboard (refresh every 5s)."),
) -> None:
    """[green]Dashboard[/green] -- workers, queues, strategies, and costs."""
    from cli.status import show_status
    show_status(watch=watch)


# ---------------------------------------------------------------------------
# strategies
# ---------------------------------------------------------------------------
@app.command()
def strategies(
    grade: Optional[str] = typer.Option(
        None, "--grade", "-g",
        help="Filter by grade (good, under_review, rejected, prop_firm_ready).",
    ),
) -> None:
    """[green]List strategies[/green] -- discovered and validated strategies with metrics."""
    from cli.strategies import list_strategies
    list_strategies(grade_filter=grade)


# ---------------------------------------------------------------------------
# deploy
# ---------------------------------------------------------------------------
@app.command()
def deploy(
    strategy: Optional[str] = typer.Argument(
        None,
        help="Specific strategy name to deploy. Omit for all validated strategies.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deployed without executing."),
) -> None:
    """[green]Deploy[/green] -- export validated strategies to Freqtrade for paper trading."""
    deploy_script = PROJECT_ROOT / "scripts" / "freqtrade-deploy.sh"
    if not deploy_script.exists():
        console.print(Panel(
            "[red]Deploy script not found.[/red]\n\n"
            f"Expected at: {deploy_script}\n"
            "Run [cyan]sigma-quant init[/cyan] to set up the environment first.",
            title="Deployment Error",
            border_style="red",
        ))
        raise typer.Exit(code=1)

    strategies_dir = PROJECT_ROOT / "output" / "strategies" / "prop_firm_ready"
    if not strategies_dir.is_dir() or not any(strategies_dir.iterdir()):
        good_dir = PROJECT_ROOT / "output" / "strategies" / "good"
        if not good_dir.is_dir() or not any(good_dir.iterdir()):
            console.print("[yellow]No validated strategies found to deploy.[/yellow]")
            console.print("Run the research pipeline first to discover strategies.")
            raise typer.Exit(code=1)

    if dry_run:
        console.print("[cyan]Dry run -- showing deployable strategies:[/cyan]\n")
        for dir_name in ["prop_firm_ready", "good"]:
            d = PROJECT_ROOT / "output" / "strategies" / dir_name
            if d.is_dir():
                for f in sorted(d.glob("*.json")):
                    try:
                        data = json.loads(f.read_text())
                        name = data.get("name", data.get("strategy_name", f.stem))
                        if strategy and strategy.lower() not in name.lower():
                            continue
                        console.print(f"  [green]>>>[/green] {name} ({dir_name})")
                    except (json.JSONDecodeError, OSError):
                        continue
        return

    console.print("[cyan]Deploying strategies to Freqtrade...[/cyan]")
    cmd = ["bash", str(deploy_script)]
    if strategy:
        cmd.append(strategy)
    subprocess.run(cmd, cwd=str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# tutorial
# ---------------------------------------------------------------------------
@app.command()
def tutorial() -> None:
    """[green]Interactive tutorial[/green] -- 6-step walkthrough of the pipeline."""
    from cli.tutorial import run_tutorial
    run_tutorial()


# ---------------------------------------------------------------------------
# data subcommands
# ---------------------------------------------------------------------------
@data_app.command("download")
def data_download(
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p",
        help="Data provider (databento, ccxt, hyperliquid). Auto-detected from profile if omitted.",
    ),
    symbol: Optional[str] = typer.Option(None, "--symbol", "-s", help="Symbol to download (e.g. ES, BTCUSDT)."),
    timeframe: str = typer.Option("5m", "--timeframe", "-t", help="Candle timeframe."),
    bars: int = typer.Option(5000, "--bars", "-b", help="Number of bars to download."),
) -> None:
    """[green]Download[/green] historical market data."""
    profile = _load_active_profile()
    adapter = provider or profile.get("dataProvider", {}).get("adapter", "ccxt")
    market_type = profile.get("marketType", "")

    console.print(Panel(
        f"Provider: [cyan]{adapter}[/cyan]\n"
        f"Market:   [cyan]{profile.get('displayName', market_type)}[/cyan]\n"
        f"Timeframe: [cyan]{timeframe}[/cyan]\n"
        f"Bars:     [cyan]{bars}[/cyan]",
        title="Data Download",
        border_style="cyan",
    ))

    download_script = PROJECT_ROOT / "scripts" / "download-data.py"

    if adapter == "databento":
        # Futures data via Databento
        api_key = os.environ.get("DATABENTO_API_KEY", "")
        if not api_key:
            env_path = PROJECT_ROOT / ".env"
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    if line.startswith("DATABENTO_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
            if not api_key:
                api_key = Prompt.ask("[yellow]Enter your Databento API key[/yellow]")
                if not api_key:
                    console.print("[red]Databento API key is required for futures data.[/red]")
                    raise typer.Exit(code=1)

        symbols = [symbol] if symbol else profile.get("symbols", {}).get("pinned", ["ES"])
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task("Downloading futures data...", total=len(symbols))
            for sym in symbols:
                progress.update(task, description=f"Downloading {sym}...")
                cmd = [
                    sys.executable, str(download_script),
                    "--provider", "databento",
                    "--symbol", sym,
                    "--timeframe", timeframe,
                    "--bars", str(bars),
                ]
                env = os.environ.copy()
                env["DATABENTO_API_KEY"] = api_key
                subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env, capture_output=True)
                progress.advance(task)

        console.print("[green]Futures data download complete.[/green]")

    elif adapter in ("ccxt", "hyperliquid"):
        # Crypto data via CCXT or Hyperliquid
        symbols = [symbol] if symbol else profile.get("symbols", {}).get("pinned", [])
        if not symbols:
            # Use default symbols from profile
            sample_files = profile.get("dataProvider", {}).get("sampleFiles", [])
            symbols = [f.split("_")[0] for f in sample_files]

        if not symbols:
            console.print("[yellow]No symbols configured. Specify with --symbol.[/yellow]")
            raise typer.Exit(code=1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task("Downloading crypto data...", total=len(symbols))
            for sym in symbols:
                progress.update(task, description=f"Downloading {sym}...")
                if download_script.exists():
                    exchange = profile.get("dataProvider", {}).get("exchange", "binance")
                    cmd = [
                        sys.executable, str(download_script),
                        "--provider", adapter,
                        "--exchange", exchange,
                        "--symbol", sym,
                        "--timeframe", timeframe,
                        "--bars", str(bars),
                    ]
                    subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True)
                progress.advance(task)

        console.print("[green]Crypto data download complete.[/green]")

    else:
        console.print(f"[red]Unknown data provider: {adapter}[/red]")
        raise typer.Exit(code=1)


@data_app.command("status")
def data_status() -> None:
    """[green]Data coverage[/green] -- show available data per market."""
    data_dir = PROJECT_ROOT / "data"
    if not data_dir.is_dir():
        console.print("[yellow]No data/ directory found.[/yellow]")
        raise typer.Exit(code=1)

    import datetime

    table = Table(title="Data Coverage", show_header=True, header_style="bold cyan")
    table.add_column("File", style="white")
    table.add_column("Size", justify="right")
    table.add_column("Rows (est.)", justify="right")
    table.add_column("Modified", justify="right")

    def _scan_dir(d: Path, prefix: str = "") -> None:
        for f in sorted(d.iterdir()):
            if f.is_dir():
                _scan_dir(f, prefix=f"{f.name}/")
            elif f.is_file() and f.suffix in (".csv", ".parquet", ".json"):
                size = f.stat().st_size
                if size > 1_000_000:
                    size_str = f"{size / 1_000_000:.1f} MB"
                elif size > 1_000:
                    size_str = f"{size / 1_000:.1f} KB"
                else:
                    size_str = f"{size} B"

                # Estimate rows for CSV files
                rows_str = "-"
                if f.suffix == ".csv" and size > 0:
                    try:
                        with open(f) as fh:
                            line_count = sum(1 for _ in fh) - 1  # subtract header
                        rows_str = f"{line_count:,}"
                    except OSError:
                        pass

                mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
                table.add_row(
                    f"{prefix}{f.name}",
                    size_str,
                    rows_str,
                    mtime.strftime("%Y-%m-%d %H:%M"),
                )

    _scan_dir(data_dir)
    console.print(table)


# ---------------------------------------------------------------------------
# config subcommands
# ---------------------------------------------------------------------------
@config_app.callback(invoke_without_command=True)
def config_default(ctx: typer.Context) -> None:
    """[green]View configuration[/green] -- current settings from config.json."""
    if ctx.invoked_subcommand is not None:
        return

    config = _load_config()
    syntax = Syntax(
        json.dumps(config, indent=2),
        "json",
        theme="monokai",
        line_numbers=True,
    )
    console.print(syntax)


@config_app.command("profiles")
def config_profiles() -> None:
    """[green]Market profiles[/green] -- list and inspect available profiles."""
    config = _load_config()
    active = config.get("activeProfile", "")
    profiles = config.get("marketProfiles", {})

    table = Table(title="Market Profiles", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="white")
    table.add_column("Display Name")
    table.add_column("Type")
    table.add_column("Active", justify="center")

    for name, info in profiles.items():
        is_active = info.get("path", "") == active
        active_marker = "[green bold]>>>[/green bold]" if is_active else ""
        table.add_row(
            name,
            info.get("displayName", ""),
            info.get("marketType", ""),
            active_marker,
        )

    console.print(table)


@config_app.command("switch")
def config_switch(
    profile: str = typer.Argument(..., help="Profile name to switch to (futures, crypto-cex, crypto-dex-hyperliquid)."),
) -> None:
    """[green]Switch profile[/green] -- change the active market profile."""
    config_path = PROJECT_ROOT / "config.json"
    config = _load_config()
    profiles = config.get("marketProfiles", {})

    if profile not in profiles:
        console.print(f"[red]Unknown profile:[/red] {profile}")
        console.print(f"Available: {', '.join(profiles.keys())}")
        raise typer.Exit(code=1)

    new_path = profiles[profile].get("path", f"profiles/{profile}.json")
    full_path = PROJECT_ROOT / new_path
    if not full_path.exists():
        console.print(f"[red]Profile file not found:[/red] {full_path}")
        raise typer.Exit(code=1)

    config["activeProfile"] = new_path
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    console.print(f"[green]Switched to profile:[/green] {profiles[profile].get('displayName', profile)}")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key (dot notation, e.g. defaults.mode)."),
    value: str = typer.Argument(..., help="New value to set."),
) -> None:
    """[green]Set config value[/green] -- update a configuration key."""
    config_path = PROJECT_ROOT / "config.json"
    config = _load_config()

    # Navigate dot notation
    parts = key.split(".")
    target = config
    for part in parts[:-1]:
        if part not in target or not isinstance(target[part], dict):
            console.print(f"[red]Invalid config key:[/red] {key}")
            raise typer.Exit(code=1)
        target = target[part]

    final_key = parts[-1]
    if final_key not in target:
        console.print(f"[yellow]Creating new key:[/yellow] {key}")

    # Try to parse value as JSON for structured types
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = value

    old_value = target.get(final_key, "<unset>")
    target[final_key] = parsed

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    console.print(f"[green]Updated:[/green] {key}")
    console.print(f"  Old: [dim]{old_value}[/dim]")
    console.print(f"  New: [cyan]{parsed}[/cyan]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    app()


if __name__ == "__main__":
    main()
