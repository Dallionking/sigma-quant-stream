#!/usr/bin/env python3
"""
Standalone vectorized backtest runner for SigmaQuantStream.

Provides a CLI tool that backtester workers can invoke to run strategies
against OHLCV data with realistic cost models for futures and crypto.

Usage::

    python lib/backtest_runner.py \
      --strategy path/to/strategy.py \
      --data path/to/data.csv \
      --cost-model '{"type": "futures", "commission_per_side": 2.50, "slippage_ticks": 0.5, "tick_value": 12.50}' \
      --output results.json

Walk-forward mode::

    python lib/backtest_runner.py \
      --strategy path/to/strategy.py \
      --data path/to/data.csv \
      --walk-forward '{"train_bars": 10000, "test_bars": 2000, "step_bars": 2000}' \
      --cost-model '{"type": "futures", "commission_per_side": 2.50, "slippage_ticks": 0.5, "tick_value": 12.50}' \
      --output wfo_results.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cost models
# ---------------------------------------------------------------------------

DEFAULT_FUTURES_COST = {
    "type": "futures",
    "commission_per_side": 2.50,
    "slippage_ticks": 0.5,
    "tick_value": 12.50,
}

DEFAULT_CRYPTO_CEX_COST = {
    "type": "crypto_cex",
    "maker_fee": 0.0002,
    "taker_fee": 0.0005,
    "slippage_pct": 0.0005,
}

DEFAULT_CRYPTO_DEX_COST = {
    "type": "crypto_dex",
    "maker_fee": 0.0002,
    "taker_fee": 0.0005,
    "gas_per_trade": 0.50,
    "slippage_pct": 0.001,
}


def compute_round_trip_cost(cost_model: dict, notional: float) -> float:
    """Compute round-trip cost in dollar terms for a single trade.

    Args:
        cost_model: Cost model dict with 'type' key.
        notional: Absolute notional value of the trade (price * quantity).

    Returns:
        Total round-trip cost in dollars.
    """
    cm_type = cost_model.get("type", "futures")

    if cm_type == "futures":
        commission = cost_model.get("commission_per_side", 2.50)
        slippage_ticks = cost_model.get("slippage_ticks", 0.5)
        tick_value = cost_model.get("tick_value", 12.50)
        return 2 * commission + 2 * slippage_ticks * tick_value

    if cm_type == "crypto_cex":
        maker = cost_model.get("maker_fee", 0.0002)
        taker = cost_model.get("taker_fee", 0.0005)
        slip = cost_model.get("slippage_pct", 0.0005)
        return (maker + taker + 2 * slip) * notional

    if cm_type == "crypto_dex":
        maker = cost_model.get("maker_fee", 0.0002)
        taker = cost_model.get("taker_fee", 0.0005)
        gas = cost_model.get("gas_per_trade", 0.50)
        slip = cost_model.get("slippage_pct", 0.001)
        return (maker + taker + 2 * slip) * notional + 2 * gas

    raise ValueError(f"Unknown cost model type: {cm_type}")


# ---------------------------------------------------------------------------
# Strategy loader
# ---------------------------------------------------------------------------


def load_strategy(strategy_path: str, params: dict | None = None) -> Any:
    """Dynamically load a Strategy class from a Python file.

    The file must define a ``Strategy`` class with ``indicators()``,
    ``signals()``, and ``default_params()`` methods.
    """
    path = Path(strategy_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Strategy file not found: {path}")

    spec = importlib.util.spec_from_file_location("strategy_module", str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load strategy module from {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "Strategy"):
        raise AttributeError(
            f"Strategy file {path} must define a 'Strategy' class"
        )

    strategy_cls = module.Strategy
    init_params = params if params is not None else {}
    try:
        strategy = strategy_cls(params=init_params) if init_params else strategy_cls()
    except TypeError:
        strategy = strategy_cls(init_params)

    # Fill in defaults if params were not provided
    if not init_params and hasattr(strategy, "default_params"):
        defaults = strategy.default_params()
        if defaults:
            strategy.params = defaults

    return strategy


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_data(data_path: str, start_bar: int = 0, end_bar: int = -1) -> pd.DataFrame:
    """Load OHLCV data from CSV.

    Auto-detects column naming conventions:
    - Standard: timestamp/datetime, open, high, low, close, volume
    - Databento: ts_event, open, high, low, close, volume
    - CCXT: timestamp, open, high, low, close, volume (unix ms)
    """
    df = pd.read_csv(data_path)

    # Normalize column names to lowercase
    df.columns = [c.strip().lower() for c in df.columns]

    # Rename common variants
    rename_map = {}
    if "ts_event" in df.columns:
        rename_map["ts_event"] = "timestamp"
    if "datetime" in df.columns and "timestamp" not in df.columns:
        rename_map["datetime"] = "timestamp"
    if "date" in df.columns and "timestamp" not in df.columns:
        rename_map["date"] = "timestamp"
    if rename_map:
        df = df.rename(columns=rename_map)

    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Data CSV missing required columns: {missing}")

    if "volume" not in df.columns:
        df["volume"] = 0.0

    # Parse timestamp if present
    if "timestamp" in df.columns:
        ts_col = df["timestamp"]
        if ts_col.dtype in ("int64", "float64"):
            # Unix seconds vs milliseconds
            sample = ts_col.iloc[0]
            if sample > 1e12:
                df["timestamp"] = pd.to_datetime(ts_col, unit="ms", utc=True)
            else:
                df["timestamp"] = pd.to_datetime(ts_col, unit="s", utc=True)
        else:
            df["timestamp"] = pd.to_datetime(ts_col, utc=True)

    # Slice bars
    if end_bar == -1:
        df = df.iloc[start_bar:]
    else:
        df = df.iloc[start_bar:end_bar]

    df = df.reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Trade simulation
# ---------------------------------------------------------------------------


@dataclass
class Trade:
    entry_bar: int
    exit_bar: int
    side: str  # "long" or "short"
    entry_price: float
    exit_price: float
    pnl: float
    mfe: float  # max favorable excursion
    mae: float  # max adverse excursion (negative)


def simulate_trades(
    df: pd.DataFrame,
    cost_model: dict,
) -> list[Trade]:
    """Vectorized trade simulation from signal column.

    Enters at next bar's open on signal change, exits on reversal.
    Tracks MFE and MAE for each trade.
    """
    if "signal" not in df.columns:
        raise ValueError("DataFrame must have a 'signal' column after strategy.signals()")

    signals = df["signal"].values
    opens = df["open"].values
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values

    trades: list[Trade] = []
    n = len(df)

    position = 0  # 0=flat, 1=long, -1=short
    entry_bar = 0
    entry_price = 0.0
    running_mfe = 0.0
    running_mae = 0.0

    for i in range(1, n):
        sig = signals[i - 1]  # signal from previous bar determines action on this bar

        # Check for signal change
        if sig != position:
            # Close existing position
            if position != 0:
                exit_price = opens[i]
                if position == 1:
                    raw_pnl = exit_price - entry_price
                else:
                    raw_pnl = entry_price - exit_price

                notional = abs(entry_price)
                rt_cost = compute_round_trip_cost(cost_model, notional)
                net_pnl = raw_pnl - rt_cost

                trades.append(Trade(
                    entry_bar=entry_bar,
                    exit_bar=i,
                    side="long" if position == 1 else "short",
                    entry_price=entry_price,
                    exit_price=exit_price,
                    pnl=net_pnl,
                    mfe=running_mfe,
                    mae=running_mae,
                ))

            # Open new position
            if sig != 0:
                position = sig
                entry_bar = i
                entry_price = opens[i]
                running_mfe = 0.0
                running_mae = 0.0
            else:
                position = 0

        # Update MFE / MAE for open position
        if position != 0:
            if position == 1:
                excursion_high = highs[i] - entry_price
                excursion_low = lows[i] - entry_price
            else:
                excursion_high = entry_price - lows[i]
                excursion_low = entry_price - highs[i]

            running_mfe = max(running_mfe, excursion_high)
            running_mae = min(running_mae, excursion_low)

    # Close any open position at the last bar's close
    if position != 0:
        exit_price = closes[-1]
        if position == 1:
            raw_pnl = exit_price - entry_price
        else:
            raw_pnl = entry_price - exit_price

        notional = abs(entry_price)
        rt_cost = compute_round_trip_cost(cost_model, notional)
        net_pnl = raw_pnl - rt_cost

        trades.append(Trade(
            entry_bar=entry_bar,
            exit_bar=n - 1,
            side="long" if position == 1 else "short",
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=net_pnl,
            mfe=running_mfe,
            mae=running_mae,
        ))

    return trades


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------


@dataclass
class BacktestMetrics:
    total_pnl: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_dollars: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    avg_trade_pnl: float = 0.0
    avg_winner: float = 0.0
    avg_loser: float = 0.0
    max_consecutive_losses: int = 0
    avg_holding_bars: float = 0.0
    expectancy: float = 0.0
    calmar_ratio: float = 0.0


def compute_metrics(trades: list[Trade]) -> BacktestMetrics:
    """Compute performance metrics from a list of trades."""
    if not trades:
        return BacktestMetrics()

    pnls = np.array([t.pnl for t in trades])
    total_pnl = float(pnls.sum())
    total_trades = len(trades)

    winners = pnls[pnls > 0]
    losers = pnls[pnls < 0]

    win_rate = len(winners) / total_trades if total_trades > 0 else 0.0
    avg_trade_pnl = float(pnls.mean()) if total_trades > 0 else 0.0
    avg_winner = float(winners.mean()) if len(winners) > 0 else 0.0
    avg_loser = float(losers.mean()) if len(losers) > 0 else 0.0

    gross_profit = float(winners.sum()) if len(winners) > 0 else 0.0
    gross_loss = abs(float(losers.sum())) if len(losers) > 0 else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Sharpe (annualized, assuming ~252 trading days)
    if total_trades > 1 and pnls.std() > 0:
        sharpe_ratio = float((pnls.mean() / pnls.std()) * math.sqrt(252))
    else:
        sharpe_ratio = 0.0

    # Max drawdown from equity curve
    equity = np.cumsum(pnls)
    running_max = np.maximum.accumulate(equity)
    drawdowns = running_max - equity
    max_dd_dollars = float(drawdowns.max()) if len(drawdowns) > 0 else 0.0
    peak = float(running_max.max()) if len(running_max) > 0 else 0.0
    max_dd_pct = max_dd_dollars / peak if peak > 0 else 0.0

    # Max consecutive losses
    max_consec = 0
    current_consec = 0
    for p in pnls:
        if p < 0:
            current_consec += 1
            max_consec = max(max_consec, current_consec)
        else:
            current_consec = 0

    # Average holding period
    holding_bars = [t.exit_bar - t.entry_bar for t in trades]
    avg_holding = float(np.mean(holding_bars)) if holding_bars else 0.0

    # Calmar ratio (annual return / max drawdown)
    calmar = abs(total_pnl / max_dd_dollars) if max_dd_dollars > 0 else 0.0

    return BacktestMetrics(
        total_pnl=round(total_pnl, 2),
        sharpe_ratio=round(sharpe_ratio, 4),
        max_drawdown=round(max_dd_pct, 4),
        max_drawdown_dollars=round(max_dd_dollars, 2),
        win_rate=round(win_rate, 4),
        profit_factor=round(profit_factor, 4),
        total_trades=total_trades,
        avg_trade_pnl=round(avg_trade_pnl, 2),
        avg_winner=round(avg_winner, 2),
        avg_loser=round(avg_loser, 2),
        max_consecutive_losses=max_consec,
        avg_holding_bars=round(avg_holding, 2),
        expectancy=round(avg_trade_pnl, 2),
        calmar_ratio=round(calmar, 4),
    )


# ---------------------------------------------------------------------------
# Monthly returns
# ---------------------------------------------------------------------------


def compute_monthly_returns(
    trades: list[Trade], df: pd.DataFrame
) -> list[dict]:
    """Compute monthly PnL from trades using the dataframe timestamps."""
    if not trades or "timestamp" not in df.columns:
        return []

    monthly: dict[str, float] = {}
    for t in trades:
        # Use exit bar timestamp for month attribution
        idx = min(t.exit_bar, len(df) - 1)
        ts = df["timestamp"].iloc[idx]
        key = ts.strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0.0) + t.pnl

    return [{"month": k, "pnl": round(v, 2)} for k, v in sorted(monthly.items())]


# ---------------------------------------------------------------------------
# Equity curve (sampled)
# ---------------------------------------------------------------------------


def compute_equity_curve(
    trades: list[Trade], total_bars: int, sample_every: int = 100
) -> list[dict]:
    """Build a sampled equity curve from trade list."""
    # Build bar-level PnL attribution
    bar_pnl = np.zeros(total_bars)
    for t in trades:
        if t.exit_bar < total_bars:
            bar_pnl[t.exit_bar] += t.pnl

    equity = np.cumsum(bar_pnl)
    points = []
    for i in range(0, total_bars, sample_every):
        points.append({"bar": int(i), "equity": round(float(equity[i]), 2)})
    # Always include the last bar
    if total_bars > 0 and (total_bars - 1) % sample_every != 0:
        points.append({
            "bar": total_bars - 1,
            "equity": round(float(equity[-1]), 2),
        })
    return points


# ---------------------------------------------------------------------------
# Anti-overfit flags and grading
# ---------------------------------------------------------------------------


@dataclass
class AntiOverfitFlags:
    sharpe_above_3: bool = False
    win_rate_above_80: bool = False
    trades_below_100: bool = False
    no_losing_months: bool = False


def check_overfit_flags(
    metrics: BacktestMetrics, monthly_returns: list[dict]
) -> AntiOverfitFlags:
    flags = AntiOverfitFlags()
    flags.sharpe_above_3 = metrics.sharpe_ratio > 3.0
    flags.win_rate_above_80 = metrics.win_rate > 0.80
    flags.trades_below_100 = metrics.total_trades < 100
    if monthly_returns:
        losing_months = sum(1 for m in monthly_returns if m["pnl"] < 0)
        flags.no_losing_months = losing_months == 0 and len(monthly_returns) > 3
    return flags


def grade_result(
    metrics: BacktestMetrics, flags: AntiOverfitFlags
) -> tuple[bool, str]:
    """Grade the backtest result.

    Returns:
        (pass_bool, grade_string) where grade is "good", "under_review", or "rejected".
    """
    # REJECT conditions
    if flags.sharpe_above_3:
        return False, "rejected"
    if flags.win_rate_above_80:
        return False, "rejected"
    if metrics.total_trades < 30:
        return False, "rejected"
    if flags.no_losing_months:
        return False, "rejected"

    # UNDER_REVIEW conditions
    if 1.0 <= metrics.sharpe_ratio <= 1.5:
        return True, "under_review"
    if metrics.max_drawdown > 0.15:
        return True, "under_review"
    if 30 <= metrics.total_trades <= 100:
        return True, "under_review"

    # GOOD conditions
    if (
        1.5 < metrics.sharpe_ratio <= 3.0
        and metrics.max_drawdown <= 0.15
        and metrics.total_trades > 100
        and metrics.win_rate <= 0.80
    ):
        return True, "good"

    # Default to under_review if none of the clear buckets match
    return True, "under_review"


# ---------------------------------------------------------------------------
# Walk-forward optimization
# ---------------------------------------------------------------------------


def run_walk_forward(
    strategy_path: str,
    df: pd.DataFrame,
    cost_model: dict,
    wf_config: dict,
    params: dict | None = None,
) -> dict:
    """Run walk-forward analysis with rolling train/test windows.

    Args:
        strategy_path: Path to strategy .py file.
        df: Full OHLCV dataframe.
        cost_model: Cost model dict.
        wf_config: Dict with train_bars, test_bars, step_bars.
        params: Optional strategy parameters.

    Returns:
        Walk-forward results dict with per-fold and aggregate metrics.
    """
    train_bars = wf_config["train_bars"]
    test_bars = wf_config["test_bars"]
    step_bars = wf_config.get("step_bars", test_bars)
    total_bars = len(df)

    folds = []
    fold_num = 0
    start = 0

    while start + train_bars + test_bars <= total_bars:
        fold_num += 1
        train_start = start
        train_end = start + train_bars
        test_start = train_end
        test_end = min(train_end + test_bars, total_bars)

        # In-sample (train)
        train_df = df.iloc[train_start:train_end].copy().reset_index(drop=True)
        strategy_is = load_strategy(strategy_path, params)
        train_df = strategy_is.indicators(train_df)
        train_df = strategy_is.signals(train_df)
        is_trades = simulate_trades(train_df, cost_model)
        is_metrics = compute_metrics(is_trades)

        # Out-of-sample (test)
        test_df = df.iloc[test_start:test_end].copy().reset_index(drop=True)
        strategy_oos = load_strategy(strategy_path, params)
        test_df = strategy_oos.indicators(test_df)
        test_df = strategy_oos.signals(test_df)
        oos_trades = simulate_trades(test_df, cost_model)
        oos_metrics = compute_metrics(oos_trades)

        # OOS decay
        if is_metrics.sharpe_ratio != 0:
            oos_decay = 1.0 - (oos_metrics.sharpe_ratio / is_metrics.sharpe_ratio)
        else:
            oos_decay = 0.0

        folds.append({
            "fold": fold_num,
            "train_range": [train_start, train_end],
            "test_range": [test_start, test_end],
            "in_sample": asdict(is_metrics),
            "out_of_sample": asdict(oos_metrics),
            "oos_decay_pct": round(oos_decay * 100, 2),
        })

        start += step_bars

    # Aggregate OOS metrics
    all_oos_sharpes = [f["out_of_sample"]["sharpe_ratio"] for f in folds]
    all_oos_pnls = [f["out_of_sample"]["total_pnl"] for f in folds]
    all_decay = [f["oos_decay_pct"] for f in folds]

    return {
        "mode": "walk_forward",
        "config": wf_config,
        "total_folds": len(folds),
        "folds": folds,
        "aggregate": {
            "avg_oos_sharpe": round(float(np.mean(all_oos_sharpes)), 4) if all_oos_sharpes else 0.0,
            "avg_oos_pnl": round(float(np.mean(all_oos_pnls)), 2) if all_oos_pnls else 0.0,
            "total_oos_pnl": round(float(np.sum(all_oos_pnls)), 2) if all_oos_pnls else 0.0,
            "avg_oos_decay_pct": round(float(np.mean(all_decay)), 2) if all_decay else 0.0,
            "max_oos_decay_pct": round(float(np.max(all_decay)), 2) if all_decay else 0.0,
        },
    }


# ---------------------------------------------------------------------------
# Main backtest runner
# ---------------------------------------------------------------------------


def run_backtest(
    strategy_path: str,
    data_path: str,
    cost_model: dict,
    start_bar: int = 0,
    end_bar: int = -1,
    params: dict | None = None,
) -> dict:
    """Run a full backtest and return results as a dict.

    This is the main entry point for programmatic use.
    """
    # Load data
    df = load_data(data_path, start_bar, end_bar)
    total_bars = len(df)

    # Load and run strategy
    strategy = load_strategy(strategy_path, params)
    strategy_name = getattr(strategy, "name", Path(strategy_path).stem)

    df = strategy.indicators(df)
    df = strategy.signals(df)

    # Simulate trades
    trades = simulate_trades(df, cost_model)

    # Compute metrics
    metrics = compute_metrics(trades)

    # Monthly returns
    monthly_returns = compute_monthly_returns(trades, df)

    # Equity curve (sample every ~1% of total bars, min 10)
    sample_interval = max(10, total_bars // 100)
    equity_curve = compute_equity_curve(trades, total_bars, sample_interval)

    # Trade log
    trade_log = [
        {
            "entry_bar": t.entry_bar,
            "exit_bar": t.exit_bar,
            "side": t.side,
            "entry_price": round(t.entry_price, 4),
            "exit_price": round(t.exit_price, 4),
            "pnl": round(t.pnl, 2),
            "mfe": round(t.mfe, 2),
            "mae": round(t.mae, 2),
        }
        for t in trades
    ]

    # Date range
    date_range = {}
    if "timestamp" in df.columns and len(df) > 0:
        date_range = {
            "start": str(df["timestamp"].iloc[0].date()),
            "end": str(df["timestamp"].iloc[-1].date()),
        }

    # Anti-overfit checks
    flags = check_overfit_flags(metrics, monthly_returns)
    passed, grade = grade_result(metrics, flags)

    return {
        "strategy_name": strategy_name,
        "data_file": str(data_path),
        "bars_tested": total_bars,
        "date_range": date_range,
        "cost_model": cost_model,
        "metrics": asdict(metrics),
        "monthly_returns": monthly_returns,
        "equity_curve": equity_curve,
        "trade_log": trade_log,
        "anti_overfit_flags": asdict(flags),
        "pass": passed,
        "grade": grade,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SigmaQuantStream Backtest Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic backtest with futures cost model
  python lib/backtest_runner.py \\
    --strategy seed/sample_strategy.py \\
    --data data/samples/ES_5min_sample.csv \\
    --cost-model '{"type": "futures", "commission_per_side": 2.50, "slippage_ticks": 0.5, "tick_value": 12.50}'

  # Walk-forward analysis
  python lib/backtest_runner.py \\
    --strategy seed/sample_strategy.py \\
    --data data/samples/ES_5min_sample.csv \\
    --walk-forward '{"train_bars": 300, "test_bars": 100, "step_bars": 100}' \\
    --cost-model '{"type": "futures", "commission_per_side": 2.50, "slippage_ticks": 0.5, "tick_value": 12.50}'
        """,
    )
    parser.add_argument(
        "--strategy",
        required=True,
        help="Path to strategy .py file defining a Strategy class",
    )
    parser.add_argument(
        "--data",
        required=True,
        help="Path to OHLCV CSV data file",
    )
    parser.add_argument(
        "--cost-model",
        type=str,
        default=None,
        help="JSON string with cost model parameters",
    )
    parser.add_argument(
        "--start-bar",
        type=int,
        default=0,
        help="Starting bar index (default: 0)",
    )
    parser.add_argument(
        "--end-bar",
        type=int,
        default=-1,
        help="Ending bar index (default: -1 = all)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path for JSON results (default: stdout)",
    )
    parser.add_argument(
        "--walk-forward",
        type=str,
        default=None,
        help='JSON walk-forward config: {"train_bars": N, "test_bars": M, "step_bars": S}',
    )
    parser.add_argument(
        "--params",
        type=str,
        default=None,
        help="JSON string with strategy parameters override",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Parse cost model
    if args.cost_model:
        try:
            cost_model = json.loads(args.cost_model)
        except json.JSONDecodeError as e:
            logger.error("Invalid --cost-model JSON: %s", e)
            print(f"Error: Invalid --cost-model JSON: {e}", file=sys.stderr)
            return 1
    else:
        cost_model = DEFAULT_FUTURES_COST.copy()

    # Parse optional strategy params
    params = None
    if args.params:
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as e:
            logger.error("Invalid --params JSON: %s", e)
            print(f"Error: Invalid --params JSON: {e}", file=sys.stderr)
            return 1

    try:
        if args.walk_forward:
            # Walk-forward mode
            try:
                wf_config = json.loads(args.walk_forward)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid --walk-forward JSON: {e}", file=sys.stderr)
                return 1

            required_keys = {"train_bars", "test_bars"}
            if not required_keys.issubset(wf_config.keys()):
                print(
                    f"Error: --walk-forward must include: {required_keys}",
                    file=sys.stderr,
                )
                return 1

            df = load_data(args.data, args.start_bar, args.end_bar)
            results = run_walk_forward(
                args.strategy, df, cost_model, wf_config, params
            )
        else:
            # Standard backtest
            results = run_backtest(
                strategy_path=args.strategy,
                data_path=args.data,
                cost_model=cost_model,
                start_bar=args.start_bar,
                end_bar=args.end_bar,
                params=params,
            )

        # Output
        output_json = json.dumps(results, indent=2, default=str)
        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output_json)
            print(f"Results written to {args.output}", file=sys.stderr)
        else:
            print(output_json)

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception("Backtest failed")
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
