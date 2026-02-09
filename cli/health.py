"""Sigma-Quant Stream — Health check implementation."""

from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_PACKAGES = [
    "pandas",
    "pandas_ta",
    "ccxt",
    "typer",
    "rich",
]

REQUIRED_ENV_KEYS = [
    "DATABENTO_API_KEY",
]

QUEUE_DIRS = [
    "queues/hypotheses",
    "queues/to-convert",
    "queues/to-backtest",
    "queues/to-optimize",
]


def _check_python_version() -> tuple[bool, str]:
    v = sys.version_info
    version_str = f"{v.major}.{v.minor}.{v.micro}"
    ok = (v.major, v.minor) >= (3, 11)
    return ok, f"Python {version_str}"


def _check_package(name: str) -> tuple[bool, str]:
    try:
        mod = importlib.import_module(name)
        version = getattr(mod, "__version__", "installed")
        return True, f"{name} {version}"
    except ImportError:
        return False, f"{name} not installed"


def _check_cli(cmd: str, label: str) -> tuple[bool, str]:
    path = shutil.which(cmd)
    if not path:
        return False, f"{label} not found"
    try:
        result = subprocess.run(
            [cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        version = result.stdout.strip().split("\n")[0] if result.stdout.strip() else "found"
        return True, f"{label} {version}"
    except (subprocess.SubprocessError, OSError):
        return True, f"{label} found at {path}"


def _check_env_file() -> tuple[bool, str]:
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        return True, ".env file found"
    return False, ".env file missing"


def _check_env_key(key: str) -> tuple[bool, str]:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return False, f"{key} — .env missing"
    content = env_path.read_text()
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key and v.strip().strip('"').strip("'"):
            return True, f"{key} set"
    if os.environ.get(key):
        return True, f"{key} set (env)"
    return False, f"{key} missing"


def _check_config_json() -> tuple[bool, str]:
    cfg_path = PROJECT_ROOT / "config.json"
    if not cfg_path.exists():
        return False, "config.json not found"
    try:
        with open(cfg_path) as f:
            json.load(f)
        return True, "config.json valid"
    except json.JSONDecodeError as e:
        return False, f"config.json invalid: {e}"


def _check_directory(rel_path: str) -> tuple[bool, str]:
    full = PROJECT_ROOT / rel_path
    if full.is_dir():
        return True, f"{rel_path}/ exists"
    return False, f"{rel_path}/ missing"


def run_health_check() -> int:
    """Run all health checks and display results. Returns count of failures."""
    checks: list[tuple[bool, str]] = []

    checks.append(_check_python_version())

    for pkg in REQUIRED_PACKAGES:
        checks.append(_check_package(pkg))

    checks.append(_check_cli("claude", "Claude Code CLI"))
    checks.append(_check_cli("tmux", "tmux"))

    checks.append(_check_env_file())
    for key in REQUIRED_ENV_KEYS:
        checks.append(_check_env_key(key))

    checks.append(_check_config_json())

    for qdir in QUEUE_DIRS:
        checks.append(_check_directory(qdir))

    checks.append(_check_directory("data"))

    lines = Text()
    passed = 0
    failed = 0
    for ok, label in checks:
        if ok:
            lines.append(" [check] ", style="green bold")
            lines.append(label + "\n", style="green")
            passed += 1
        else:
            lines.append(" [x]    ", style="red bold")
            lines.append(label + "\n", style="red")
            failed += 1

    total = passed + failed
    score_style = "green bold" if failed == 0 else ("yellow bold" if failed <= 2 else "red bold")
    lines.append(f"\n Score: {passed}/{total} checks passed", style=score_style)

    panel = Panel(
        lines,
        title="Sigma-Quant Health Check",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)

    return failed
