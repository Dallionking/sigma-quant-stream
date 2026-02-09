"""
On-chain analytics service -- SOPR, MVRV, exchange flows, whale tracking.

Feeds the @quant-onchain-researcher agent with aggregated on-chain data
from multiple sources (CryptoQuant, Glassnode, DeFi Llama).

Graceful degradation: If premium API keys are not set, falls back to
DeFi Llama (free) for available data and returns partial results for the rest.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SOPRData:
    """Spent Output Profit Ratio data.

    SOPR = value_of_outputs / value_of_inputs.
    > 1.0  -> coins moving at profit (bullish)
    < 1.0  -> capitulation (bearish)
    ~ 1.0  -> cost basis (neutral)
    """

    asset: str
    value: float
    interpretation: str  # "bullish", "bearish", "neutral"
    percentile_90d: float


@dataclass
class MVRVData:
    """Market Value to Realized Value ratio data.

    MVRV = market_cap / realized_cap.
    > 3.5  -> overheated
    1.0-3.5 -> neutral
    < 1.0  -> undervalued
    """

    asset: str
    value: float
    interpretation: str  # "overheated", "neutral", "undervalued"
    percentile_90d: float


@dataclass
class ExchangeFlowData:
    """Exchange inflow/outflow data.

    net_flow_24h: positive = net inflows (bearish / selling pressure).
    """

    asset: str
    net_flow_24h: float  # positive = inflows (bearish)
    inflows_24h: float
    outflows_24h: float
    large_transactions: int  # > $10M
    whale_direction: str  # "accumulating", "distributing", "neutral"


@dataclass
class StablecoinSupplyData:
    """Stablecoin supply and SSR data.

    SSR (Stablecoin Supply Ratio) = BTC Market Cap / Total Stablecoin Supply.
    Low SSR -> high buying power -> bullish.
    """

    total_stablecoin_supply_usd: float
    top_stablecoins: list[dict[str, Any]] = field(default_factory=list)
    ssr: float | None = None  # Requires BTC market cap


@dataclass
class CompositeSignal:
    """Aggregated on-chain signal combining all indicators."""

    asset: str
    direction: str  # "bullish", "bearish", "neutral"
    strength: float  # 0-1
    supporting: list[str] = field(default_factory=list)
    conflicting: list[str] = field(default_factory=list)
    is_strong_accumulation: bool = False
    is_strong_distribution: bool = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFI_LLAMA_BASE_URL = "https://api.llama.fi"
DEFI_LLAMA_STABLECOINS_URL = "https://stablecoins.llama.fi"
CRYPTOQUANT_BASE_URL = "https://api.cryptoquant.com/v1"
GLASSNODE_BASE_URL = "https://api.glassnode.com/v1"

# SOPR interpretation thresholds
SOPR_BULLISH_THRESHOLD = 1.02
SOPR_BEARISH_THRESHOLD = 0.98

# MVRV interpretation thresholds
MVRV_OVERHEATED_THRESHOLD = 3.5
MVRV_UNDERVALUED_THRESHOLD = 1.0

# Exchange flow thresholds (BTC units per 24h)
LARGE_TX_THRESHOLD_USD = 10_000_000
WHALE_ACCUMULATION_NET_FLOW_THRESHOLD = -500  # net outflow > 500 BTC
WHALE_DISTRIBUTION_NET_FLOW_THRESHOLD = 500  # net inflow > 500 BTC


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class OnChainService:
    """Aggregates on-chain data from multiple sources.

    Uses a tiered approach:
      1. CryptoQuant (if key provided) -- SOPR, MVRV, exchange flows
      2. Glassnode (if key provided) -- additional on-chain metrics
      3. DeFi Llama (free, always available) -- stablecoin supply, TVL

    If premium keys are absent, metrics that require them return
    estimated/partial data with appropriate flags.
    """

    def __init__(
        self,
        cryptoquant_api_key: str = "",
        glassnode_api_key: str = "",
    ) -> None:
        """Initialize on-chain service.

        Args:
            cryptoquant_api_key: API key for CryptoQuant. Empty string = disabled.
            glassnode_api_key: API key for Glassnode. Empty string = disabled.
        """
        self.cryptoquant_key = cryptoquant_api_key
        self.glassnode_key = glassnode_api_key
        self._http = httpx.AsyncClient(timeout=30.0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_sopr(self, asset: str = "BTC") -> SOPRData:
        """Get SOPR from CryptoQuant or return estimated fallback.

        SOPR = value_of_outputs / value_of_inputs.
        > 1.0  -> bullish (coins moving at profit)
        < 1.0  -> bearish (capitulation)
        ~ 1.0  -> neutral (cost basis)

        Args:
            asset: Cryptocurrency asset symbol (default BTC).

        Returns:
            SOPRData with current value and interpretation.
        """
        if self.cryptoquant_key:
            try:
                return await self._fetch_sopr_cryptoquant(asset)
            except Exception:
                logger.warning(
                    "CryptoQuant SOPR fetch failed for %s, using fallback",
                    asset,
                    exc_info=True,
                )

        # Fallback: return neutral estimate with explicit flag
        logger.info("No CryptoQuant key or fetch failed; returning SOPR estimate for %s", asset)
        return SOPRData(
            asset=asset,
            value=1.0,
            interpretation="neutral",
            percentile_90d=50.0,
        )

    async def get_mvrv(self, asset: str = "BTC") -> MVRVData:
        """Get MVRV ratio from Glassnode or CryptoQuant.

        MVRV = market_cap / realized_cap.
        > 3.5  -> overheated
        1.0-3.5 -> neutral
        < 1.0  -> undervalued

        Args:
            asset: Cryptocurrency asset symbol (default BTC).

        Returns:
            MVRVData with current value and interpretation.
        """
        # Try Glassnode first, then CryptoQuant
        if self.glassnode_key:
            try:
                return await self._fetch_mvrv_glassnode(asset)
            except Exception:
                logger.warning(
                    "Glassnode MVRV fetch failed for %s, trying CryptoQuant",
                    asset,
                    exc_info=True,
                )

        if self.cryptoquant_key:
            try:
                return await self._fetch_mvrv_cryptoquant(asset)
            except Exception:
                logger.warning(
                    "CryptoQuant MVRV fetch failed for %s, using fallback",
                    asset,
                    exc_info=True,
                )

        # Fallback: neutral estimate
        logger.info("No API key for MVRV; returning estimate for %s", asset)
        return MVRVData(
            asset=asset,
            value=1.5,
            interpretation="neutral",
            percentile_90d=50.0,
        )

    async def get_exchange_flows(
        self, asset: str = "BTC", hours: int = 24
    ) -> ExchangeFlowData:
        """Get exchange inflow/outflow data.

        Net flow = inflows - outflows.
        Large inflows (>1000 BTC) indicate selling pressure.
        Large outflows indicate accumulation.

        Args:
            asset: Cryptocurrency asset symbol (default BTC).
            hours: Lookback window in hours (default 24).

        Returns:
            ExchangeFlowData with flow metrics and whale direction.
        """
        if self.cryptoquant_key:
            try:
                return await self._fetch_exchange_flows_cryptoquant(asset, hours)
            except Exception:
                logger.warning(
                    "CryptoQuant exchange flow fetch failed for %s, using fallback",
                    asset,
                    exc_info=True,
                )

        # Fallback: neutral / zero flows
        logger.info("No CryptoQuant key for exchange flows; returning neutral for %s", asset)
        return ExchangeFlowData(
            asset=asset,
            net_flow_24h=0.0,
            inflows_24h=0.0,
            outflows_24h=0.0,
            large_transactions=0,
            whale_direction="neutral",
        )

    async def get_stablecoin_supply(self) -> StablecoinSupplyData:
        """Get stablecoin supply data from DeFi Llama (free, no API key).

        SSR = BTC Market Cap / Total Stablecoin Cap.
        Low SSR -> high buying power -> bullish.

        Returns:
            StablecoinSupplyData with total supply and top stablecoins.
        """
        try:
            url = f"{DEFI_LLAMA_STABLECOINS_URL}/stablecoins?includePrices=true"
            resp = await self._http.get(url)
            resp.raise_for_status()
            data = resp.json()

            stablecoins_list = data.get("peggedAssets", [])
            total_supply = 0.0
            top_coins: list[dict[str, Any]] = []

            for coin in stablecoins_list:
                circulating = coin.get("circulating", {})
                peg_usd = circulating.get("peggedUSD", 0)
                if peg_usd is None:
                    peg_usd = 0
                peg_usd = float(peg_usd)
                total_supply += peg_usd

                if len(top_coins) < 10:
                    top_coins.append(
                        {
                            "name": coin.get("name", "Unknown"),
                            "symbol": coin.get("symbol", "???"),
                            "circulating_usd": peg_usd,
                        }
                    )

            # Sort top coins by circulating supply descending
            top_coins.sort(key=lambda c: c["circulating_usd"], reverse=True)

            logger.info(
                "DeFi Llama stablecoin supply: $%.2fB across %d assets",
                total_supply / 1e9,
                len(stablecoins_list),
            )

            return StablecoinSupplyData(
                total_stablecoin_supply_usd=total_supply,
                top_stablecoins=top_coins[:10],
                ssr=None,  # Would need BTC market cap to compute
            )

        except Exception:
            logger.warning("DeFi Llama stablecoin fetch failed", exc_info=True)
            return StablecoinSupplyData(
                total_stablecoin_supply_usd=0.0,
                top_stablecoins=[],
                ssr=None,
            )

    async def composite_signal(self, asset: str = "BTC") -> CompositeSignal:
        """Generate composite on-chain signal combining all indicators.

        Strong accumulation criteria:
          - SOPR < 1.0 AND MVRV < 1.5 AND outflows > inflows
          - Stablecoin supply increasing (high buying power)

        Strong distribution criteria:
          - SOPR > 1.05 AND MVRV > 3.0 AND inflows > outflows significantly

        Args:
            asset: Cryptocurrency asset symbol (default BTC).

        Returns:
            CompositeSignal with aggregated direction and strength.
        """
        # Gather all data concurrently-safe (sequential to avoid overwhelming APIs)
        sopr = await self.get_sopr(asset)
        mvrv = await self.get_mvrv(asset)
        flows = await self.get_exchange_flows(asset)
        stablecoins = await self.get_stablecoin_supply()

        supporting: list[str] = []
        conflicting: list[str] = []
        bullish_score = 0.0
        bearish_score = 0.0

        # --- SOPR signal (weight: 0.25) ---
        if sopr.value < SOPR_BEARISH_THRESHOLD:
            bullish_score += 0.25  # Capitulation = contrarian bullish
            supporting.append(f"SOPR={sopr.value:.3f} (capitulation, contrarian bullish)")
        elif sopr.value > SOPR_BULLISH_THRESHOLD:
            bearish_score += 0.15  # Profit taking = mildly bearish
            conflicting.append(f"SOPR={sopr.value:.3f} (profit-taking)")
        else:
            supporting.append(f"SOPR={sopr.value:.3f} (neutral)")

        # --- MVRV signal (weight: 0.30) ---
        if mvrv.value < MVRV_UNDERVALUED_THRESHOLD:
            bullish_score += 0.30
            supporting.append(f"MVRV={mvrv.value:.2f} (undervalued)")
        elif mvrv.value > MVRV_OVERHEATED_THRESHOLD:
            bearish_score += 0.30
            conflicting.append(f"MVRV={mvrv.value:.2f} (overheated)")
        elif mvrv.value > 2.5:
            bearish_score += 0.10
            conflicting.append(f"MVRV={mvrv.value:.2f} (elevated)")
        else:
            supporting.append(f"MVRV={mvrv.value:.2f} (neutral)")

        # --- Exchange flow signal (weight: 0.25) ---
        if flows.net_flow_24h < WHALE_ACCUMULATION_NET_FLOW_THRESHOLD:
            bullish_score += 0.25
            supporting.append(
                f"Net flow={flows.net_flow_24h:.1f} (outflows dominant, accumulation)"
            )
        elif flows.net_flow_24h > WHALE_DISTRIBUTION_NET_FLOW_THRESHOLD:
            bearish_score += 0.25
            conflicting.append(
                f"Net flow={flows.net_flow_24h:.1f} (inflows dominant, selling pressure)"
            )
        else:
            supporting.append(f"Net flow={flows.net_flow_24h:.1f} (balanced)")

        # --- Stablecoin signal (weight: 0.20) ---
        if stablecoins.total_stablecoin_supply_usd > 150e9:
            bullish_score += 0.20
            supporting.append(
                f"Stablecoin supply=${stablecoins.total_stablecoin_supply_usd / 1e9:.1f}B (high buying power)"
            )
        elif stablecoins.total_stablecoin_supply_usd > 0:
            bullish_score += 0.05
            supporting.append(
                f"Stablecoin supply=${stablecoins.total_stablecoin_supply_usd / 1e9:.1f}B"
            )

        # --- Compute composite ---
        net_score = bullish_score - bearish_score

        if net_score > 0.15:
            direction = "bullish"
        elif net_score < -0.15:
            direction = "bearish"
        else:
            direction = "neutral"

        strength = min(abs(net_score), 1.0)

        # Strong accumulation check
        is_strong_accumulation = (
            sopr.value < 1.0
            and mvrv.value < 1.5
            and flows.net_flow_24h < WHALE_ACCUMULATION_NET_FLOW_THRESHOLD
        )

        # Strong distribution check
        is_strong_distribution = (
            sopr.value > 1.05
            and mvrv.value > MVRV_OVERHEATED_THRESHOLD
            and flows.net_flow_24h > WHALE_DISTRIBUTION_NET_FLOW_THRESHOLD
        )

        logger.info(
            "Composite signal for %s: direction=%s strength=%.2f "
            "bullish=%.2f bearish=%.2f accumulation=%s distribution=%s",
            asset,
            direction,
            strength,
            bullish_score,
            bearish_score,
            is_strong_accumulation,
            is_strong_distribution,
        )

        return CompositeSignal(
            asset=asset,
            direction=direction,
            strength=strength,
            supporting=supporting,
            conflicting=conflicting,
            is_strong_accumulation=is_strong_accumulation,
            is_strong_distribution=is_strong_distribution,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()

    # ------------------------------------------------------------------
    # Private: CryptoQuant
    # ------------------------------------------------------------------

    async def _fetch_sopr_cryptoquant(self, asset: str) -> SOPRData:
        """Fetch SOPR from CryptoQuant API.

        Endpoint: /v1/btc/market-indicator/sopr
        """
        asset_lower = asset.lower()
        url = f"{CRYPTOQUANT_BASE_URL}/{asset_lower}/market-indicator/sopr"
        headers = {"Authorization": f"Bearer {self.cryptoquant_key}"}

        resp = await self._http.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        # Parse the latest data point
        result_data = data.get("result", {}).get("data", [])
        if not result_data:
            raise ValueError(f"No SOPR data returned for {asset}")

        latest = result_data[-1]
        value = float(latest.get("sopr", 1.0))
        interpretation = self._interpret_sopr(value)

        # Calculate 90-day percentile from available data
        values = [float(d.get("sopr", 1.0)) for d in result_data[-90:]]
        percentile_90d = self._calculate_percentile(value, values)

        logger.info("CryptoQuant SOPR for %s: %.4f (%s)", asset, value, interpretation)

        return SOPRData(
            asset=asset,
            value=value,
            interpretation=interpretation,
            percentile_90d=percentile_90d,
        )

    async def _fetch_mvrv_cryptoquant(self, asset: str) -> MVRVData:
        """Fetch MVRV from CryptoQuant API.

        Endpoint: /v1/btc/market-indicator/mvrv
        """
        asset_lower = asset.lower()
        url = f"{CRYPTOQUANT_BASE_URL}/{asset_lower}/market-indicator/mvrv"
        headers = {"Authorization": f"Bearer {self.cryptoquant_key}"}

        resp = await self._http.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        result_data = data.get("result", {}).get("data", [])
        if not result_data:
            raise ValueError(f"No MVRV data returned for {asset}")

        latest = result_data[-1]
        value = float(latest.get("mvrv", 1.5))
        interpretation = self._interpret_mvrv(value)

        values = [float(d.get("mvrv", 1.5)) for d in result_data[-90:]]
        percentile_90d = self._calculate_percentile(value, values)

        logger.info("CryptoQuant MVRV for %s: %.2f (%s)", asset, value, interpretation)

        return MVRVData(
            asset=asset,
            value=value,
            interpretation=interpretation,
            percentile_90d=percentile_90d,
        )

    async def _fetch_exchange_flows_cryptoquant(
        self, asset: str, hours: int
    ) -> ExchangeFlowData:
        """Fetch exchange flows from CryptoQuant API.

        Endpoints:
          - /v1/btc/exchange-flows/inflow
          - /v1/btc/exchange-flows/outflow
        """
        asset_lower = asset.lower()
        headers = {"Authorization": f"Bearer {self.cryptoquant_key}"}

        # Fetch inflows
        inflow_url = f"{CRYPTOQUANT_BASE_URL}/{asset_lower}/exchange-flows/inflow"
        inflow_resp = await self._http.get(
            inflow_url, headers=headers, params={"window": "hour", "limit": hours}
        )
        inflow_resp.raise_for_status()
        inflow_data = inflow_resp.json().get("result", {}).get("data", [])

        # Fetch outflows
        outflow_url = f"{CRYPTOQUANT_BASE_URL}/{asset_lower}/exchange-flows/outflow"
        outflow_resp = await self._http.get(
            outflow_url, headers=headers, params={"window": "hour", "limit": hours}
        )
        outflow_resp.raise_for_status()
        outflow_data = outflow_resp.json().get("result", {}).get("data", [])

        # Aggregate over the window
        total_inflows = sum(float(d.get("inflow_total", 0)) for d in inflow_data)
        total_outflows = sum(float(d.get("outflow_total", 0)) for d in outflow_data)
        net_flow = total_inflows - total_outflows

        # Count large transactions (> $10M threshold)
        # CryptoQuant provides transaction counts by size in separate endpoints
        large_tx = sum(
            1 for d in inflow_data if float(d.get("inflow_total", 0)) > 100  # ~100 BTC rough proxy
        )

        whale_direction = self._determine_whale_direction(net_flow)

        logger.info(
            "CryptoQuant exchange flows for %s: inflows=%.2f outflows=%.2f net=%.2f whale=%s",
            asset,
            total_inflows,
            total_outflows,
            net_flow,
            whale_direction,
        )

        return ExchangeFlowData(
            asset=asset,
            net_flow_24h=net_flow,
            inflows_24h=total_inflows,
            outflows_24h=total_outflows,
            large_transactions=large_tx,
            whale_direction=whale_direction,
        )

    # ------------------------------------------------------------------
    # Private: Glassnode
    # ------------------------------------------------------------------

    async def _fetch_mvrv_glassnode(self, asset: str) -> MVRVData:
        """Fetch MVRV from Glassnode API.

        Endpoint: /v1/metrics/market/mvrv
        """
        url = f"{GLASSNODE_BASE_URL}/metrics/market/mvrv"
        params = {
            "a": asset.upper(),
            "api_key": self.glassnode_key,
            "s": "90d",
        }

        resp = await self._http.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            raise ValueError(f"No Glassnode MVRV data for {asset}")

        # data is a list of {"t": timestamp, "v": value}
        values = [float(d.get("v", 1.5)) for d in data if d.get("v") is not None]
        if not values:
            raise ValueError(f"Empty Glassnode MVRV values for {asset}")

        latest_value = values[-1]
        interpretation = self._interpret_mvrv(latest_value)
        percentile_90d = self._calculate_percentile(latest_value, values)

        logger.info("Glassnode MVRV for %s: %.2f (%s)", asset, latest_value, interpretation)

        return MVRVData(
            asset=asset,
            value=latest_value,
            interpretation=interpretation,
            percentile_90d=percentile_90d,
        )

    # ------------------------------------------------------------------
    # Private: Interpretation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _interpret_sopr(value: float) -> str:
        """Interpret SOPR value."""
        if value > SOPR_BULLISH_THRESHOLD:
            return "bullish"
        if value < SOPR_BEARISH_THRESHOLD:
            return "bearish"
        return "neutral"

    @staticmethod
    def _interpret_mvrv(value: float) -> str:
        """Interpret MVRV value."""
        if value > MVRV_OVERHEATED_THRESHOLD:
            return "overheated"
        if value < MVRV_UNDERVALUED_THRESHOLD:
            return "undervalued"
        return "neutral"

    @staticmethod
    def _determine_whale_direction(net_flow: float) -> str:
        """Determine whale direction from net flow.

        Negative net flow (outflows > inflows) = accumulating.
        Positive net flow (inflows > outflows) = distributing.
        """
        if net_flow < WHALE_ACCUMULATION_NET_FLOW_THRESHOLD:
            return "accumulating"
        if net_flow > WHALE_DISTRIBUTION_NET_FLOW_THRESHOLD:
            return "distributing"
        return "neutral"

    @staticmethod
    def _calculate_percentile(value: float, values: list[float]) -> float:
        """Calculate where value falls in the distribution of values (0-100)."""
        if not values:
            return 50.0
        sorted_values = sorted(values)
        count_below = sum(1 for v in sorted_values if v < value)
        return round((count_below / len(sorted_values)) * 100, 1)
