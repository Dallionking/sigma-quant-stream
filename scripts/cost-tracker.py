#!/usr/bin/env python3
"""
cost-tracker.py - Budget Enforcement and API Spend Tracking
============================================================

Tracks API costs across all panes and enforces budget caps.
When budget is exceeded, pauses all panes and sends notification.

Usage:
    python cost-tracker.py --add --pane=1 --service=claude_api --amount=0.15 --description="Backtest iteration"
    python cost-tracker.py --status
    python cost-tracker.py --check  # Returns exit code 1 if budget exceeded
    python cost-tracker.py --reset  # Reset all tracking (use carefully)
    python cost-tracker.py --set-budget=100.00

Services tracked:
    - claude_api: Claude API calls
    - exa_api: Exa search/research
    - elevenlabs: Voice notifications
    - firecrawl: Web scraping
    - perplexity: Perplexity API
    - databento: Market data (if used)

Environment Variables:
    QUANT_BUDGET_CAP: Override default budget cap (default: $50.00)
"""

import os
import sys
import json
import argparse
import fcntl
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

# Configuration
SCRIPT_DIR = Path(__file__).parent
STREAM_QUANT_DIR = SCRIPT_DIR.parent.parent / "stream-quant"
COST_FILE = STREAM_QUANT_DIR / "cost-tracker.json"
PROGRESS_FILE = STREAM_QUANT_DIR / "progress.json"

# Default budget from environment or $50
DEFAULT_BUDGET = float(os.getenv("QUANT_BUDGET_CAP", "50.00"))

# Service cost estimates (per unit)
COST_ESTIMATES = {
    "claude_api": {
        "input_per_1k": 0.003,    # $3/M input tokens = $0.003/1K
        "output_per_1k": 0.015,   # $15/M output tokens = $0.015/1K
        "typical_call": 0.02,     # Typical call estimate
    },
    "exa_api": {
        "search": 0.001,          # Per search
        "deep_research": 0.01,    # Per deep research
    },
    "elevenlabs": {
        "per_character": 0.00003, # ~$0.30/10K chars
        "typical_notification": 0.01,
    },
    "firecrawl": {
        "per_page": 0.001,
    },
    "perplexity": {
        "per_query": 0.005,
    },
    "databento": {
        "per_symbol_day": 0.01,
    },
}


def acquire_lock(file_handle) -> bool:
    """Acquire exclusive lock on file."""
    try:
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False


def release_lock(file_handle) -> None:
    """Release lock on file."""
    fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)


def load_cost_data() -> Dict[str, Any]:
    """Load cost tracking data, creating if doesn't exist."""
    if not COST_FILE.exists():
        COST_FILE.parent.mkdir(parents=True, exist_ok=True)
        initial = {
            "version": "1.0.0",
            "budget": DEFAULT_BUDGET,
            "spent": 0.00,
            "remaining": DEFAULT_BUDGET,
            "breakdown": {
                "claude_api": 0.00,
                "exa_api": 0.00,
                "elevenlabs": 0.00,
                "firecrawl": 0.00,
                "perplexity": 0.00,
                "databento": 0.00,
            },
            "byPane": {},
            "transactions": [],
            "startedAt": None,
            "pausedAt": None,
            "pauseReason": None,
        }
        save_cost_data(initial)
        return initial

    with open(COST_FILE, 'r') as f:
        return json.load(f)


