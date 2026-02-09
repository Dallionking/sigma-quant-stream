"""
Freqtrade Strategy Bridge.

Converts validated Sigma-Quant crypto strategies into Freqtrade IStrategy
format for paper trading (dry-run mode).

Maps indicator names to pandas-ta equivalents and generates
Freqtrade-compatible strategy files + config.json.
"""

from __future__ import annotations

import json
import logging
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Output directory for generated Freqtrade strategies
FREQTRADE_OUTPUT_DIR = Path("strategies/freqtrade")

# Mapping: indicator names -> pandas-ta function calls
INDICATOR_MAP: dict[str, str] = {
    "sma": "ta.sma(dataframe['close'], length={period})",
    "ema": "ta.ema(dataframe['close'], length={period})",
    "rsi": "ta.rsi(dataframe['close'], length={period})",
    "macd": "ta.macd(dataframe['close'], fast={fast}, slow={slow}, signal={signal})",
    "bbands": "ta.bbands(dataframe['close'], length={period}, std={std})",
    "atr": "ta.atr(dataframe['high'], dataframe['low'], dataframe['close'], length={period})",
    "vwap": "ta.vwap(dataframe['high'], dataframe['low'], dataframe['close'], dataframe['volume'])",
    "adx": "ta.adx(dataframe['high'], dataframe['low'], dataframe['close'], length={period})",
    "stoch_rsi": "ta.stochrsi(dataframe['close'], length={period})",
    "obv": "ta.obv(dataframe['close'], dataframe['volume'])",
}


@dataclass
class FreqtradeConfig:
    """Configuration for Freqtrade dry-run deployment."""

    strategy_name: str
    exchange: str = "binance"
    trading_mode: str = "futures"
    margin_mode: str = "isolated"
    stake_currency: str = "USDT"
    stake_amount: float = 100.0
    max_open_trades: int = 3
    timeframe: str = "5m"
    dry_run: bool = True  # Always paper trade
    pairs: list[str] = field(default_factory=lambda: ["BTC/USDT:USDT"])
    stoploss: float = -0.05
    trailing_stop: bool = False
    roi: dict[str, float] = field(
        default_factory=lambda: {"0": 0.10, "30": 0.05, "60": 0.02, "120": 0}
    )

    def to_dict(self) -> dict[str, Any]:
        """Generate Freqtrade config.json content."""
        return {
            "trading_mode": self.trading_mode,
            "margin_mode": self.margin_mode,
            "stake_currency": self.stake_currency,
            "stake_amount": self.stake_amount,
            "max_open_trades": self.max_open_trades,
            "dry_run": self.dry_run,
            "dry_run_wallet": 10000,
            "exchange": {
                "name": self.exchange,
                "key": "",
                "secret": "",
                "ccxt_sync_config": {"enableRateLimit": True},
                "ccxt_async_config": {"enableRateLimit": True},
            },
            "pairlists": [{"method": "StaticPairList"}],
            "pair_whitelist": self.pairs,
            "timeframe": self.timeframe,
            "strategy": self.strategy_name,
        }


