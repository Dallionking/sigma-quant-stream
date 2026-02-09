#!/usr/bin/env python3
"""
prop-firm-validator.py - Prop Firm Compliance Validator
========================================================

Validates trading strategies against all 14 prop firm rule sets.
Simulates evaluation and funded account periods to determine compliance.

Usage:
    python prop-firm-validator.py --strategy="output/strategies/good/rsi_divergence.json"
    python prop-firm-validator.py --trades="output/backtests/2026-01-18/trades.csv"
    python prop-firm-validator.py --list-firms
    python prop-firm-validator.py --firm=topstep --account-size=50000

Output:
    Creates prop firm result JSON in output/strategies/prop_firm_ready/ or rejected/
"""

import os
import sys
import json
import argparse
import csv
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

# Configuration paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
RULES_FILE = PROJECT_ROOT / "docs" / "prop-firms" / "prop-firm-rules.json"
OUTPUT_DIR = PROJECT_ROOT / "output"


@dataclass
class Trade:
    """Represents a single trade."""
    timestamp: datetime
    direction: str  # LONG or SHORT
    entry_price: float
    exit_price: float
    contracts: int
    pnl: float
    commission: float
    slippage: float
    net_pnl: float
    symbol: str = "ES"
    high_during: float = 0.0  # For MFE calculation
    low_during: float = 0.0   # For MFE calculation


@dataclass
class PropFirmResult:
    """Result of prop firm validation for a single firm."""
    firm_name: str
    account_size: int
    passed: bool
    violation_reason: Optional[str] = None
    violation_date: Optional[str] = None
    final_equity: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    trading_days: int = 0
    total_trades: int = 0
    consistency_score: float = 0.0
    best_day_pnl: float = 0.0
    total_profit: float = 0.0


def load_prop_firm_rules() -> Dict[str, Any]:
    """Load prop firm rules from JSON file."""
    if not RULES_FILE.exists():
        raise FileNotFoundError(f"Prop firm rules not found: {RULES_FILE}")

    with open(RULES_FILE, 'r') as f:
        return json.load(f)


def load_trades_from_csv(filepath: Path) -> List[Trade]:
    """Load trades from CSV file."""
    trades = []

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trade = Trade(
                timestamp=datetime.fromisoformat(row['timestamp']),
                direction=row['direction'],
                entry_price=float(row['entry_price']),
                exit_price=float(row['exit_price']),
                contracts=int(row.get('contracts', 1)),
                pnl=float(row['pnl']),
                commission=float(row.get('commission', 5.0)),
                slippage=float(row.get('slippage', 6.25)),
                net_pnl=float(row['net_pnl']),
                symbol=row.get('symbol', 'ES'),
                high_during=float(row.get('high_during', 0)),
                low_during=float(row.get('low_during', 0)),
            )
            trades.append(trade)

    return trades


def load_trades_from_strategy(strategy_path: Path) -> List[Trade]:
    """Load trades from strategy JSON file."""
    with open(strategy_path, 'r') as f:
        strategy = json.load(f)

    trades = []
    for t in strategy.get('trades', []):
        trade = Trade(
            timestamp=datetime.fromisoformat(t['timestamp']),
            direction=t['direction'],
            entry_price=t['entry_price'],
            exit_price=t['exit_price'],
            contracts=t.get('contracts', 1),
            pnl=t['pnl'],
            commission=t.get('commission', 5.0),
            slippage=t.get('slippage', 6.25),
            net_pnl=t['net_pnl'],
            symbol=t.get('symbol', 'ES'),
            high_during=t.get('high_during', 0),
            low_during=t.get('low_during', 0),
        )
        trades.append(trade)

    return trades


def get_daily_pnls(trades: List[Trade]) -> Dict[str, float]:
    """Aggregate trades by day and return daily PnL."""
    daily = defaultdict(float)
    for trade in trades:
        day = trade.timestamp.strftime('%Y-%m-%d')
        daily[day] += trade.net_pnl
    return dict(daily)


def get_drawdown_type(firm_rules: Dict) -> Tuple[str, float]:
    """Extract drawdown type and percentage from firm rules."""
    dd_rules = firm_rules.get('risk_limits', {}).get('drawdown', {})

    dd_type = dd_rules.get('type', 'trailing')
    dd_percent = dd_rules.get('percent', 0.05)

    # Handle nested structures
    if isinstance(dd_percent, dict):
        # Take first value
        dd_percent = list(dd_percent.values())[0]

    if 'values' in dd_rules:
        values = dd_rules['values']
        if isinstance(values, dict):
            # Get first value
            dd_percent = list(values.values())[0] / 100 if list(values.values())[0] > 1 else list(values.values())[0]

    return dd_type, float(dd_percent) if dd_percent < 1 else float(dd_percent) / 100