def save_cost_data(data: Dict[str, Any]) -> None:
    """Save cost tracking data."""
    with open(COST_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def add_cost(
    pane: int,
    service: str,
    amount: float,
    description: str = "",
    tokens_in: int = 0,
    tokens_out: int = 0,
) -> Dict[str, Any]:
    """
    Add a cost entry with file locking.

    Returns:
        Dict with 'success', 'remaining', 'budget_exceeded', etc.
    """
    COST_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Ensure file exists before using 'r+' mode
    if not COST_FILE.exists():
        save_cost_data(load_cost_data())

    with open(COST_FILE, 'r+') as f:
        # Try to acquire lock with retries
        max_retries = 10
        for i in range(max_retries):
            if acquire_lock(f):
                break
            if i == max_retries - 1:
                return {
                    "success": False,
                    "message": "Could not acquire lock after retries",
                    "retry": True
                }
            time.sleep(0.1)

        try:
            # Read current data
            f.seek(0)
            content = f.read()
            if content:
                data = json.loads(content)
            else:
                data = load_cost_data()

            # Set start time if not set
            if not data.get("startedAt"):
                data["startedAt"] = datetime.now().isoformat()

            # Create transaction
            transaction = {
                "id": len(data["transactions"]) + 1,
                "pane": pane,
                "service": service,
                "amount": round(amount, 6),
                "description": description,
                "timestamp": datetime.now().isoformat(),
            }
            if tokens_in:
                transaction["tokens_in"] = tokens_in
            if tokens_out:
                transaction["tokens_out"] = tokens_out

            data["transactions"].append(transaction)

            # Update totals
            data["spent"] = round(data["spent"] + amount, 6)
            data["remaining"] = round(data["budget"] - data["spent"], 6)

            # Update breakdown by service
            if service not in data["breakdown"]:
                data["breakdown"][service] = 0.00
            data["breakdown"][service] = round(
                data["breakdown"][service] + amount, 6
            )

            # Update by pane
            pane_key = str(pane)
            if pane_key not in data["byPane"]:
                data["byPane"][pane_key] = 0.00
            data["byPane"][pane_key] = round(
                data["byPane"][pane_key] + amount, 6
            )

            # Check if budget exceeded
            budget_exceeded = data["spent"] >= data["budget"]

            if budget_exceeded and not data.get("pausedAt"):
                data["pausedAt"] = datetime.now().isoformat()
                data["pauseReason"] = "budget_exceeded"

            # Write updated data
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)

            return {
                "success": True,
                "spent": data["spent"],
                "remaining": data["remaining"],
                "budget": data["budget"],
                "budget_exceeded": budget_exceeded,
                "transaction_id": transaction["id"],
            }

        finally:
            release_lock(f)


def get_status() -> Dict[str, Any]:
    """Get current cost tracking status."""
    data = load_cost_data()

    # Calculate usage percentage
    usage_percent = (data["spent"] / data["budget"]) * 100 if data["budget"] > 0 else 0

    return {
        "budget": data["budget"],
        "spent": data["spent"],
        "remaining": data["remaining"],
        "usage_percent": round(usage_percent, 1),
        "breakdown": data["breakdown"],
        "byPane": data["byPane"],
        "transaction_count": len(data["transactions"]),
        "paused": data.get("pausedAt") is not None,
        "pauseReason": data.get("pauseReason"),
        "startedAt": data.get("startedAt"),
    }


def check_budget() -> Dict[str, Any]:
    """Check if budget is still available."""
    data = load_cost_data()

    # If budget is very high (unlimited mode), always return OK
    is_unlimited = data["budget"] >= 999999
    budget_ok = is_unlimited or data["spent"] < data["budget"]
    remaining = data["remaining"]

    return {
        "ok": budget_ok,
        "remaining": remaining,
        "spent": data["spent"],
        "budget": data["budget"],
        "unlimited": is_unlimited,
        "paused": data.get("pausedAt") is not None,
    }


def set_budget(new_budget: float) -> Dict[str, Any]:
    """Update the budget cap."""
    # Ensure file exists before using 'r+' mode
    if not COST_FILE.exists():
        save_cost_data(load_cost_data())

    with open(COST_FILE, 'r+') as f:
        if not acquire_lock(f):
            return {"success": False, "message": "Could not acquire lock"}

        try:
            f.seek(0)
            content = f.read()
            data = json.loads(content) if content else load_cost_data()

            old_budget = data["budget"]
            data["budget"] = new_budget
            data["remaining"] = round(new_budget - data["spent"], 6)

            # Clear pause if new budget allows
            if data["remaining"] > 0 and data.get("pauseReason") == "budget_exceeded":
                data["pausedAt"] = None
                data["pauseReason"] = None

            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)

            return {
                "success": True,
                "old_budget": old_budget,
                "new_budget": new_budget,
                "remaining": data["remaining"],
                "resumed": data.get("pausedAt") is None,
            }

        finally:
            release_lock(f)


def pause_tracking(reason: str = "manual") -> Dict[str, Any]:
    """Pause cost tracking (stops all panes)."""
    # Ensure file exists before using 'r+' mode
    if not COST_FILE.exists():
        save_cost_data(load_cost_data())

    with open(COST_FILE, 'r+') as f:
        if not acquire_lock(f):
            return {"success": False, "message": "Could not acquire lock"}

        try:
            f.seek(0)
            content = f.read()
            data = json.loads(content) if content else load_cost_data()

            if data.get("pausedAt"):
                return {
                    "success": False,
                    "message": "Already paused",
                    "pausedAt": data["pausedAt"],
                    "pauseReason": data["pauseReason"],
                }

            data["pausedAt"] = datetime.now().isoformat()
            data["pauseReason"] = reason

            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)

            return {"success": True, "pausedAt": data["pausedAt"]}

        finally:
            release_lock(f)


