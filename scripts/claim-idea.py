#!/usr/bin/env python3
"""
claim-idea.py - Idea Claiming System with File Locking
=======================================================

Prevents duplicate work across panes by maintaining a global registry
of claimed ideas with file locking.

Usage:
    python claim-idea.py --pane=1 --idea="RSI divergence strategy"
    python claim-idea.py --pane=2 --check="VWAP bounce strategy"
    python claim-idea.py --list
    python claim-idea.py --release --idea="Abandoned strategy"

The script uses file locking (fcntl.flock) to prevent race conditions
when multiple panes try to claim the same idea simultaneously.
"""

import os
import sys
import json
import argparse
import fcntl
import hashlib
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

# Configuration
SCRIPT_DIR = Path(__file__).parent
STREAM_QUANT_DIR = SCRIPT_DIR.parent.parent / "stream-quant"
CLAIMS_FILE = STREAM_QUANT_DIR / "claimed-ideas.json"


def normalize_idea(idea: str) -> str:
    """Normalize idea string for comparison."""
    # Lowercase, remove extra whitespace, strip punctuation
    normalized = " ".join(idea.lower().split())
    return normalized


def get_idea_hash(idea: str) -> str:
    """Get a short hash of the idea for quick comparison."""
    normalized = normalize_idea(idea)
    # Use SHA256 instead of deprecated MD5
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]


def load_claims() -> Dict[str, Any]:
    """Load claims file, creating if it doesn't exist."""
    if not CLAIMS_FILE.exists():
        CLAIMS_FILE.parent.mkdir(parents=True, exist_ok=True)
        initial = {
            "version": "1.0.0",
            "description": "Global registry of claimed ideas",
            "lastUpdated": None,
            "claims": []
        }
        save_claims(initial)
        return initial

    with open(CLAIMS_FILE, 'r') as f:
        return json.load(f)


def save_claims(data: Dict[str, Any]) -> None:
    """Save claims file."""
    data["lastUpdated"] = datetime.now().isoformat()
    with open(CLAIMS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


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


def find_claim(claims: List[Dict], idea: str) -> Optional[Dict]:
    """Find a claim by idea (normalized comparison)."""
    normalized = normalize_idea(idea)
    idea_hash = get_idea_hash(idea)

    for claim in claims:
        # Check by hash first (fast)
        if claim.get("ideaHash") == idea_hash:
            return claim
        # Fallback to normalized comparison
        if normalize_idea(claim.get("idea", "")) == normalized:
            return claim

    return None


def claim_idea(pane: int, idea: str, force: bool = False) -> Dict[str, Any]:
    """
    Claim an idea for a pane.

    Returns:
        Dict with 'success', 'message', and optionally 'claim' or 'existing_claim'
    """
    # Ensure directory exists
    CLAIMS_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Ensure file exists before using 'r+' mode
    if not CLAIMS_FILE.exists():
        save_claims(load_claims())

    # Open file with locking
    with open(CLAIMS_FILE, 'r+') as f:
        # Try to acquire lock (with timeout retry)
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
                data = {
                    "version": "1.0.0",
                    "description": "Global registry of claimed ideas",
                    "lastUpdated": None,
                    "claims": []
                }

            # Check if already claimed
            existing = find_claim(data["claims"], idea)
            if existing:
                if existing.get("status") == "completed":
                    return {
                        "success": False,
                        "message": f"Idea already completed by pane {existing['pane']}",
                        "existing_claim": existing
                    }
                elif existing.get("status") == "in_progress":
                    if force:
                        # Force re-claim (steal from other pane)
                        existing["pane"] = pane
                        existing["claimedAt"] = datetime.now().isoformat()
                        existing["status"] = "in_progress"
                        existing["forceClaimed"] = True
                    else:
                        return {
                            "success": False,
                            "message": f"Idea already claimed by pane {existing['pane']}",
                            "existing_claim": existing
                        }
                elif existing.get("status") == "rejected":
                    # Allow re-claiming rejected ideas
                    existing["pane"] = pane
                    existing["claimedAt"] = datetime.now().isoformat()
                    existing["status"] = "in_progress"
                    existing["reclaimedFrom"] = "rejected"
                else:
                    # Update existing claim
                    existing["pane"] = pane
                    existing["claimedAt"] = datetime.now().isoformat()
                    existing["status"] = "in_progress"
            else:
                # Create new claim
                new_claim = {
                    "idea": idea,
                    "ideaHash": get_idea_hash(idea),
                    "pane": pane,
                    "claimedAt": datetime.now().isoformat(),
                    "status": "in_progress"
                }
                data["claims"].append(new_claim)
                existing = new_claim

            # Write updated data
            data["lastUpdated"] = datetime.now().isoformat()
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)

            return {
                "success": True,
                "message": f"Idea claimed by pane {pane}",
                "claim": existing
            }

        finally:
            release_lock(f)


def check_idea(idea: str) -> Dict[str, Any]:
    """Check if an idea is already claimed."""
    data = load_claims()
    existing = find_claim(data["claims"], idea)

    if existing:
        return {
            "claimed": True,
            "claim": existing
        }
    return {
        "claimed": False
    }


