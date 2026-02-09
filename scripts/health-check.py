#!/usr/bin/env python3
"""
QuantStream Health Check
=========================
Post-setup environment validator. Checks all dependencies, keys, and tools
needed to run the Quant Research Team.

Usage:
    python health-check.py           # Full check
    python health-check.py --fix     # Auto-install missing soft dependencies
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
STREAM_QUANT = PROJECT_ROOT / "stream-quant"
ACTIVE_PROFILE = STREAM_QUANT / "profiles" / "active-profile.json"

# ---------------------------------------------------------------------------
# Terminal colours
# ---------------------------------------------------------------------------
class C:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    NC = "\033[0m"


def check_mark(ok: bool, label: str, detail: str = "", blocker: bool = False):
    if ok:
        print(f"  {C.GREEN}\u2713{C.NC} {label}  {C.DIM}{detail}{C.NC}")
    elif blocker:
        print(f"  {C.RED}\u2717{C.NC} {label}  {C.RED}{detail}{C.NC}")
    else:
        print(f"  {C.YELLOW}\u26a0{C.NC} {label}  {C.YELLOW}{detail}{C.NC}")


def run_cmd(cmd: list[str], timeout: int = 10) -> tuple[bool, str]:
    """Run a command, return (success, output)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False, ""


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
class CheckResult:
    def __init__(self):
        self.blockers: list[str] = []
        self.warnings: list[str] = []
        self.passed: int = 0
        self.total: int = 0


def check_python(results: CheckResult):
    """Check Python 3.8+."""
    results.total += 1
    v = sys.version_info
    ok = v.major == 3 and v.minor >= 8
    version_str = f"{v.major}.{v.minor}.{v.micro}"
    if ok:
        results.passed += 1
        check_mark(True, "Python 3.8+", f"v{version_str}", blocker=True)
    else:
        results.blockers.append("Python 3.8+")
        check_mark(False, "Python 3.8+", f"Found v{version_str} \u2014 need 3.8+. Install: https://python.org", blocker=True)


def check_claude_cli(results: CheckResult):
    """Check Claude Code CLI."""
    results.total += 1
    ok, output = run_cmd(["claude", "--version"])
    if ok:
        results.passed += 1
        check_mark(True, "Claude CLI", output.split("\n")[0])
    else:
        results.blockers.append("Claude CLI")
        check_mark(False, "Claude CLI", "Install: npm install -g @anthropic-ai/claude-code", blocker=True)


def check_anthropic_key(results: CheckResult):
    """Check ANTHROPIC_API_KEY."""
    results.total += 1
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
        # Quick validation
        try:
            import requests
            resp = requests.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                },
                timeout=5,
            )
            if resp.status_code == 200:
                results.passed += 1
                check_mark(True, "ANTHROPIC_API_KEY", f"{masked} (validated)")
            else:
                results.passed += 1  # Key exists even if validation fails
                check_mark(True, "ANTHROPIC_API_KEY", f"{masked} (set, validation returned {resp.status_code})")
        except Exception:
            results.passed += 1
            check_mark(True, "ANTHROPIC_API_KEY", f"{masked} (set, could not validate)")
    else:
        results.blockers.append("ANTHROPIC_API_KEY")
        check_mark(False, "ANTHROPIC_API_KEY", "Export ANTHROPIC_API_KEY=sk-ant-...", blocker=True)


def check_tmux(results: CheckResult):
    """Check tmux."""
    results.total += 1
    ok, output = run_cmd(["tmux", "-V"])
    if ok:
        results.passed += 1
        check_mark(True, "tmux", output)
    else:
        results.blockers.append("tmux")
        install_cmd = "brew install tmux" if platform.system() == "Darwin" else "sudo apt install tmux"
        check_mark(False, "tmux", f"Install: {install_cmd}", blocker=True)


def check_pip_package(name: str, import_name: str, results: CheckResult, auto_fix: bool = False):
    """Check if a pip package is importable."""
    results.total += 1
    try:
        __import__(import_name)
        # Get version if possible
        try:
            mod = __import__(import_name)
            ver = getattr(mod, "__version__", "installed")
        except Exception:
            ver = "installed"
        results.passed += 1
        check_mark(True, name, ver)
    except ImportError:
        if auto_fix:
            print(f"  {C.CYAN}\u2935{C.NC} Installing {name}...", end="", flush=True)
            ok, _ = run_cmd([sys.executable, "-m", "pip", "install", name], timeout=60)
            if ok:
                results.passed += 1
                check_mark(True, name, "auto-installed")
            else:
                results.warnings.append(name)
                check_mark(False, name, f"pip install {name}")
        else:
            results.warnings.append(name)
            check_mark(False, name, f"pip install {name}")


def check_mcp_tools(results: CheckResult):
    """Check if MCP tools are likely available (heuristic)."""
    results.total += 1
    # Check for MCP config files
    mcp_config = Path.home() / ".claude" / "mcp_config.json"
    local_mcp = PROJECT_ROOT / ".mcp.json"

    if mcp_config.exists() or local_mcp.exists():
        results.passed += 1
        check_mark(True, "MCP tools config", "Config file found")
    else:
        results.warnings.append("MCP tools")
        check_mark(False, "MCP tools (exa, ref)", "See .claude/skills/INDEX.md for setup")


def check_data_provider_key(results: CheckResult):
    """Check for at least one data provider key."""
    results.total += 1
    providers = {
        "DATABENTO_API_KEY": "Databento (futures)",
        "BINANCE_API_KEY": "Binance (crypto CEX)",
        "BYBIT_API_KEY": "Bybit (crypto CEX)",
        "OKX_API_KEY": "OKX (crypto CEX)",
    }
    found = []
    for env, label in providers.items():
        if os.environ.get(env):
            found.append(label)

    if found:
        results.passed += 1
        check_mark(True, "Data provider key", ", ".join(found))
    else:
        results.warnings.append("Data provider key")
        check_mark(
            False,
            "Data provider key",
            "No provider key found \u2014 will use sample data as fallback",
        )


