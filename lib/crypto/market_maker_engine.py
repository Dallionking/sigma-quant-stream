"""Avellaneda-Stoikov market making engine for crypto perpetuals.

Implements the classic A-S framework with extensions for:
- 24/7 crypto markets (no closing bell, so ``time_remaining`` defaults to 1.0)
- Inventory skewing with configurable thresholds
- Adverse-selection detection via order-flow imbalance
- Volatility circuit-breaker to pause quoting in extreme conditions

All methods are synchronous (pure computation, no API calls).
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Quote:
    """A single bid/ask quote pair."""

    bid_price: float
    ask_price: float
    bid_size: float
    ask_size: float
    spread_bps: float


@dataclass
class MMParameters:
    """Configurable parameters for the market-making engine."""

    gamma: float  # risk aversion coefficient (0.01 - 1.0)
    base_spread_bps: float
    max_inventory: float
    skew_threshold: float  # fraction of max_inventory to start skewing (0-1)
    quote_size: float
    refresh_rate_ms: int
    min_spread_bps: float  # floor spread -- never quote tighter than this


@dataclass
class InventoryAction:
    """Describes how quotes should be skewed based on inventory."""

    should_skew: bool
    bid_offset: float
    ask_offset: float
    reduce_side: Optional[str]  # "bid" or "ask" if at inventory limit, else None


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class AvellanedaStoikovEngine:
    """Market making with the Avellaneda-Stoikov framework adapted for 24/7 crypto.

    The A-S model computes:

    1. **Reservation price** -- an inventory-adjusted fair value that is
       shifted away from mid when the market maker is carrying inventory.
    2. **Optimal spread** -- the width of the bid-ask that balances adverse
       selection risk against the desire to capture spread.

    Parameters are encapsulated in ``MMParameters``.
    """

    def __init__(self, params: MMParameters) -> None:
        if params.gamma <= 0:
            raise ValueError("gamma must be positive")
        self.params = params

    # ------------------------------------------------------------------
    # Core A-S computations
    # ------------------------------------------------------------------

    def reservation_price(
        self,
        mid_price: float,
        inventory: float,
        volatility: float,
        time_remaining: float = 1.0,
    ) -> float:
        """Calculate the reservation (indifference) price.

        Formula:
            ``r = mid - q * gamma * sigma^2 * T``

        where *q* is the signed inventory, *gamma* the risk-aversion
        parameter, *sigma* the volatility, and *T* time remaining
        (normalised; defaults to 1.0 for 24/7 crypto).
        """
        return mid_price - inventory * self.params.gamma * volatility ** 2 * time_remaining

    def optimal_spread(
        self,
        volatility: float,
        time_remaining: float = 1.0,
        order_intensity: float = 1.0,
    ) -> float:
        """Calculate the optimal full spread as a **fraction of price**.

        The raw Avellaneda-Stoikov formula outputs a spread in abstract
        units.  We normalise it to a fraction so that it can be applied
        to any mid price via ``mid * spread_fraction``.

        Formula:
            ``delta = gamma * sigma^2 * T + (2 / gamma) * ln(1 + gamma / k)``

        The result is clamped to be no less than ``min_spread_bps / 10_000``.
        """
        gamma = self.params.gamma
        intensity = max(order_intensity, 1e-9)  # avoid division by zero / log(1)
        spread = (
            gamma * volatility ** 2 * time_remaining
            + (2.0 / gamma) * math.log(1.0 + gamma / intensity)
        )
        min_spread = self.params.min_spread_bps / 10_000.0
        return max(spread, min_spread)

    # ------------------------------------------------------------------
    # Inventory management
    # ------------------------------------------------------------------

    def inventory_skew(self, inventory: float) -> InventoryAction:
        """Calculate quote skew based on current inventory position.

        When inventory exceeds ``skew_threshold * max_inventory``, quotes
        are biased to reduce the position.  At full ``max_inventory`` the
        side that would *increase* inventory is removed entirely.
        """
        max_inv = self.params.max_inventory
        if max_inv <= 0:
            return InventoryAction(False, 0.0, 0.0, None)

        threshold = max_inv * self.params.skew_threshold

        if abs(inventory) <= threshold:
            return InventoryAction(False, 0.0, 0.0, None)

        # How far past threshold we are, normalised to [0, 1].
        skew_pct = (abs(inventory) - threshold) / (max_inv - threshold)
        skew_pct = min(skew_pct, 1.0)

        if inventory > 0:
            # Long inventory -- make the ask more attractive (lower ask),
            # make the bid less attractive (lower bid).
            bid_offset = skew_pct * 0.001
            ask_offset = -skew_pct * 0.001
            reduce_side = "bid" if inventory >= max_inv else None
        else:
            # Short inventory -- make the bid more attractive (raise bid),
            # make the ask less attractive (raise ask).
            bid_offset = -skew_pct * 0.001
            ask_offset = skew_pct * 0.001
            reduce_side = "ask" if abs(inventory) >= max_inv else None

        return InventoryAction(
            should_skew=True,
            bid_offset=bid_offset,
            ask_offset=ask_offset,
            reduce_side=reduce_side,
        )

    # ------------------------------------------------------------------
    # Quote generation
    # ------------------------------------------------------------------

    def generate_quotes(
        self,
        mid_price: float,
        inventory: float,
        volatility: float,
        time_remaining: float = 1.0,
        order_intensity: float = 1.0,
    ) -> Quote:
        """Generate bid/ask quotes with inventory skewing.

        This is the main entry point for the quoting loop.  It combines
        the reservation price, optimal spread, and inventory skew into
        a final ``Quote``.

        ``optimal_spread()`` returns a spread as a fraction of price.
        We convert it to an absolute price spread by multiplying by
        ``mid_price``.
        """
        res_price = self.reservation_price(mid_price, inventory, volatility, time_remaining)
        spread_frac = self.optimal_spread(volatility, time_remaining, order_intensity)
        # Convert fractional spread to absolute price spread
        spread_abs = spread_frac * mid_price

        # Apply inventory skew (offsets are in fractional terms, scale to price)
        skew = self.inventory_skew(inventory)
        bid_skew = skew.bid_offset * mid_price
        ask_skew = skew.ask_offset * mid_price

        bid = res_price - spread_abs / 2.0 + bid_skew
        ask = res_price + spread_abs / 2.0 + ask_skew

        # Ensure bid < ask invariant
        if bid >= ask:
            centre = (bid + ask) / 2.0
            min_half = (self.params.min_spread_bps / 10_000.0) * mid_price / 2.0
            bid = centre - min_half
            ask = centre + min_half

        # Determine sizes (reduce on limit side)
        bid_size = self.params.quote_size
        ask_size = self.params.quote_size
        if skew.reduce_side == "bid":
            bid_size = 0.0  # Stop buying
        elif skew.reduce_side == "ask":
            ask_size = 0.0  # Stop selling

        spread_bps = ((ask - bid) / mid_price * 10_000) if mid_price > 0 else 0.0

        return Quote(
            bid_price=round(bid, 8),
            ask_price=round(ask, 8),
            bid_size=bid_size,
            ask_size=ask_size,
            spread_bps=round(spread_bps, 2),
        )

    # ------------------------------------------------------------------
    # Risk controls
    # ------------------------------------------------------------------

    @staticmethod
    def detect_adverse_selection(
        order_flow_imbalance: float,
        duration_minutes: float,
    ) -> bool:
        """Detect toxic order flow that should trigger spread widening.

        An order-flow imbalance exceeding 70% sustained for at least
        5 minutes indicates informed trading against the market maker.
        """
        return order_flow_imbalance > 0.7 and duration_minutes >= 5.0

    def volatility_circuit_breaker(
        self,
        current_vol: float,
        normal_vol: float,
    ) -> bool:
        """Check if volatility warrants pausing MM activity.

        Returns ``True`` when current volatility exceeds 5x normal --
        the market maker should pull all quotes until conditions normalise.
        """
        if normal_vol <= 0:
            return False
        return current_vol > normal_vol * 5.0

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def effective_spread_at_vol(self, volatility: float) -> float:
        """Return the effective spread in bps at a given volatility level.

        Since ``optimal_spread()`` already returns a fraction of price,
        converting to basis points is simply ``frac * 10_000``.
        """
        spread_frac = self.optimal_spread(volatility)
        return spread_frac * 10_000  # convert fraction to bps