def resume_tracking() -> Dict[str, Any]:
    """Resume cost tracking."""
    # Ensure file exists before using 'r+' mode
    if not COST_FILE.exists():
        save_cost_data(load_cost_data())

    with open(COST_FILE, 'r+') as f:
        if not acquire_lock(f):
            return {"success": False, "message": "Could not acquire lock"}

        try:
            f.seek(0)
            content = f.read()
            data = json.loads(content) if content else load_cost_data()

            if not data.get("pausedAt"):
                return {"success": False, "message": "Not paused"}

            # Can't resume if budget exceeded
            if data["spent"] >= data["budget"]:
                return {
                    "success": False,
                    "message": "Cannot resume - budget exceeded. Increase budget first.",
                    "spent": data["spent"],
                    "budget": data["budget"],
                }

            was_paused_at = data["pausedAt"]
            data["pausedAt"] = None
            data["pauseReason"] = None

            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)

            return {"success": True, "was_paused_at": was_paused_at}

        finally:
            release_lock(f)


def reset_tracking(confirm: bool = False) -> Dict[str, Any]:
    """Reset all cost tracking data."""
    if not confirm:
        return {
            "success": False,
            "message": "Pass --confirm to actually reset all data",
        }

    data = load_cost_data()
    old_spent = data["spent"]
    old_transactions = len(data["transactions"])

    new_data = {
        "version": "1.0.0",
        "budget": data["budget"],  # Keep budget
        "spent": 0.00,
        "remaining": data["budget"],
        "breakdown": {k: 0.00 for k in data["breakdown"]},
        "byPane": {},
        "transactions": [],
        "startedAt": None,
        "pausedAt": None,
        "pauseReason": None,
    }

    save_cost_data(new_data)

    return {
        "success": True,
        "message": f"Reset complete. Cleared ${old_spent:.2f} across {old_transactions} transactions.",
        "old_spent": old_spent,
        "old_transactions": old_transactions,
    }


def get_recent_transactions(limit: int = 10, pane: Optional[int] = None) -> List[Dict]:
    """Get recent transactions, optionally filtered by pane."""
    data = load_cost_data()
    transactions = data["transactions"]

    if pane is not None:
        transactions = [t for t in transactions if t.get("pane") == pane]

    return transactions[-limit:]


def estimate_cost(service: str, operation: str = "typical_call", count: int = 1) -> float:
    """Estimate cost for a planned operation."""
    if service not in COST_ESTIMATES:
        return 0.0

    estimates = COST_ESTIMATES[service]
    if operation in estimates:
        return estimates[operation] * count
    elif "typical_call" in estimates:
        return estimates["typical_call"] * count
    else:
        return list(estimates.values())[0] * count