def update_claim_status(idea: str, status: str, result: Optional[Dict] = None) -> Dict[str, Any]:
    """Update the status of a claim."""
    # Ensure file exists before using 'r+' mode
    if not CLAIMS_FILE.exists():
        save_claims(load_claims())

    with open(CLAIMS_FILE, 'r+') as f:
        if not acquire_lock(f):
            return {"success": False, "message": "Could not acquire lock"}

        try:
            f.seek(0)
            data = json.load(f)

            existing = find_claim(data["claims"], idea)
            if not existing:
                return {"success": False, "message": "Claim not found"}

            existing["status"] = status
            existing["updatedAt"] = datetime.now().isoformat()
            if result:
                existing["result"] = result

            data["lastUpdated"] = datetime.now().isoformat()
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)

            return {"success": True, "claim": existing}

        finally:
            release_lock(f)


def release_claim(idea: str) -> Dict[str, Any]:
    """Release a claim (mark as available)."""
    return update_claim_status(idea, "released")


def complete_claim(idea: str, result: Optional[Dict] = None) -> Dict[str, Any]:
    """Mark a claim as completed."""
    return update_claim_status(idea, "completed", result)


def reject_claim(idea: str, reason: str) -> Dict[str, Any]:
    """Mark a claim as rejected."""
    return update_claim_status(idea, "rejected", {"reason": reason})


def list_claims(status: Optional[str] = None) -> List[Dict]:
    """List all claims, optionally filtered by status."""
    data = load_claims()
    claims = data["claims"]

    if status:
        claims = [c for c in claims if c.get("status") == status]

    return claims


def cleanup_stale_claims(max_age_hours: int = 24) -> Dict[str, Any]:
    """Release claims that have been in_progress for too long."""
    from datetime import timedelta

    # Ensure file exists before using 'r+' mode
    if not CLAIMS_FILE.exists():
        save_claims(load_claims())

    with open(CLAIMS_FILE, 'r+') as f:
        if not acquire_lock(f):
            return {"success": False, "message": "Could not acquire lock"}

        try:
            f.seek(0)
            data = json.load(f)

            released = []
            cutoff = datetime.now() - timedelta(hours=max_age_hours)

            for claim in data["claims"]:
                if claim.get("status") == "in_progress":
                    claimed_at = datetime.fromisoformat(claim["claimedAt"])
                    if claimed_at < cutoff:
                        claim["status"] = "stale"
                        claim["releasedAt"] = datetime.now().isoformat()
                        released.append(claim["idea"])

            data["lastUpdated"] = datetime.now().isoformat()
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)

            return {
                "success": True,
                "released": released,
                "count": len(released)
            }

        finally:
            release_lock(f)


def main():
    parser = argparse.ArgumentParser(
        description="Idea Claiming System for Quant Research Team"
    )

    parser.add_argument("--pane", type=int, help="Pane number claiming the idea")
    parser.add_argument("--idea", help="Idea to claim/check/release")
    parser.add_argument("--check", help="Check if idea is claimed (doesn't claim)")
    parser.add_argument("--list", action="store_true", help="List all claims")
    parser.add_argument("--status", choices=["in_progress", "completed", "rejected", "released", "stale"],
                        help="Filter list by status")
    parser.add_argument("--release", action="store_true", help="Release a claim")
    parser.add_argument("--complete", action="store_true", help="Mark claim as completed")
    parser.add_argument("--reject", help="Mark claim as rejected with reason")
    parser.add_argument("--force", action="store_true", help="Force claim even if already taken")
    parser.add_argument("--cleanup", type=int, metavar="HOURS",
                        help="Release claims older than N hours")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    result = None

    if args.list:
        result = list_claims(args.status)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if not result:
                print("No claims found.")
            else:
                print(f"{'Idea':<50} {'Pane':<6} {'Status':<12} {'Claimed At':<20}")
                print("-" * 90)
                for claim in result:
                    idea = claim.get("idea", "")[:48]
                    print(f"{idea:<50} {claim.get('pane', '?'):<6} "
                          f"{claim.get('status', '?'):<12} {claim.get('claimedAt', '?')[:19]}")

    elif args.cleanup:
        result = cleanup_stale_claims(args.cleanup)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Released {result['count']} stale claims")

    elif args.check:
        result = check_idea(args.check)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["claimed"]:
                claim = result["claim"]
                print(f"CLAIMED by pane {claim['pane']} ({claim['status']})")
            else:
                print("AVAILABLE")

    elif args.release and args.idea:
        result = release_claim(args.idea)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(result["message"] if not result["success"] else "Released")

    elif args.complete and args.idea:
        result = complete_claim(args.idea)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(result["message"] if not result["success"] else "Completed")

    elif args.reject and args.idea:
        result = reject_claim(args.idea, args.reject)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(result["message"] if not result["success"] else "Rejected")

    elif args.pane and args.idea:
        result = claim_idea(args.pane, args.idea, args.force)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(f"SUCCESS: {result['message']}")
                sys.exit(0)
            else:
                print(f"FAILED: {result['message']}")
                sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