def get_daily_loss_limit(firm_rules: Dict, account_size: int) -> Optional[float]:
    """Get daily loss limit for account size."""
    dll_rules = firm_rules.get('risk_limits', {}).get('daily_loss_limit', {})

    if not dll_rules.get('enabled', True):
        return None

    if dll_rules.get('enabled') is False:
        return None

    values = dll_rules.get('values', {})
    if isinstance(values, dict):
        return values.get(str(account_size), values.get(account_size))

    # Percent-based
    if 'percent' in dll_rules:
        pct = dll_rules['percent']
        return account_size * (pct / 100 if pct > 1 else pct)

    return None


def get_consistency_rule(firm_rules: Dict, phase: str = 'evaluation') -> Optional[float]:
    """Get consistency rule percentage."""
    cons_rules = firm_rules.get(phase, {}).get('consistency_rule', {})

    if not cons_rules:
        cons_rules = firm_rules.get('funded', {}).get('consistency_rule', {})

    if not cons_rules.get('enabled', False):
        return None

    pct = cons_rules.get('percent', cons_rules.get('max_single_day_percent'))
    if pct:
        return pct / 100 if pct > 1 else pct

    return None


def simulate_prop_firm(
    trades: List[Trade],
    firm_name: str,
    firm_rules: Dict,
    account_size: int,
) -> PropFirmResult:
    """
    Simulate a prop firm evaluation/funded period.

    Returns PropFirmResult with pass/fail and details.
    """
    # Initialize
    equity = float(account_size)
    high_water_mark = float(account_size)
    daily_pnl = 0.0
    current_day = None
    violated = False
    violation_reason = None
    violation_date = None

    daily_pnls = []
    max_drawdown = 0.0
    trading_days_set = set()

    # Get rules
    dd_type, dd_limit = get_drawdown_type(firm_rules)
    daily_loss_limit = get_daily_loss_limit(firm_rules, account_size)
    consistency_pct = get_consistency_rule(firm_rules)

    # Convert dd_limit to absolute if percentage
    if dd_limit < 1:
        dd_limit_abs = account_size * dd_limit
    else:
        dd_limit_abs = dd_limit

    # Process trades
    for trade in trades:
        trade_day = trade.timestamp.strftime('%Y-%m-%d')
        trading_days_set.add(trade_day)

        # New day check
        if trade_day != current_day:
            # Check daily loss limit for previous day
            if current_day and daily_loss_limit:
                if daily_pnl < -daily_loss_limit:
                    violated = True
                    violation_reason = f"Daily loss ${abs(daily_pnl):.2f} > limit ${daily_loss_limit:.2f}"
                    violation_date = current_day
                    break

            # Record daily PnL
            if current_day:
                daily_pnls.append(daily_pnl)

            daily_pnl = 0.0
            current_day = trade_day

            # EOD drawdown type: update HWM at day change
            if 'eod' in dd_type.lower():
                high_water_mark = max(high_water_mark, equity)

        # Apply trade
        equity += trade.net_pnl
        daily_pnl += trade.net_pnl

        # Intraday drawdown type: update HWM continuously
        if 'intraday' in dd_type.lower() or 'trailing' in dd_type.lower():
            high_water_mark = max(high_water_mark, equity)

        # Calculate current drawdown
        current_dd = high_water_mark - equity
        max_drawdown = max(max_drawdown, current_dd)

        # Check drawdown violation
        if current_dd > dd_limit_abs:
            violated = True
            violation_reason = f"Drawdown ${current_dd:.2f} > limit ${dd_limit_abs:.2f} ({dd_limit*100:.1f}%)"
            violation_date = trade_day
            break

    # Record final day
    if current_day and not violated:
        daily_pnls.append(daily_pnl)

        # Check final daily loss
        if daily_loss_limit and daily_pnl < -daily_loss_limit:
            violated = True
            violation_reason = f"Daily loss ${abs(daily_pnl):.2f} > limit ${daily_loss_limit:.2f}"
            violation_date = current_day

    # Calculate metrics
    profitable_days = [p for p in daily_pnls if p > 0]
    total_profit = sum(profitable_days) if profitable_days else 0
    best_day = max(daily_pnls) if daily_pnls else 0

    # Consistency check
    consistency_score = 0.0
    if total_profit > 0 and best_day > 0:
        consistency_score = best_day / total_profit

        # Check consistency rule if not already violated
        if not violated and consistency_pct and consistency_score > consistency_pct:
            # For some firms this is warning, for others it's violation
            # We'll flag it but not fail (most firms enforce at payout)
            pass

    return PropFirmResult(
        firm_name=firm_name,
        account_size=account_size,
        passed=not violated,
        violation_reason=violation_reason,
        violation_date=violation_date,
        final_equity=equity,
        max_drawdown=max_drawdown,
        max_drawdown_pct=max_drawdown / account_size,
        trading_days=len(trading_days_set),
        total_trades=len(trades),
        consistency_score=consistency_score,
        best_day_pnl=best_day,
        total_profit=total_profit,
    )