def main():
    parser = argparse.ArgumentParser(
        description="Quant Research Team Budget Enforcement"
    )

    # Actions
    parser.add_argument("--add", action="store_true", help="Add a cost entry")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--check", action="store_true",
                        help="Check if budget OK (exit 1 if exceeded)")
    parser.add_argument("--reset", action="store_true", help="Reset all tracking")
    parser.add_argument("--confirm", action="store_true", help="Confirm reset")
    parser.add_argument("--pause", action="store_true", help="Pause tracking")
    parser.add_argument("--resume", action="store_true", help="Resume tracking")
    parser.add_argument("--transactions", action="store_true",
                        help="Show recent transactions")
    parser.add_argument("--estimate", help="Estimate cost for service")

    # Parameters
    parser.add_argument("--pane", type=int, help="Pane number")
    parser.add_argument("--service", choices=[
        "claude_api", "exa_api", "elevenlabs", "firecrawl",
        "perplexity", "databento"
    ], help="Service name")
    parser.add_argument("--amount", type=float, help="Cost amount")
    parser.add_argument("--description", default="", help="Description")
    parser.add_argument("--tokens-in", type=int, default=0, help="Input tokens")
    parser.add_argument("--tokens-out", type=int, default=0, help="Output tokens")
    parser.add_argument("--set-budget", type=float, help="Set new budget cap")
    parser.add_argument("--unlimited", action="store_true",
                        help="Mark budget as unlimited (for Claude Max users)")
    parser.add_argument("--limit", type=int, default=10,
                        help="Limit for transactions list")
    parser.add_argument("--reason", default="manual", help="Pause reason")

    # Output
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    result = None

    if args.set_budget:
        result = set_budget(args.set_budget)
        if not args.json:
            if result["success"]:
                if args.unlimited or args.set_budget >= 999999:
                    print("Budget set to UNLIMITED (Claude Max mode)")
                    print("Cost tracking disabled - no budget enforcement")
                else:
                    print(f"Budget updated: ${result['old_budget']:.2f} → ${result['new_budget']:.2f}")
                    print(f"Remaining: ${result['remaining']:.2f}")
                if result.get("resumed"):
                    print("Tracking resumed (was paused due to budget)")
            else:
                print(f"Failed: {result['message']}")

    elif args.add:
        if not args.pane or not args.service or args.amount is None:
            print("Error: --add requires --pane, --service, and --amount")
            sys.exit(1)

        result = add_cost(
            pane=args.pane,
            service=args.service,
            amount=args.amount,
            description=args.description,
            tokens_in=args.tokens_in,
            tokens_out=args.tokens_out,
        )

        if not args.json:
            if result["success"]:
                print(f"Added ${args.amount:.4f} for {args.service}")
                print(f"Spent: ${result['spent']:.2f} / ${result['budget']:.2f} "
                      f"(${result['remaining']:.2f} remaining)")
                if result["budget_exceeded"]:
                    print("⚠️  BUDGET EXCEEDED - Panes will pause")
            else:
                print(f"Failed: {result['message']}")
                sys.exit(1)

    elif args.status:
        result = get_status()

        if not args.json:
            print(f"{'='*50}")
            print(f"Quant Team Budget Status")
            print(f"{'='*50}")
            print(f"Budget:    ${result['budget']:.2f}")
            print(f"Spent:     ${result['spent']:.2f} ({result['usage_percent']:.1f}%)")
            print(f"Remaining: ${result['remaining']:.2f}")
            print()

            if result["breakdown"]:
                print("By Service:")
                for service, amount in result["breakdown"].items():
                    if amount > 0:
                        print(f"  {service:<15} ${amount:.4f}")
            print()

            if result["byPane"]:
                print("By Pane:")
                for pane, amount in result["byPane"].items():
                    print(f"  Pane {pane:<10} ${amount:.4f}")
            print()

            print(f"Transactions: {result['transaction_count']}")
            if result["paused"]:
                print(f"⚠️  PAUSED: {result['pauseReason']}")

    elif args.check:
        result = check_budget()

        if not args.json:
            if result.get("unlimited"):
                print("OK - UNLIMITED (Claude Max)")
            elif result["ok"]:
                print(f"OK - ${result['remaining']:.2f} remaining")
            else:
                print(f"EXCEEDED - ${result['spent']:.2f} / ${result['budget']:.2f}")

        # Exit with code 1 if budget exceeded (for scripting)
        if not result["ok"]:
            if args.json:
                print(json.dumps(result, indent=2))
            sys.exit(1)

    elif args.pause:
        result = pause_tracking(args.reason)
        if not args.json:
            if result["success"]:
                print(f"Paused at {result['pausedAt']}")
            else:
                print(f"Failed: {result['message']}")

    elif args.resume:
        result = resume_tracking()
        if not args.json:
            if result["success"]:
                print("Resumed tracking")
            else:
                print(f"Failed: {result['message']}")
                sys.exit(1)

    elif args.reset:
        result = reset_tracking(args.confirm)
        if not args.json:
            if result["success"]:
                print(result["message"])
            else:
                print(result["message"])
                if not args.confirm:
                    sys.exit(1)

    elif args.transactions:
        result = get_recent_transactions(args.limit, args.pane)
        if not args.json:
            if not result:
                print("No transactions found.")
            else:
                print(f"{'ID':<5} {'Pane':<5} {'Service':<12} {'Amount':<10} {'Description':<30}")
                print("-" * 65)
                for t in result:
                    print(f"{t['id']:<5} {t['pane']:<5} {t['service']:<12} "
                          f"${t['amount']:<9.4f} {t.get('description', '')[:30]}")

    elif args.estimate:
        cost = estimate_cost(args.estimate)
        result = {"service": args.estimate, "estimated_cost": cost}
        if not args.json:
            print(f"Estimated cost for {args.estimate}: ${cost:.4f}")

    else:
        # Default: show status
        result = get_status()
        if not args.json:
            print(f"Budget: ${result['budget']:.2f} | "
                  f"Spent: ${result['spent']:.2f} | "
                  f"Remaining: ${result['remaining']:.2f}")
            if result["paused"]:
                print(f"⚠️  PAUSED: {result['pauseReason']}")

    if args.json and result:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
