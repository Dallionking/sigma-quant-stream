"""Sigma-Quant Stream -- Claude Code agent team setup.

Usage:
    sigma-quant setup-claude
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Step helpers
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


# ---------------------------------------------------------------------------
# Step 1: Verify Claude Code CLI
# ---------------------------------------------------------------------------

def _step_verify_claude() -> bool:
    """Check that Claude Code CLI is installed and accessible."""
    _step_header(1, 5, "VERIFY CLAUDE CODE CLI")

    claude_path = shutil.which("claude")
    if not claude_path:
        console.print(Panel(
            "[red bold]Claude Code CLI not found.[/red bold]\n\n"
            "Install it with:\n"
            "  [cyan]npm install -g @anthropic-ai/claude-code[/cyan]\n\n"
            "Or follow the docs at:\n"
            "  https://docs.anthropic.com/en/docs/claude-code",
            title="Missing Dependency",
            border_style="red",
        ))
        return False

    # Get version
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        version = result.stdout.strip().split("\n")[0] if result.stdout.strip() else "unknown"
    except (subprocess.SubprocessError, OSError):
        version = "found (version unknown)"

    console.print(f"[green]Claude Code CLI found:[/green] {version}")
    console.print(f"[dim]Path: {claude_path}[/dim]")
    return True


# ---------------------------------------------------------------------------
# Step 2: Install .claude/settings.json
# ---------------------------------------------------------------------------

CLAUDE_SETTINGS = {
    "permissions": {
        "allow": [
            "Bash(*)",
            "Read(*)",
            "Write(**)",
            "Edit(**)",
            "Glob(*)",
            "Grep(*)",
            "mcp__exa__*",
            "mcp__Ref__*",
        ],
    },
}


def _step_install_settings() -> None:
    """Create or update .claude/settings.json."""
    _step_header(2, 5, "CONFIGURE SETTINGS")

    claude_dir = PROJECT_ROOT / ".claude"
    settings_path = claude_dir / "settings.json"

    claude_dir.mkdir(exist_ok=True)

    if settings_path.exists():
        with open(settings_path) as f:
            existing = json.load(f)

        console.print("[yellow]Existing .claude/settings.json found.[/yellow]\n")
        console.print(Syntax(
            json.dumps(existing, indent=2),
            "json",
            theme="monokai",
        ))
        console.print()

        overwrite = Confirm.ask("Overwrite with recommended settings?", default=False)
        if not overwrite:
            # Merge permissions
            existing_perms = existing.get("permissions", {}).get("allow", [])
            new_perms = CLAUDE_SETTINGS["permissions"]["allow"]
            merged = list(dict.fromkeys(existing_perms + new_perms))  # preserve order, dedupe
            existing.setdefault("permissions", {})["allow"] = merged

            with open(settings_path, "w") as f:
                json.dump(existing, f, indent=2)
                f.write("\n")

            console.print("[green]Merged permissions into existing settings.[/green]")
            return

    with open(settings_path, "w") as f:
        json.dump(CLAUDE_SETTINGS, f, indent=2)
        f.write("\n")

    console.print("[green]Created .claude/settings.json[/green]")
    console.print()
    console.print(Syntax(
        json.dumps(CLAUDE_SETTINGS, indent=2),
        "json",
        theme="monokai",
    ))

    console.print()
    console.print("Permissions granted:")
    perm_table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    perm_table.add_column("Permission", style="white")
    perm_table.add_column("Description")

    perm_descriptions = {
        "Bash(*)": "Execute shell commands",
        "Read(*)": "Read any file",
        "Write(**)": "Write any file",
        "Edit(**)": "Edit any file",
        "Glob(*)": "Search file patterns",
        "Grep(*)": "Search file contents",
        "mcp__exa__*": "Exa web search and crawling",
        "mcp__Ref__*": "Ref documentation lookup",
    }

    for perm in CLAUDE_SETTINGS["permissions"]["allow"]:
        desc = perm_descriptions.get(perm, "")
        perm_table.add_row(perm, desc)

    console.print(perm_table)


# ---------------------------------------------------------------------------
# Step 3: Terminal layout choice
# ---------------------------------------------------------------------------

def _step_terminal_layout() -> str:
    """Choose terminal layout. Returns 'tmux', 'iterm', or 'manual'."""
    _step_header(3, 5, "TERMINAL LAYOUT")

    is_macos = platform.system() == "Darwin"
    has_tmux = shutil.which("tmux") is not None

    console.print("Choose how to arrange worker terminals:\n")

    options = []
    if has_tmux:
        console.print("  [bold cyan][1][/bold cyan] tmux (recommended) -- 4 panes in one terminal window")
        options.append("1")
    else:
        console.print("  [dim][1] tmux -- not installed (brew install tmux)[/dim]")

    if is_macos:
        console.print("  [bold cyan][2][/bold cyan] iTerm2 native panes -- macOS AppleScript integration")
        options.append("2")
    else:
        console.print("  [dim][2] iTerm2 -- macOS only[/dim]")

    console.print("  [bold cyan][3][/bold cyan] Manual -- copy-paste commands yourself")
    options.append("3")

    console.print()
    choice = Prompt.ask("Select layout", choices=options, default=options[0])

    layout_map = {"1": "tmux", "2": "iterm", "3": "manual"}
    selected = layout_map[choice]
    console.print(f"\n[green]Selected:[/green] {selected}")
    return selected


# ---------------------------------------------------------------------------
# Step 4: Generate layout scripts
# ---------------------------------------------------------------------------

TMUX_LAYOUT_SCRIPT = """#!/bin/bash
# Sigma-Quant Stream -- tmux layout launcher
# Generated by: sigma-quant setup-claude