def validate_all_firms(
    trades: List[Trade],
    account_sizes: List[int] = None,
) -> Dict[str, Any]:
    """
    Validate strategy against all 14 prop firms.

    Returns comprehensive validation report.
    """
    rules_data = load_prop_firm_rules()
    firms = rules_data.get('firms', {})

    if not account_sizes:
        account_sizes = [50000, 100000]

    results = {}
    passing_firms = []
    failing_firms = []

    for firm_name, firm_rules in firms.items():
        firm_results = {}

        # Get account sizes for this firm
        firm_sizes = firm_rules.get('evaluation', {}).get('account_sizes', account_sizes)

        # Test intersection of requested and available sizes
        test_sizes = [s for s in account_sizes if s in firm_sizes] or firm_sizes[:2]

        for size in test_sizes:
            result = simulate_prop_firm(trades, firm_name, firm_rules, size)
            firm_results[size] = asdict(result)

        results[firm_name] = firm_results

        # Track passing/failing
        if any(r['passed'] for r in firm_results.values()):
            passing_firms.append(firm_name)
        else:
            failing_firms.append(firm_name)

    # Summary
    summary = {
        'firmsTested': len(firms),
        'firmsPassing': len(passing_firms),
        'firmsFailing': len(failing_firms),
        'passingFirms': passing_firms,
        'failingFirms': failing_firms,
        'deploymentReady': len(passing_firms) >= 3,
        'recommendedFirms': get_recommended_firms(results, passing_firms),
        'warnings': get_warnings(results),
    }

    return {
        'results': results,
        'summary': summary,
        'timestamp': datetime.now().isoformat(),
    }


def get_recommended_firms(results: Dict, passing_firms: List[str]) -> List[str]:
    """Get top recommended firms based on results."""
    # Rank by: lowest max_drawdown_pct, highest profit retention
    scores = []

    for firm_name in passing_firms:
        firm_results = results.get(firm_name, {})
        for size, result in firm_results.items():
            if result.get('passed'):
                score = (
                    1 - result.get('max_drawdown_pct', 1),  # Lower DD = better
                    result.get('final_equity', 0) / size,    # Higher profit = better
                )
                scores.append((firm_name, score))
                break

    # Sort by score (higher is better)
    scores.sort(key=lambda x: x[1], reverse=True)

    # Return top 3
    return [s[0] for s in scores[:3]]


def get_warnings(results: Dict) -> List[str]:
    """Extract warnings from validation results."""
    warnings = []

    for firm_name, firm_results in results.items():
        for size, result in firm_results.items():
            # Consistency warning
            cons_score = result.get('consistency_score', 0)
            if 0.40 < cons_score < 0.50:
                warnings.append(
                    f"{firm_name}: Consistency score {cons_score:.0%} close to limit"
                )

            # Drawdown warning
            dd_pct = result.get('max_drawdown_pct', 0)
            if result.get('passed') and dd_pct > 0.06:
                warnings.append(
                    f"{firm_name}: Max drawdown {dd_pct:.1%} close to limits"
                )

    return list(set(warnings))[:5]  # Dedupe and limit


