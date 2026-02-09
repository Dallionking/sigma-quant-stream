"""
Crypto risk modeling -- EVT VaR, cascade risk, correlation regimes.

Feeds the @quant-risk-modeler agent with fat-tail-adjusted risk metrics
specifically calibrated for crypto market characteristics.

Key differences from traditional futures risk:
  - Higher margin buffer (2.5x vs 1.5x for futures)
  - Fat-tailed return distributions require EVT, not Gaussian VaR
  - Liquidation cascade risk is unique to crypto
  - Correlation regimes shift dramatically in stress
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.stats import genpareto

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class RiskReport:
    """Comprehensive risk assessment for a crypto strategy.

    Thresholds (from spec):
      EVT VaR: safe <5%, caution 5-10%, danger >10%
      Cascade risk: safe <0.3, caution 0.3-0.6, danger >0.6
      Margin buffer: 2.5x maintenance for crypto
      Max leverage: capped at 20x
    """

    strategy: str
    var_95_daily: float
    var_99_daily: float
    evt_var_99: float  # Fat-tail adjusted
    cvar_99: float  # Expected shortfall (CVaR)
    cascade_risk_score: float  # 0-1
    margin_buffer_multiple: float
    margin_buffer_ok: bool  # >= 2.5x for crypto
    max_recommended_leverage: float
    max_recommended_position_usd: float
    correlation_regime: str  # "normal", "elevated", "stress"
    risk_flags: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class EmergencyAction:
    """Emergency action triggered by risk thresholds."""

    trigger: str
    action: str
    severity: str  # "warning", "critical", "emergency"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# EVT VaR thresholds
EVT_VAR_SAFE = 0.05  # 5%
EVT_VAR_CAUTION = 0.10  # 10%

# Cascade risk thresholds
CASCADE_SAFE = 0.3
CASCADE_CAUTION = 0.6

# Margin buffer requirements
CRYPTO_MARGIN_BUFFER_MULTIPLE = 2.5
FUTURES_MARGIN_BUFFER_MULTIPLE = 1.5

# Leverage cap
MAX_LEVERAGE_CAP = 20.0

# Minimum tail observations for GPD fit
MIN_TAIL_OBSERVATIONS = 10

# Correlation regime thresholds
CORRELATION_STRESS_THRESHOLD = 0.95
CORRELATION_ELEVATED_THRESHOLD = 0.85


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class CryptoRiskModeler:
    """Risk modeling adapted for crypto market characteristics.

    Crypto markets exhibit:
      - Fatter tails than equities (kurtosis 10-50 vs 3-5)
      - Liquidation cascades from leveraged positions
      - Rapid correlation regime shifts in stress
      - 24/7 trading with gap risk on low-liquidity hours

    This modeler uses Extreme Value Theory (GPD) instead of
    Gaussian assumptions, and includes cascade risk scoring
    unique to crypto markets.
    """

    # Crypto requires higher margin buffers than traditional futures
    CRYPTO_MARGIN_BUFFER = CRYPTO_MARGIN_BUFFER_MULTIPLE

    @staticmethod
    def evt_var(returns: np.ndarray, confidence: float = 0.99) -> float:
        """Extreme Value Theory VaR using Generalized Pareto Distribution.

        More accurate than Gaussian VaR for crypto's fat-tailed returns.
        Falls back to historical VaR if insufficient tail data.

        Algorithm:
          1. Find threshold (5th percentile of losses)
          2. Extract exceedances below threshold
          3. Fit GPD to tail exceedances
          4. Calculate EVT VaR using GPD parameters

        Args:
            returns: Array of daily returns (e.g., [-0.03, 0.01, -0.05, ...]).
            confidence: Confidence level (default 0.99 for 99% VaR).

        Returns:
            EVT-adjusted VaR as a negative number (loss).
        """
        if len(returns) < 20:
            logger.warning(
                "Insufficient data for EVT VaR (%d observations), using historical VaR",
                len(returns),
            )
            return float(np.percentile(returns, (1 - confidence) * 100))

        # 1. Find threshold (5th percentile of losses)
        threshold = float(np.percentile(returns, 5))
        exceedances = returns[returns < threshold] - threshold

        if len(exceedances) < MIN_TAIL_OBSERVATIONS:
            # Not enough tail data, fall back to historical VaR
            logger.info(
                "Only %d tail exceedances (need %d), falling back to historical VaR",
                len(exceedances),
                MIN_TAIL_OBSERVATIONS,
            )
            return float(np.percentile(returns, (1 - confidence) * 100))

        # 2. Fit GPD to tail exceedances (negate since GPD fits positive values)
        try:
            shape, loc, scale = genpareto.fit(-exceedances, floc=0)
        except Exception:
            logger.warning("GPD fit failed, falling back to historical VaR", exc_info=True)
            return float(np.percentile(returns, (1 - confidence) * 100))

        # 3. Calculate EVT VaR
        n = len(returns)
        n_u = len(exceedances)

        if abs(shape) < 1e-10:
            # shape ~ 0: exponential tail
            var_evt = threshold - scale * np.log(n / n_u * (1 - confidence))
        else:
            var_evt = threshold - scale / shape * (
                (n / n_u * (1 - confidence)) ** (-shape) - 1
            )

        logger.debug(
            "EVT VaR: threshold=%.4f, shape=%.4f, scale=%.4f, VaR=%.4f",
            threshold,
            shape,
            scale,
            var_evt,
        )

        return float(var_evt)

    @staticmethod
    def cvar(returns: np.ndarray, confidence: float = 0.99) -> float:
        """Conditional VaR (Expected Shortfall) -- average loss beyond VaR.

        CVaR answers: "Given that we are in the worst (1-confidence)% of cases,
        what is the expected loss?"

        Always worse (more negative) than VaR. More sensitive to tail shape.

        Args:
            returns: Array of daily returns.
            confidence: Confidence level (default 0.99).

        Returns:
            CVaR as a negative number (expected tail loss).
        """
        if len(returns) == 0:
            return 0.0

        var = float(np.percentile(returns, (1 - confidence) * 100))
        tail_losses = returns[returns <= var]

        if len(tail_losses) == 0:
            return var

        return float(np.mean(tail_losses))

    @staticmethod
    def cascade_risk_score(
        oi_usd: float,
        estimated_leverage: float,
        funding_rate_8h: float,
        daily_volatility: float,
    ) -> float:
        """Estimate probability of liquidation cascade (0-1).

        Weighted combination of:
          - Leverage concentration (30%)
          - Funding rate extremity (25%)
          - Daily volatility (25%)
          - Open interest concentration (20%)

        High scores indicate elevated risk of cascading liquidations
        that can cause sudden 10-30% moves.

        Args:
            oi_usd: Total open interest in USD.
            estimated_leverage: Estimated average leverage in the market.
            funding_rate_8h: Current 8-hour funding rate (e.g., 0.0001 = 0.01%).
            daily_volatility: Daily return standard deviation (e.g., 0.03 = 3%).

        Returns:
            Cascade risk score from 0.0 (safe) to 1.0 (extreme danger).
        """
        # Normalize each component to [0, 1]
        leverage_risk = min(estimated_leverage / 20.0, 1.0)
        funding_risk = min(abs(funding_rate_8h) / 0.001, 1.0)  # 0.1% per 8h = max
        vol_risk = min(daily_volatility / 0.05, 1.0)  # 5% daily = max
        oi_concentration = min(oi_usd / 1e10, 1.0)  # $10B = max

        score = (
            0.30 * leverage_risk
            + 0.25 * funding_risk
            + 0.25 * vol_risk
            + 0.20 * oi_concentration
        )

        logger.debug(
            "Cascade risk: leverage=%.2f funding=%.2f vol=%.2f oi=%.2f -> %.3f",
            leverage_risk,
            funding_risk,
            vol_risk,
            oi_concentration,
            score,
        )

        return float(score)

    @staticmethod
    def correlation_regime(correlation_matrix: np.ndarray) -> str:
        """Determine if correlations indicate stress.

        In stress regimes, all correlations converge to 1.0
        ("everything sells together"). This eliminates diversification
        benefits and amplifies portfolio risk.

        Args:
            correlation_matrix: NxN correlation matrix.

        Returns:
            "normal" (avg < 0.85), "elevated" (0.85-0.95), or "stress" (> 0.95).
        """
        if correlation_matrix.shape[0] < 2:
            return "normal"

        upper_triangle = correlation_matrix[
            np.triu_indices_from(correlation_matrix, k=1)
        ]

        if len(upper_triangle) == 0:
            return "normal"

        avg = float(np.mean(upper_triangle))

        if avg > CORRELATION_STRESS_THRESHOLD:
            return "stress"
        if avg > CORRELATION_ELEVATED_THRESHOLD:
            return "elevated"
        return "normal"

    @staticmethod
    def margin_buffer_ok(
        leverage: float, buffer_multiple: float = CRYPTO_MARGIN_BUFFER_MULTIPLE
    ) -> bool:
        """Check if margin buffer meets crypto requirements.

        For crypto, we require 2.5x maintenance margin buffer
        (vs 1.5x for traditional futures).

        The check verifies that the required buffer does not
        exceed 100% of capital at the given leverage.

        Args:
            leverage: Current leverage (e.g., 5.0 = 5x).
            buffer_multiple: Required buffer multiple (default 2.5x for crypto).

        Returns:
            True if margin buffer is sufficient.
        """
        if leverage <= 0:
            return True  # No leverage = always OK

        maintenance_margin = 1.0 / leverage
        required_buffer = maintenance_margin * buffer_multiple

        return required_buffer <= 1.0  # Must not exceed 100% of capital

    @staticmethod
    def max_recommended_leverage(
        daily_volatility: float, cascade_risk: float
    ) -> float:
        """Calculate maximum safe leverage given current conditions.

        Base formula: 1 / (3 * daily_vol) -- survive a 3-sigma move.
        Adjusted down by cascade risk discount.

        Args:
            daily_volatility: Daily return standard deviation.
            cascade_risk: Current cascade risk score (0-1).

        Returns:
            Maximum recommended leverage, capped at 20x.
        """
        # Ensure minimum volatility to avoid division by zero
        safe_vol = max(daily_volatility, 0.01)

        # Base: survive a 3-sigma move
        base_leverage = 1.0 / (3.0 * safe_vol)

        # Reduce further if cascade risk is high
        cascade_discount = 1.0 - (cascade_risk * 0.5)

        recommended = base_leverage * cascade_discount

        # Cap at 20x even in best conditions
        result = min(float(recommended), MAX_LEVERAGE_CAP)

        logger.debug(
            "Max leverage: vol=%.4f base=%.1fx cascade_discount=%.2f -> %.1fx",
            daily_volatility,
            base_leverage,
            cascade_discount,
            result,
        )

        return result

    def assess_risk(
        self,
        strategy_name: str,
        returns: np.ndarray,
        leverage: float,
        position_size_usd: float,
        oi_usd: float = 0.0,
        funding_rate_8h: float = 0.0,
        account_equity: float = 100_000.0,
    ) -> RiskReport:
        """Comprehensive risk assessment for a crypto strategy.

        Combines all risk metrics into a single report with flags
        and actionable recommendations.

        Args:
            strategy_name: Name of the strategy being assessed.
            returns: Array of historical daily returns.
            leverage: Current or intended leverage.
            position_size_usd: Intended position size in USD.
            oi_usd: Total open interest in USD (for cascade risk).
            funding_rate_8h: Current 8-hour funding rate.
            account_equity: Total account equity in USD.

        Returns:
            Complete RiskReport with all metrics, flags, and recommendations.
        """
        risk_flags: list[str] = []
        recommendations: list[str] = []

        # --- Core VaR metrics ---
        var_95 = float(np.percentile(returns, 5)) if len(returns) > 0 else 0.0
        var_99 = float(np.percentile(returns, 1)) if len(returns) > 0 else 0.0
        evt_var_99 = self.evt_var(returns, confidence=0.99)
        cvar_99 = self.cvar(returns, confidence=0.99)

        # --- Daily volatility ---
        daily_vol = float(np.std(returns)) if len(returns) > 1 else 0.03

        # --- Cascade risk ---
        cascade_score = self.cascade_risk_score(
            oi_usd=oi_usd,
            estimated_leverage=leverage,
            funding_rate_8h=funding_rate_8h,
            daily_volatility=daily_vol,
        )

        # --- Margin buffer ---
        buffer_ok = self.margin_buffer_ok(leverage, self.CRYPTO_MARGIN_BUFFER)
        if leverage > 0:
            margin_buffer_multiple = 1.0 / (leverage * (1.0 / leverage))  # Simplified
            # Actual margin buffer: how many times maintenance margin fits in equity
            maintenance_req = position_size_usd / leverage if leverage > 0 else position_size_usd
            margin_buffer_multiple = (
                account_equity / maintenance_req if maintenance_req > 0 else float("inf")
            )
        else:
            margin_buffer_multiple = float("inf")

        # --- Max leverage recommendation ---
        max_lev = self.max_recommended_leverage(daily_vol, cascade_score)

        # --- Max position size recommendation ---
        # Risk no more than 2% of equity per trade at the recommended leverage
        risk_per_trade_pct = 0.02
        max_position = account_equity * max_lev * risk_per_trade_pct / max(abs(evt_var_99), 0.001)
        max_position = min(max_position, account_equity * max_lev)

        # --- Correlation regime ---
        # Single strategy: default to normal. Multi-asset needs external matrix.
        corr_regime = "normal"

        # --- Generate flags ---
        # EVT VaR flags
        if abs(evt_var_99) > EVT_VAR_CAUTION:
            risk_flags.append(f"EVT VaR 99% = {evt_var_99:.2%} exceeds danger threshold (>10%)")
            recommendations.append("Reduce position size or leverage immediately")
        elif abs(evt_var_99) > EVT_VAR_SAFE:
            risk_flags.append(f"EVT VaR 99% = {evt_var_99:.2%} in caution zone (5-10%)")
            recommendations.append("Consider reducing leverage or adding hedges")

        # Cascade risk flags
        if cascade_score > CASCADE_CAUTION:
            risk_flags.append(
                f"Cascade risk = {cascade_score:.2f} is DANGER level (>0.6)"
            )
            recommendations.append("Reduce exposure by 50% due to liquidation cascade risk")
        elif cascade_score > CASCADE_SAFE:
            risk_flags.append(
                f"Cascade risk = {cascade_score:.2f} in caution zone (0.3-0.6)"
            )
            recommendations.append("Tighten stop losses and reduce new entries")

        # Margin buffer flags
        if not buffer_ok:
            risk_flags.append("Margin buffer below 2.5x crypto minimum")
            recommendations.append(
                f"Reduce leverage from {leverage:.1f}x to below "
                f"{max_lev:.1f}x to meet 2.5x margin buffer"
            )

        # Leverage flags
        if leverage > max_lev:
            risk_flags.append(
                f"Current leverage {leverage:.1f}x exceeds recommended {max_lev:.1f}x"
            )
            recommendations.append(f"Reduce leverage to {max_lev:.1f}x or below")

        # Position size flags
        if position_size_usd > max_position:
            risk_flags.append(
                f"Position ${position_size_usd:,.0f} exceeds recommended ${max_position:,.0f}"
            )
            recommendations.append(
                f"Reduce position to ${max_position:,.0f} or below"
            )

        # Funding rate flags
        if abs(funding_rate_8h) > 0.0005:
            risk_flags.append(
                f"Extreme funding rate: {funding_rate_8h:.4%} per 8h"
            )
            recommendations.append("Consider mean-reversion or contra-funding trade")

        # Default recommendation if nothing flagged
        if not recommendations:
            recommendations.append("Risk parameters within acceptable bounds")

        logger.info(
            "Risk assessment for '%s': EVT_VaR=%.4f cascade=%.2f "
            "leverage=%.1fx/%.1fx flags=%d",
            strategy_name,
            evt_var_99,
            cascade_score,
            leverage,
            max_lev,
            len(risk_flags),
        )

        return RiskReport(
            strategy=strategy_name,
            var_95_daily=var_95,
            var_99_daily=var_99,
            evt_var_99=evt_var_99,
            cvar_99=cvar_99,
            cascade_risk_score=cascade_score,
            margin_buffer_multiple=margin_buffer_multiple,
            margin_buffer_ok=buffer_ok,
            max_recommended_leverage=max_lev,
            max_recommended_position_usd=max_position,
            correlation_regime=corr_regime,
            risk_flags=risk_flags,
            recommendations=recommendations,
        )

    def check_emergency(self, risk_report: RiskReport) -> Optional[EmergencyAction]:
        """Check if emergency action is needed based on risk report.

        Emergency rules:
          - cascade_risk > 0.7 -> reduce 50%
          - margin_buffer < 2x -> reduce leverage
          - correlation stress -> flatten all
          - EVT VaR > 15% -> halt entries

        Args:
            risk_report: A completed RiskReport.

        Returns:
            EmergencyAction if action needed, None if all clear.
        """
        # Emergency: correlation stress (most severe -- flatten everything)
        if risk_report.correlation_regime == "stress":
            logger.critical(
                "EMERGENCY: Correlation stress detected for '%s'. Flatten all positions.",
                risk_report.strategy,
            )
            return EmergencyAction(
                trigger=f"Correlation regime = {risk_report.correlation_regime}",
                action="FLATTEN_ALL: Close all positions immediately",
                severity="emergency",
            )

        # Emergency: EVT VaR > 15% (halt all new entries)
        if abs(risk_report.evt_var_99) > 0.15:
            logger.critical(
                "EMERGENCY: EVT VaR %.2f%% for '%s'. Halt all entries.",
                risk_report.evt_var_99 * 100,
                risk_report.strategy,
            )
            return EmergencyAction(
                trigger=f"EVT VaR 99% = {risk_report.evt_var_99:.2%} (>15%)",
                action="HALT_ENTRIES: No new positions. Tighten existing stops.",
                severity="emergency",
            )

        # Critical: cascade_risk > 0.7 (reduce 50%)
        if risk_report.cascade_risk_score > 0.7:
            logger.warning(
                "CRITICAL: Cascade risk %.2f for '%s'. Reduce 50%%.",
                risk_report.cascade_risk_score,
                risk_report.strategy,
            )
            return EmergencyAction(
                trigger=f"Cascade risk = {risk_report.cascade_risk_score:.2f} (>0.7)",
                action="REDUCE_50PCT: Cut all positions by 50%",
                severity="critical",
            )

        # Critical: margin buffer < 2.0x (below minimum)
        if risk_report.margin_buffer_multiple < 2.0:
            logger.warning(
                "CRITICAL: Margin buffer %.1fx for '%s'. Reduce leverage.",
                risk_report.margin_buffer_multiple,
                risk_report.strategy,
            )
            return EmergencyAction(
                trigger=f"Margin buffer = {risk_report.margin_buffer_multiple:.1f}x (<2.0x)",
                action="REDUCE_LEVERAGE: Decrease leverage to restore 2.5x buffer",
                severity="critical",
            )

        # Warning: cascade_risk > 0.5 (elevated but not critical)
        if risk_report.cascade_risk_score > 0.5:
            logger.info(
                "WARNING: Elevated cascade risk %.2f for '%s'.",
                risk_report.cascade_risk_score,
                risk_report.strategy,
            )
            return EmergencyAction(
                trigger=f"Cascade risk = {risk_report.cascade_risk_score:.2f} (>0.5)",
                action="TIGHTEN_STOPS: Reduce stop distances by 25%",
                severity="warning",
            )

        return None