class FreqtradeBridge:
    """
    Converts Sigma-Quant strategy profiles to Freqtrade IStrategy classes.

    Usage:
        bridge = FreqtradeBridge()
        result = bridge.convert(strategy_profile, config)
        # result.strategy_path -> Path to generated .py file
        # result.config_path -> Path to generated config.json
    """

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or FREQTRADE_OUTPUT_DIR

    def convert(
        self,
        profile: dict[str, Any],
        config: FreqtradeConfig | None = None,
    ) -> ConversionResult:
        """
        Convert a Sigma-Quant strategy profile to Freqtrade format.

        Args:
            profile: Strategy profile dict with indicators, entry/exit rules
            config: Freqtrade config (defaults generated from profile)

        Returns:
            ConversionResult with paths to generated files
        """
        strategy_name = self._sanitize_name(
            profile.get("name", profile.get("strategy", {}).get("name", "SigmaQuantStrategy"))
        )

        if config is None:
            config = self._config_from_profile(profile, strategy_name)

        # Generate strategy class code
        strategy_code = self._generate_strategy(profile, strategy_name, config)

        # Write files
        self.output_dir.mkdir(parents=True, exist_ok=True)
        strategy_path = self.output_dir / f"{strategy_name}.py"
        config_path = self.output_dir / f"{strategy_name}_config.json"

        strategy_path.write_text(strategy_code)
        config_path.write_text(json.dumps(config.to_dict(), indent=2))

        logger.info(
            "Freqtrade strategy generated: %s (%d lines)",
            strategy_path,
            len(strategy_code.splitlines()),
        )

        return ConversionResult(
            strategy_name=strategy_name,
            strategy_path=strategy_path,
            config_path=config_path,
            config=config,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _sanitize_name(self, name: str) -> str:
        """Convert strategy name to valid Python class name."""
        # Remove special chars, capitalize words
        cleaned = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
        parts = cleaned.split("_")
        return "".join(p.capitalize() for p in parts if p)

    def _config_from_profile(
        self, profile: dict[str, Any], strategy_name: str
    ) -> FreqtradeConfig:
        """Generate FreqtradeConfig from strategy profile."""
        params = profile.get("parameters", {})
        risk = profile.get("risk_params", params)
        deployment = profile.get("deployment", {})

        symbols = deployment.get("symbols", ["BTC/USDT:USDT"])
        if isinstance(symbols, str):
            symbols = [symbols]

        # Convert stop loss percentage to Freqtrade format (negative fraction)
        sl_pct = risk.get("stop_loss_pct", 5.0)
        stoploss = -(sl_pct / 100.0)

        return FreqtradeConfig(
            strategy_name=strategy_name,
            exchange=deployment.get("exchange", "binance"),
            timeframe=params.get("timeframe", "5m"),
            pairs=symbols,
            stoploss=stoploss,
            stake_amount=deployment.get("stake_amount", 100.0),
            max_open_trades=deployment.get("max_open_trades", 3),
        )

    def _generate_strategy(
        self,
        profile: dict[str, Any],
        strategy_name: str,
        config: FreqtradeConfig,
    ) -> str:
        """Generate Freqtrade IStrategy Python code."""
        indicators_code = self._generate_indicators(profile)
        buy_conditions = self._generate_buy_conditions(profile)
        sell_conditions = self._generate_sell_conditions(profile)

        return textwrap.dedent(f'''\
            """
            Auto-generated Freqtrade strategy from Sigma-Quant.

            Strategy: {strategy_name}
            Generated: {datetime.now(timezone.utc).isoformat()}
            Source: Sigma-Quant Crypto Pipeline
            Mode: DRY RUN ONLY
            """

            import pandas_ta as ta
            from freqtrade.strategy import IStrategy, DecimalParameter
            from pandas import DataFrame


            class {strategy_name}(IStrategy):
                """
                Sigma-Quant auto-converted strategy for paper trading.

                WARNING: This is for dry-run/paper trading only.
                Do not use with real funds without manual review.
                """

                INTERFACE_VERSION = 3
                timeframe = "{config.timeframe}"
                stoploss = {config.stoploss}
                trailing_stop = {str(config.trailing_stop)}
                minimal_roi = {json.dumps(config.roi)}
                can_short = True

                def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                    """Calculate indicators using pandas-ta."""
            {textwrap.indent(indicators_code, "        ")}
                    return dataframe

                def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                    """Define entry conditions."""
            {textwrap.indent(buy_conditions, "        ")}
                    return dataframe

                def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                    """Define exit conditions."""
            {textwrap.indent(sell_conditions, "        ")}
                    return dataframe
        ''')

    def _generate_indicators(self, profile: dict[str, Any]) -> str:
        """Generate indicator calculation code from profile."""
        lines: list[str] = []
        indicators = profile.get("indicators", profile.get("parameters", {}).get("indicators", []))

        if not indicators:
            # Default indicators
            lines.append("dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)")
            lines.append("dataframe['ema_fast'] = ta.ema(dataframe['close'], length=9)")
            lines.append("dataframe['ema_slow'] = ta.ema(dataframe['close'], length=21)")
            return "\n".join(lines)

        for ind in indicators:
            if isinstance(ind, str):
                name = ind
                params: dict[str, Any] = {}
            elif isinstance(ind, dict):
                name = ind.get("name", "")
                params = ind.get("params", ind.get("parameters", {}))
            else:
                continue

            template = INDICATOR_MAP.get(name.lower())
            if template:
                try:
                    code = template.format(**params) if params else template.format(period=14, fast=12, slow=26, signal=9, std=2)
                    col_name = f"{name}_{params.get('period', '')}" if params.get('period') else name
                    lines.append(f"dataframe['{col_name}'] = {code}")
                except (KeyError, ValueError):
                    lines.append(f"# Skipped {name}: missing parameters")

        if not lines:
            lines.append("dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)")

        return "\n".join(lines)

    def _generate_buy_conditions(self, profile: dict[str, Any]) -> str:
        """Generate entry condition code from profile."""
        entry = profile.get("entry_logic", profile.get("entry_rules", {}))

        if not entry:
            return textwrap.dedent("""\
                dataframe.loc[
                    (dataframe['rsi'] < 30),
                    ['enter_long', 'enter_tag']
                ] = (1, 'rsi_oversold')
                dataframe.loc[
                    (dataframe['rsi'] > 70),
                    ['enter_short', 'enter_tag']
                ] = (1, 'rsi_overbought')""")

        # Build from entry conditions
        conditions = entry.get("conditions", [])
        if not conditions:
            return textwrap.dedent("""\
                dataframe.loc[
                    (dataframe['rsi'] < 30),
                    ['enter_long', 'enter_tag']
                ] = (1, 'default_long')""")

        lines: list[str] = []
        for i, cond in enumerate(conditions):
            indicator = cond.get("indicator", "rsi")
            operator = cond.get("operator", "<")
            value = cond.get("value", 30)
            tag = cond.get("tag", f"cond_{i}")

            lines.append("dataframe.loc[")
            lines.append(f"    (dataframe['{indicator}'] {operator} {value}),")
            lines.append("    ['enter_long', 'enter_tag']")
            lines.append(f"] = (1, '{tag}')")

        return "\n".join(lines)

    def _generate_sell_conditions(self, profile: dict[str, Any]) -> str:
        """Generate exit condition code from profile."""
        exit_rules = profile.get("exit_logic", profile.get("exit_rules", {}))

        if not exit_rules:
            return textwrap.dedent("""\
                dataframe.loc[
                    (dataframe['rsi'] > 70),
                    ['exit_long', 'exit_tag']
                ] = (1, 'rsi_exit')
                dataframe.loc[
                    (dataframe['rsi'] < 30),
                    ['exit_short', 'exit_tag']
                ] = (1, 'rsi_exit_short')""")

        conditions = exit_rules.get("conditions", [])
        if not conditions:
            return textwrap.dedent("""\
                dataframe.loc[
                    (dataframe['rsi'] > 70),
                    ['exit_long', 'exit_tag']
                ] = (1, 'default_exit')""")

        lines: list[str] = []
        for i, cond in enumerate(conditions):
            indicator = cond.get("indicator", "rsi")
            operator = cond.get("operator", ">")
            value = cond.get("value", 70)
            tag = cond.get("tag", f"exit_{i}")

            lines.append("dataframe.loc[")
            lines.append(f"    (dataframe['{indicator}'] {operator} {value}),")
            lines.append("    ['exit_long', 'exit_tag']")
            lines.append(f"] = (1, '{tag}')")

        return "\n".join(lines)


@dataclass
class ConversionResult:
    """Result of a Freqtrade strategy conversion."""

    strategy_name: str
    strategy_path: Path
    config_path: Path
    config: FreqtradeConfig
    generated_at: str