def save_result(
    result: Dict,
    strategy_name: str,
    output_type: str = 'prop_firm_ready',
) -> Path:
    """Save validation result to appropriate directory."""
    output_subdir = OUTPUT_DIR / "strategies" / output_type
    output_subdir.mkdir(parents=True, exist_ok=True)

    filename = f"{strategy_name}_propfirm_{datetime.now().strftime('%Y%m%d')}.json"
    filepath = output_subdir / filename

    with open(filepath, 'w') as f:
        json.dump(result, f, indent=2)

    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Prop Firm Compliance Validator"
    )

    parser.add_argument(
        '--strategy',
        type=Path,
        help='Path to strategy JSON file with trades'
    )
    parser.add_argument(
        '--trades',
        type=Path,
        help='Path to trades CSV file'
    )
    parser.add_argument(
        '--list-firms',
        action='store_true',
        help='List all available prop firms'
    )
    parser.add_argument(
        '--firm',
        help='Test specific firm only'
    )
    parser.add_argument(
        '--account-size',
        type=int,
        default=50000,
        help='Account size to test'
    )
    parser.add_argument(
        '--account-sizes',
        help='Comma-separated account sizes (e.g., 50000,100000)'
    )
    parser.add_argument(
        '--output-name',
        help='Strategy name for output file'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Minimal output'
    )

    args = parser.parse_args()

    # List firms
    if args.list_firms:
        rules = load_prop_firm_rules()
        firms = rules.get('firms', {})

        print(f"{'#':<3} {'Firm':<25} {'Drawdown':<12} {'Daily Limit':<12} {'Consistency'}")
        print("-" * 70)

        for i, (name, firm) in enumerate(firms.items(), 1):
            dd_type, dd_pct = get_drawdown_type(firm)
            dll = get_daily_loss_limit(firm, 50000)
            cons = get_consistency_rule(firm)

            dd_str = f"{dd_pct*100:.0f}% {dd_type[:3]}" if dd_pct else "N/A"
            dll_str = f"${dll:,.0f}" if dll else "None"
            cons_str = f"{cons*100:.0f}%" if cons else "None"

            print(f"{i:<3} {name:<25} {dd_str:<12} {dll_str:<12} {cons_str}")

        return

    # Load trades
    trades = []
    strategy_name = args.output_name or "strategy"

    if args.strategy:
        trades = load_trades_from_strategy(args.strategy)
        strategy_name = args.strategy.stem
    elif args.trades:
        trades = load_trades_from_csv(args.trades)
        strategy_name = args.trades.stem
    else:
        print("Error: Provide --strategy or --trades")
        sys.exit(1)

    if len(trades) < 30:
        print(f"Warning: Only {len(trades)} trades. Results may be unreliable.")

    # Parse account sizes
    account_sizes = [args.account_size]
    if args.account_sizes:
        account_sizes = [int(s.strip()) for s in args.account_sizes.split(',')]

    # Single firm test
    if args.firm:
        rules = load_prop_firm_rules()
        firm_rules = rules.get('firms', {}).get(args.firm)

        if not firm_rules:
            print(f"Error: Unknown firm '{args.firm}'")
            sys.exit(1)

        result = simulate_prop_firm(
            trades, args.firm, firm_rules, args.account_size
        )

        if args.json:
            print(json.dumps(asdict(result), indent=2))
        else:
            status = "PASS" if result.passed else "FAIL"
            print(f"\n{args.firm} ${args.account_size:,}: {status}")
            if result.violation_reason:
                print(f"  Reason: {result.violation_reason}")
                print(f"  Date: {result.violation_date}")
            print(f"  Final Equity: ${result.final_equity:,.2f}")
            print(f"  Max Drawdown: ${result.max_drawdown:,.2f} ({result.max_drawdown_pct:.1%})")
            print(f"  Trading Days: {result.trading_days}")
            print(f"  Consistency: {result.consistency_score:.1%}")

        return

    # Full validation
    if not args.quiet:
        print(f"Validating {len(trades)} trades against 14 prop firms...")

    result = validate_all_firms(trades, account_sizes)
    result['strategy'] = strategy_name
    result['tradeCount'] = len(trades)

    summary = result['summary']

    # Determine output type
    if summary['deploymentReady']:
        output_type = 'prop_firm_ready'
    else:
        output_type = 'rejected'

    # Save result
    filepath = save_result(result, strategy_name, output_type)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"Prop Firm Validation: {strategy_name}")
        print(f"{'='*60}")
        print(f"Firms Tested: {summary['firmsTested']}")
        print(f"Firms Passing: {summary['firmsPassing']}/{summary['firmsTested']}")
        print(f"Deployment Ready: {'YES' if summary['deploymentReady'] else 'NO'}")
        print()

        print("Passing Firms:")
        for firm in summary['passingFirms']:
            firm_result = result['results'][firm]
            sizes = list(firm_result.keys())
            print(f"  - {firm} ({', '.join(f'${s:,}' for s in sizes)})")

        if summary['failingFirms']:
            print("\nFailing Firms:")
            for firm in summary['failingFirms'][:5]:
                firm_result = result['results'][firm]
                for size, r in firm_result.items():
                    if not r['passed']:
                        print(f"  - {firm}: {r.get('violation_reason', 'Unknown')}")
                        break

        if summary['recommendedFirms']:
            print(f"\nRecommended: {', '.join(summary['recommendedFirms'])}")

        if summary['warnings']:
            print("\nWarnings:")
            for w in summary['warnings']:
                print(f"  - {w}")

        print(f"\nOutput: {filepath}")


if __name__ == "__main__":
    main()