set -euo pipefail

SESSION="sigma-quant"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Kill existing session if present
tmux has-session -t "$SESSION" 2>/dev/null && tmux kill-session -t "$SESSION"

# Create session with first worker
tmux new-session -d -s "$SESSION" -n workers -c "$PROJECT_DIR"

# Split into 4 panes
tmux split-window -t "$SESSION:workers" -h -c "$PROJECT_DIR"
tmux split-window -t "$SESSION:workers.0" -v -c "$PROJECT_DIR"
tmux split-window -t "$SESSION:workers.2" -v -c "$PROJECT_DIR"

# Send commands to each pane
WORKERS=("researcher" "converter" "backtester" "optimizer")
for i in "${!WORKERS[@]}"; do
    WORKER="${WORKERS[$i]}"
    if [ -f "$PROJECT_DIR/scripts/quant-ralph.sh" ]; then
        tmux send-keys -t "$SESSION:workers.$i" "bash scripts/quant-ralph.sh $WORKER" C-m
    else
        tmux send-keys -t "$SESSION:workers.$i" "echo 'Worker: $WORKER -- ready'" C-m
    fi
done

# Create a 5th pane for status
tmux split-window -t "$SESSION:workers" -v -l 8 -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION:workers.4" "python -m cli.main status --watch" C-m

# Arrange panes
tmux select-layout -t "$SESSION:workers" tiled

echo "Session '$SESSION' created with ${#WORKERS[@]} workers + status pane."
echo "Attach with: tmux attach -t $SESSION"
"""


ITERM_LAYOUT_SCRIPT = """#!/bin/bash
# Sigma-Quant Stream -- iTerm2 layout launcher (macOS)
# Generated by: sigma-quant setup-claude

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKERS=("researcher" "converter" "backtester" "optimizer")

osascript <<APPLESCRIPT
tell application "iTerm2"
    activate

    -- Create new window
    set newWindow to (create window with default profile)

    tell current session of newWindow
        set name to "researcher"
        write text "cd '$PROJECT_DIR' && bash scripts/quant-ralph.sh researcher"
    end tell

    -- Split horizontally for converter
    tell current session of newWindow
        set newSession to (split horizontally with default profile)
        tell newSession
            set name to "converter"
            write text "cd '$PROJECT_DIR' && bash scripts/quant-ralph.sh converter"
        end tell
    end tell

    -- Go to first tab's first session and split vertically for backtester
    tell first session of first tab of newWindow
        set newSession to (split vertically with default profile)
        tell newSession
            set name to "backtester"
            write text "cd '$PROJECT_DIR' && bash scripts/quant-ralph.sh backtester"
        end tell
    end tell

    -- Split the converter pane vertically for optimizer
    tell last session of first tab of newWindow
        set newSession to (split vertically with default profile)
        tell newSession
            set name to "optimizer"
            write text "cd '$PROJECT_DIR' && bash scripts/quant-ralph.sh optimizer"
        end tell
    end tell

end tell
APPLESCRIPT