def check_elevenlabs(results: CheckResult):
    """Check ElevenLabs key (purely optional)."""
    results.total += 1
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    if key:
        results.passed += 1
        check_mark(True, "ElevenLabs", "Voice notifications enabled")
    else:
        # Check for macOS say
        has_say = shutil.which("say") is not None
        if has_say:
            results.passed += 1
            check_mark(True, "Voice notifications", "Using macOS 'say' (no ElevenLabs key)")
        else:
            results.warnings.append("Voice notifications")
            check_mark(False, "Voice notifications", "Set ELEVENLABS_API_KEY or install macOS")


def check_disk_space(results: CheckResult):
    """Check for 500MB free disk space."""
    results.total += 1
    try:
        stat = os.statvfs(str(PROJECT_ROOT))
        free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
        if free_mb >= 500:
            results.passed += 1
            check_mark(True, "Disk space", f"{free_mb / 1024:.1f} GB free")
        else:
            results.warnings.append("Disk space")
            check_mark(False, "Disk space", f"Only {free_mb:.0f} MB free (need 500 MB)")
    except Exception:
        results.passed += 1
        check_mark(True, "Disk space", "Could not check, assuming OK")


def check_active_profile(results: CheckResult, auto_fix: bool = False):
    """Check if active profile exists."""
    results.total += 1
    if ACTIVE_PROFILE.exists():
        try:
            import json
            with open(ACTIVE_PROFILE) as f:
                profile = json.load(f)
            name = profile.get("displayName", "Unknown")
            results.passed += 1
            check_mark(True, "Active profile", name)
        except Exception:
            results.warnings.append("Active profile (corrupt)")
            check_mark(False, "Active profile", "File exists but is corrupt")
    else:
        if auto_fix:
            print(f"  {C.CYAN}\u2935{C.NC} Running setup wizard...\n")
            wizard = SCRIPT_DIR / "setup-wizard.py"
            if wizard.exists():
                subprocess.run([sys.executable, str(wizard)], cwd=str(PROJECT_ROOT))
                if ACTIVE_PROFILE.exists():
                    results.passed += 1
                    check_mark(True, "Active profile", "Created via wizard")
                else:
                    results.warnings.append("Active profile")
                    check_mark(False, "Active profile", "Wizard did not create profile")
            else:
                results.warnings.append("Active profile")
                check_mark(False, "Active profile", "setup-wizard.py not found")
        else:
            results.warnings.append("Active profile")
            check_mark(False, "Active profile", "Run: python scripts/quant-team/setup-wizard.py")


def check_git(results: CheckResult):
    """Check git is available."""
    results.total += 1
    ok, output = run_cmd(["git", "--version"])
    if ok:
        results.passed += 1
        check_mark(True, "git", output)
    else:
        results.warnings.append("git")
        check_mark(False, "git", "Install git for version control")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="QuantStream Health Check")
    parser.add_argument("--fix", action="store_true", help="Auto-install missing soft dependencies")
    args = parser.parse_args()

    print(f"""
{C.CYAN}{C.BOLD}
 \u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510
 \u2502        QuantStream Health Check                         \u2502
 \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518
{C.NC}""")

    results = CheckResult()

    # ---- Blockers ----
    print(f"  {C.BOLD}Required (blockers){C.NC}")
    print(f"  {C.DIM}{'=' * 50}{C.NC}")
    check_python(results)
    check_claude_cli(results)
    check_anthropic_key(results)
    check_tmux(results)

    # ---- Soft dependencies ----
    print(f"\n  {C.BOLD}Recommended (soft){C.NC}")
    print(f"  {C.DIM}{'=' * 50}{C.NC}")
    check_pip_package("requests", "requests", results, auto_fix=args.fix)
    check_pip_package("ccxt", "ccxt", results, auto_fix=args.fix)
    check_mcp_tools(results)
    check_data_provider_key(results)
    check_git(results)

    # ---- Optional ----
    print(f"\n  {C.BOLD}Optional{C.NC}")
    print(f"  {C.DIM}{'=' * 50}{C.NC}")
    check_elevenlabs(results)
    check_disk_space(results)
    check_active_profile(results, auto_fix=args.fix)

    # ---- Summary ----
    print(f"\n  {C.BOLD}{'=' * 50}{C.NC}")
    print(f"  {C.BOLD}Results:{C.NC} {results.passed}/{results.total} checks passed")

    if results.blockers:
        print(f"\n  {C.RED}{C.BOLD}BLOCKERS (must fix before running):{C.NC}")
        for b in results.blockers:
            print(f"    {C.RED}\u2022{C.NC} {b}")
        print(f"\n  {C.RED}Fix blockers and re-run: python scripts/quant-team/health-check.py{C.NC}")
        sys.exit(1)

    if results.warnings:
        print(f"\n  {C.YELLOW}Warnings (optional to fix):{C.NC}")
        for w in results.warnings:
            print(f"    {C.YELLOW}\u2022{C.NC} {w}")
        print(f"\n  {C.DIM}Auto-fix soft deps: python scripts/quant-team/health-check.py --fix{C.NC}")

    if not results.blockers:
        print(f"""
  {C.GREEN}{C.BOLD}Ready to go!{C.NC}

  Next steps:
    {C.CYAN}python scripts/quant-team/setup-wizard.py{C.NC}   # First-time setup
    {C.CYAN}./scripts/quant-team/spawn-quant-team.sh{C.NC}    # Launch team
""")


if __name__ == "__main__":
    main()