echo "iTerm2 layout launched with ${#WORKERS[@]} worker panes."
"""


def _step_generate_scripts(layout: str) -> None:
    """Generate terminal layout scripts."""
    _step_header(4, 5, "GENERATE LAYOUT SCRIPTS")

    scripts_dir = PROJECT_ROOT / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    generated: list[str] = []

    if layout in ("tmux", "manual"):
        tmux_path = scripts_dir / "tmux-layout.sh"
        tmux_path.write_text(TMUX_LAYOUT_SCRIPT)
        tmux_path.chmod(0o755)
        generated.append(str(tmux_path))
        console.print(f"[green]Created:[/green] scripts/tmux-layout.sh")

    if layout == "iterm" or platform.system() == "Darwin":
        iterm_path = scripts_dir / "iterm-layout.sh"
        iterm_path.write_text(ITERM_LAYOUT_SCRIPT)
        iterm_path.chmod(0o755)
        generated.append(str(iterm_path))
        console.print(f"[green]Created:[/green] scripts/iterm-layout.sh")

    if layout == "manual":
        console.print()
        console.print("[bold]Manual setup instructions:[/bold]\n")
        console.print("Open 4 terminal windows and run:\n")
        workers = ["researcher", "converter", "backtester", "optimizer"]
        for i, w in enumerate(workers):
            console.print(f"  [cyan]Terminal {i + 1}:[/cyan] cd {PROJECT_ROOT} && bash scripts/quant-ralph.sh {w}")
        console.print(f"\n  [cyan]Terminal 5:[/cyan] cd {PROJECT_ROOT} && sigma-quant status --watch")

    if generated:
        console.print()
        console.print(f"[green]{len(generated)} script(s) generated.[/green]")


# ---------------------------------------------------------------------------
# Step 5: Test launch
# ---------------------------------------------------------------------------

def _step_test_launch(layout: str) -> None:
    """Optionally run a 60-second test."""
    _step_header(5, 5, "TEST LAUNCH (OPTIONAL)")

    console.print(
        "Run a 60-second test to verify everything works?\n"
        "This will launch workers briefly and shut them down.\n"
    )

    run_test = Confirm.ask("Run test launch?", default=False)
    if not run_test:
        console.print("[dim]Skipped test launch.[/dim]")
        _print_completion()
        return

    if layout == "tmux" and shutil.which("tmux"):
        tmux_script = PROJECT_ROOT / "scripts" / "tmux-layout.sh"
        if tmux_script.exists():
            console.print("[cyan]Launching tmux layout for 60 seconds...[/cyan]")
            subprocess.run(["bash", str(tmux_script)], cwd=str(PROJECT_ROOT))

            import time

            console.print("[dim]Workers running. Waiting 60 seconds...[/dim]")
            try:
                time.sleep(60)
            except KeyboardInterrupt:
                console.print("[yellow]Interrupted.[/yellow]")

            # Kill the test session
            subprocess.run(
                ["tmux", "kill-session", "-t", "sigma-quant"],
                capture_output=True,
            )
            console.print("[green]Test complete. Workers shut down.[/green]")
        else:
            console.print("[yellow]tmux-layout.sh not found. Skipping test.[/yellow]")
    else:
        console.print(
            "[dim]Test launch only available with tmux layout.\n"
            "You can test manually by running:[/dim]\n"
            f"  [cyan]sigma-quant start[/cyan]"
        )

    _print_completion()


def _print_completion() -> None:
    """Print setup completion message."""
    console.print()
    console.print(Panel(
        "[bold green]Claude Code setup complete.[/bold green]\n\n"
        "Your agent team is configured and ready.\n\n"
        "Quick start:\n"
        "  [cyan]sigma-quant start[/cyan]          -- Launch all workers\n"
        "  [cyan]sigma-quant status --watch[/cyan]  -- Monitor the dashboard\n"
        "  [cyan]sigma-quant tutorial[/cyan]        -- Learn the pipeline\n\n"
        "Layout scripts:\n"
        "  [dim]scripts/tmux-layout.sh[/dim]   -- tmux pane layout\n"
        "  [dim]scripts/iterm-layout.sh[/dim]  -- iTerm2 pane layout (macOS)",
        title="Setup Complete",
        border_style="green",
    ))


# ---------------------------------------------------------------------------
# Main Entry
# ---------------------------------------------------------------------------

def run_setup_claude() -> None:
    """Run the full Claude Code setup flow."""
    console.print()
    console.print(Panel(
        "[bold cyan]Claude Code Agent Team Setup[/bold cyan]\n"
        "[dim]Configure Claude Code for autonomous strategy research[/dim]",
        border_style="cyan",
        padding=(1, 2),
    ))

    # Step 1: Verify CLI
    cli_ok = _step_verify_claude()
    if not cli_ok:
        proceed = Confirm.ask("Continue setup without Claude Code CLI?", default=True)
        if not proceed:
            console.print("[dim]Exiting setup.[/dim]")
            return

    # Step 2: Install settings
    _step_install_settings()

    # Step 3: Terminal layout
    layout = _step_terminal_layout()

    # Step 4: Generate scripts
    _step_generate_scripts(layout)

    # Step 5: Test launch
    _step_test_launch(layout)
