#!/usr/bin/env python3
"""
QuantStream Setup Wizard
========================
Interactive first-run market selection wizard for the Quant Research Team.

Usage:
    python setup-wizard.py                  # Full interactive wizard
    python setup-wizard.py --reconfigure    # Re-run even if profile exists
    python setup-wizard.py --profile crypto-cex  # Switch to existing profile
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
STREAM_QUANT = PROJECT_ROOT / "stream-quant"
PROFILES_DIR = STREAM_QUANT / "profiles"
ACTIVE_PROFILE = PROFILES_DIR / "active-profile.json"
ENV_FILE = STREAM_QUANT / ".env"
ENV_EXAMPLE = STREAM_QUANT / ".env.example"

# ---------------------------------------------------------------------------
# Terminal colours (ANSI, works in every modern terminal)
# ---------------------------------------------------------------------------
class C:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    MAGENTA = "\033[0;35m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    NC = "\033[0m"


def banner():
    print(f"""
{C.CYAN}{C.BOLD}
 ╔══════════════════════════════════════════════════════════════╗
 ║        QuantStream Setup Wizard                             ║
 ║        Multi-Market Autonomous Research Factory              ║
 ╚══════════════════════════════════════════════════════════════╝
{C.NC}""")


def ask(prompt: str, choices: list[str] | None = None, default: str = "") -> str:
    """Ask a question, optionally showing numbered choices."""
    if choices:
        for i, ch in enumerate(choices, 1):
            print(f"  {C.CYAN}[{i}]{C.NC} {ch}")
        raw = input(f"\n  {C.BOLD}{prompt}{C.NC} [{default}]: ").strip()
        if not raw and default:
            return default
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            # Accept raw text too (e.g. the user types the name)
            lower = raw.lower()
            for ch in choices:
                if lower in ch.lower():
                    return ch
        print(f"  {C.YELLOW}Invalid selection, using default: {default}{C.NC}")
        return default
    else:
        raw = input(f"  {C.BOLD}{prompt}{C.NC} [{default}]: ").strip()
        return raw if raw else default


def ask_yn(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    raw = input(f"  {C.BOLD}{prompt}{C.NC} [{hint}]: ").strip().lower()
    if not raw:
        return default
    return raw.startswith("y")


def ok(msg: str):
    print(f"  {C.GREEN}\u2713{C.NC} {msg}")


def warn(msg: str):
    print(f"  {C.YELLOW}\u26a0{C.NC} {msg}")


def fail(msg: str):
    print(f"  {C.RED}\u2717{C.NC} {msg}")


def section(title: str):
    print(f"\n{C.BOLD}{C.BLUE}{'=' * 60}{C.NC}")
    print(f"  {C.BOLD}{title}{C.NC}")
    print(f"{C.BOLD}{C.BLUE}{'=' * 60}{C.NC}\n")


# ---------------------------------------------------------------------------
# Step 1 - Market Selection
# ---------------------------------------------------------------------------
MARKET_CHOICES = [
    "Futures (ES, NQ, YM, GC) \u2014 CME index & commodity futures",
    "Crypto - CEX (Binance, Bybit, OKX) \u2014 Centralized exchange perps/spot",
    "Crypto - DEX (Hyperliquid) \u2014 On-chain perpetuals",
    "Multiple markets (configure each)",
]

MARKET_MAP = {
    MARKET_CHOICES[0]: "futures",
    MARKET_CHOICES[1]: "crypto-cex",
    MARKET_CHOICES[2]: "crypto-dex",
    MARKET_CHOICES[3]: "multi",
}


def step_market_selection() -> list[str]:
    section("Step 1/5 \u2014 Market Selection")
    print(f"  {C.DIM}What market(s) do you want to research?{C.NC}\n")
    choice = ask("Select market", MARKET_CHOICES, MARKET_CHOICES[0])
    market = MARKET_MAP.get(choice, "futures")

    if market == "multi":
        markets = []
        for m in ["futures", "crypto-cex", "crypto-dex"]:
            if ask_yn(f"Include {m}?", default=(m == "futures")):
                markets.append(m)
        if not markets:
            markets = ["futures"]
        return markets
    return [market]


# ---------------------------------------------------------------------------
# Step 2 - Exchange / Provider (per market)
# ---------------------------------------------------------------------------
CEX_EXCHANGES = ["binance", "bybit", "okx", "kraken"]


def _validate_databento_key(key: str) -> bool:
    try:
        import requests
        resp = requests.get(
            "https://hist.databento.com/v0/metadata.list_datasets",
            auth=(key, ""),
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def _validate_ccxt_exchange(exchange: str, api_key: str = "", secret: str = "") -> bool:
    try:
        import ccxt  # type: ignore
        cls = getattr(ccxt, exchange, None)
        if cls is None:
            return False
        params = {"enableRateLimit": True}
        if api_key:
            params["apiKey"] = api_key
            params["secret"] = secret
        ex = cls(params)
        ex.load_markets()
        return True
    except ImportError:
        warn("ccxt not installed \u2014 install with: pip install ccxt")
        return False
    except Exception as e:
        warn(f"Exchange validation failed: {e}")
        return False


def _validate_hyperliquid() -> bool:
    try:
        import requests
        resp = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "meta"},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def step_exchange_provider(market: str) -> dict:
    section(f"Step 2/5 \u2014 Data Provider ({market})")
    provider: dict = {}

    if market == "futures":
        print(f"  {C.DIM}Databento provides historical + live CME futures data.{C.NC}")
        print(f"  {C.DIM}You can skip the API key to use sample data.{C.NC}\n")
        key = ask("Databento API key (or press Enter to skip)")
        if key:
            print(f"  {C.DIM}Validating...{C.NC}", end="", flush=True)
            if _validate_databento_key(key):
                ok("Databento key validated")
                provider = {
                    "adapter": "databento",
                    "apiKeyEnv": "DATABENTO_API_KEY",
                    "apiKeyValue": key,
                    "sampleDataDir": "data/",
                    "sampleFiles": ["ES_5min_sample.csv", "NQ_5min_sample.csv"],
                }
            else:
                warn("Validation failed \u2014 will use sample data as fallback")
                provider = {
                    "adapter": "databento",
                    "apiKeyEnv": "DATABENTO_API_KEY",
                    "sampleDataDir": "data/",
                    "sampleFiles": ["ES_5min_sample.csv", "NQ_5min_sample.csv"],
                }
        else:
            ok("Using sample data (no API key)")
            provider = {
                "adapter": "databento",
                "apiKeyEnv": "DATABENTO_API_KEY",
                "sampleDataDir": "data/",
                "sampleFiles": ["ES_5min_sample.csv", "NQ_5min_sample.csv"],
            }

    elif market == "crypto-cex":
        print(f"  {C.DIM}Select your preferred centralized exchange.{C.NC}\n")
        exchange = ask("Exchange", CEX_EXCHANGES, "binance")
        api_key = ask(f"{exchange} API key (optional, Enter to skip)")
        secret = ""
        if api_key:
            secret = ask(f"{exchange} API secret")

        print(f"  {C.DIM}Validating exchange connection...{C.NC}", end="", flush=True)
        valid = _validate_ccxt_exchange(exchange, api_key, secret)
        if valid:
            ok(f"{exchange} connection verified")
        else:
            warn(f"Could not validate {exchange} \u2014 proceeding anyway")

        provider = {
            "adapter": "ccxt",
            "exchange": exchange,
            "apiKeyEnv": f"{exchange.upper()}_API_KEY",
            "secretEnv": f"{exchange.upper()}_SECRET",
            "sampleDataDir": "data/crypto-cex/",
            "sampleFiles": [
                "BTCUSDT_5min_sample.csv",
                "ETHUSDT_5min_sample.csv",
            ],
        }
        if api_key:
            provider["apiKeyValue"] = api_key
            provider["secretValue"] = secret

    elif market == "crypto-dex":
        print(f"  {C.DIM}Hyperliquid uses public API for data \u2014 no key needed.{C.NC}\n")
        wallet = ask("Wallet address (optional, for trading later)")
        print(f"  {C.DIM}Checking Hyperliquid API...{C.NC}", end="", flush=True)
        if _validate_hyperliquid():
            ok("Hyperliquid API reachable")
        else:
            warn("Hyperliquid API unreachable \u2014 proceeding anyway")

        provider = {
            "adapter": "hyperliquid",
            "apiUrl": "https://api.hyperliquid.xyz",
            "sampleDataDir": "data/crypto-dex/",
            "sampleFiles": ["BTC_5min_sample.csv", "ETH_5min_sample.csv"],
        }
        if wallet:
            provider["wallet"] = wallet

    return provider


# ---------------------------------------------------------------------------
# Step 3 - Symbol Discovery
# ---------------------------------------------------------------------------
DEFAULT_SYMBOLS = {
    "futures": ["ES", "NQ", "YM", "GC", "CL", "RTY"],
    "crypto-cex": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"],
    "crypto-dex": ["BTC", "ETH", "SOL", "ARB", "DOGE"],
}


def _fetch_top_symbols_ccxt(exchange: str, limit: int = 20) -> list[dict]:
    """Fetch top symbols by 24h volume via ccxt."""
    try:
        import ccxt  # type: ignore
        cls = getattr(ccxt, exchange)
        ex = cls({"enableRateLimit": True})
        tickers = ex.fetch_tickers()
        # Filter USDT pairs, sort by quoteVolume
        usdt_tickers = [
            {"symbol": k, "volume_24h": v.get("quoteVolume", 0) or 0}
            for k, v in tickers.items()
            if k.endswith("/USDT") and v.get("quoteVolume")
        ]
        usdt_tickers.sort(key=lambda x: x["volume_24h"], reverse=True)
        return usdt_tickers[:limit]
    except Exception as e:
        warn(f"Could not fetch symbols: {e}")
        return []


def _fetch_top_symbols_hyperliquid(limit: int = 20) -> list[dict]:
    """Fetch available symbols from Hyperliquid."""
    try:
        import requests
        resp = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "meta"},
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        universe = data.get("universe", [])
        return [{"symbol": u["name"], "volume_24h": 0} for u in universe[:limit]]
    except Exception:
        return []


def _format_volume(vol: float) -> str:
    if vol >= 1_000_000_000:
        return f"${vol / 1_000_000_000:.1f}B"
    if vol >= 1_000_000:
        return f"${vol / 1_000_000:.1f}M"
    if vol >= 1_000:
        return f"${vol / 1_000:.0f}K"
    return f"${vol:.0f}"


def step_symbol_discovery(market: str, provider: dict) -> dict:
    section(f"Step 3/5 \u2014 Symbol Discovery ({market})")
    defaults = DEFAULT_SYMBOLS.get(market, [])
    discovered: list[dict] = []

    # Try dynamic discovery
    if market == "crypto-cex" and provider.get("adapter") == "ccxt":
        exchange = provider.get("exchange", "binance")
        print(f"  {C.DIM}Fetching top symbols from {exchange}...{C.NC}")
        discovered = _fetch_top_symbols_ccxt(exchange)
    elif market == "crypto-dex":
        print(f"  {C.DIM}Fetching Hyperliquid symbols...{C.NC}")
        discovered = _fetch_top_symbols_hyperliquid()

    if discovered:
        print(f"\n  {C.BOLD}Top symbols by volume:{C.NC}")
        for i, s in enumerate(discovered[:15], 1):
            vol = _format_volume(s["volume_24h"]) if s["volume_24h"] else "N/A"
            print(f"    {C.CYAN}{i:2d}.{C.NC} {s['symbol']:<15} {C.DIM}vol: {vol}{C.NC}")
        print()
        ok(f"Found {len(discovered)} symbols")
    else:
        if market != "futures":
            warn("Dynamic discovery unavailable \u2014 using defaults")
        else:
            ok("Futures symbols use contract roots (ES, NQ, etc.)")

    # Pinned symbols
    print(f"\n  {C.DIM}Pinned symbols are always included in research.{C.NC}")
    default_pinned = ",".join(defaults)
    raw = ask(f"Pinned symbols (comma-separated)", default=default_pinned)
    pinned = [s.strip() for s in raw.split(",") if s.strip()]

    # Excluded
    raw = ask("Excluded symbols (comma-separated, or Enter for none)", default="")
    excluded = [s.strip() for s in raw.split(",") if s.strip()]

    return {
        "mode": "dynamic",
        "discovery": {
            "method": "volume_rank",
            "maxSymbols": 20 if market.startswith("crypto") else 10,
            "refreshInterval": "24h",
        },
        "pinned": pinned,
        "excluded": excluded,
        "current": [s["symbol"] for s in discovered[:10]] if discovered else pinned,
    }


# ---------------------------------------------------------------------------
# Step 4 - Mode
# ---------------------------------------------------------------------------
def step_mode() -> str:
    section("Step 4/5 \u2014 Research Mode")
    modes = [
        "Research \u2014 Sample data, quick iterations, cheaper",
        "Production \u2014 Live data feeds, full historical, real costs",
    ]
    choice = ask("Select mode", modes, modes[0])
    return "research" if "Research" in choice else "production"


# ---------------------------------------------------------------------------
# Step 5 - Compliance
# ---------------------------------------------------------------------------
PROP_FIRMS = [
    "Apex", "Topstep", "TakeProfitTrader", "Earn2Trade", "Bulenox",
    "My Funded Futures", "Leeloo", "Trade Day", "UProfit",
    "Elite Trader Funding", "The Trading Pit", "Tradeify",
    "Funded Next", "OneUp Trader",
]


def step_compliance(market: str) -> dict:
    section(f"Step 5/5 \u2014 Compliance ({market})")

    if market == "futures":
        print(f"  {C.DIM}Select prop firms to validate strategies against.{C.NC}")
        print(f"  {C.DIM}Strategies must pass >= 3 firms for 'prop_firm_ready' status.{C.NC}\n")
        for i, f in enumerate(PROP_FIRMS, 1):
            print(f"    {C.CYAN}[{i:2d}]{C.NC} {f}")
        print(f"\n  {C.DIM}Enter numbers separated by commas, or 'all' for all firms.{C.NC}")
        raw = ask("Select firms", default="all")
        if raw.lower() == "all":
            selected = PROP_FIRMS[:]
        else:
            indices = []
            for part in raw.split(","):
                try:
                    idx = int(part.strip()) - 1
                    if 0 <= idx < len(PROP_FIRMS):
                        indices.append(idx)
                except ValueError:
                    pass
            selected = [PROP_FIRMS[i] for i in indices] if indices else PROP_FIRMS[:]

        ok(f"Selected {len(selected)} firms")
        return {
            "type": "prop-firm",
            "firms": selected,
            "minPassing": 3,
            "defaultAccountSizes": [50000, 100000],
        }

    else:  # crypto
        print(f"  {C.DIM}Set risk limits for crypto trading research.{C.NC}\n")
        max_lev = ask("Max leverage", default="20")
        pos_limit = ask("Max position size (USD)", default="100000")
        liq_buffer = ask("Liquidation buffer (%)", default="0.5")

        return {
            "type": "exchange-rules",
            "maxLeverage": int(max_lev),
            "positionLimitUSD": int(pos_limit),
            "liquidationBuffer": float(liq_buffer) / 100,
        }


# ---------------------------------------------------------------------------
# Cost model defaults
# ---------------------------------------------------------------------------
def default_costs(market: str) -> dict:
    if market == "futures":
        return {
            "model": "per_contract",
            "commission": 2.50,
            "slippage": 0.5,
            "slippageUnit": "ticks",
            "alwaysInclude": True,
        }
    elif market == "crypto-cex":
        return {
            "model": "percentage",
            "makerFee": 0.0002,
            "takerFee": 0.0005,
            "slippageBps": 5,
            "fundingRateAvg": 0.0001,
            "alwaysInclude": True,
        }
    else:  # crypto-dex
        return {
            "model": "percentage",
            "makerFee": 0.0002,
            "takerFee": 0.00035,
            "slippageBps": 10,
            "fundingRateAvg": 0.0001,
            "gasEstimate": 0.50,
            "alwaysInclude": True,
        }


# ---------------------------------------------------------------------------
# Build & save profile
# ---------------------------------------------------------------------------
def build_profile(
    market: str,
    provider: dict,
    symbols: dict,
    mode: str,
    compliance: dict,
) -> dict:
    """Assemble a complete profile JSON."""
    # Load base profile if it exists
    base_file = PROFILES_DIR / f"{market}.json"
    if base_file.exists():
        with open(base_file) as f:
            profile = json.load(f)
    else:
        profile = {}

    profile.update({
        "profileId": market,
        "displayName": _market_display_name(market),
        "marketType": market,
        "dataProvider": provider,
        "symbols": symbols,
        "costs": default_costs(market),
        "compliance": compliance,
        "mode": mode,
        "tradingHours": "CME" if market == "futures" else "24/7",
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    return profile


def _market_display_name(market: str) -> str:
    return {
        "futures": "CME Futures (ES, NQ, YM, GC)",
        "crypto-cex": "Crypto CEX (Centralized Exchange)",
        "crypto-dex": "Crypto DEX (Hyperliquid)",
    }.get(market, market)


def save_profile(profile: dict):
    """Write active-profile.json."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    with open(ACTIVE_PROFILE, "w") as f:
        json.dump(profile, f, indent=2)
    ok(f"Profile saved to {ACTIVE_PROFILE.relative_to(PROJECT_ROOT)}")


def save_env_keys(profile: dict):
    """Append any discovered API keys to .env (if not already there)."""
    provider = profile.get("dataProvider", {})
    lines_to_add = []
    key_val = provider.get("apiKeyValue")
    key_env = provider.get("apiKeyEnv")
    if key_val and key_env:
        lines_to_add.append(f"{key_env}={key_val}")
    secret_val = provider.get("secretValue")
    secret_env = provider.get("secretEnv")
    if secret_val and secret_env:
        lines_to_add.append(f"{secret_env}={secret_val}")

    if not lines_to_add:
        return

    existing = ""
    if ENV_FILE.exists():
        existing = ENV_FILE.read_text()

    new_lines = []
    for line in lines_to_add:
        env_name = line.split("=")[0]
        if env_name not in existing:
            new_lines.append(line)

    if new_lines:
        with open(ENV_FILE, "a") as f:
            f.write("\n".join(new_lines) + "\n")
        ok(f"API keys appended to {ENV_FILE.relative_to(PROJECT_ROOT)}")

    # Strip sensitive values from profile before saving
    if "apiKeyValue" in profile.get("dataProvider", {}):
        del profile["dataProvider"]["apiKeyValue"]
    if "secretValue" in profile.get("dataProvider", {}):
        del profile["dataProvider"]["secretValue"]


# ---------------------------------------------------------------------------
# Switch profile (--profile flag)
# ---------------------------------------------------------------------------
def switch_profile(name: str):
    """Activate an existing profile by name."""
    candidates = list(PROFILES_DIR.glob(f"{name}*"))
    if not candidates:
        fail(f"No profile matching '{name}' found in {PROFILES_DIR}")
        sys.exit(1)
    src = candidates[0]
    with open(src) as f:
        profile = json.load(f)
    save_profile(profile)
    print(f"\n  {C.GREEN}{C.BOLD}Switched to profile: {profile.get('displayName', name)}{C.NC}")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def print_summary(profile: dict):
    print(f"""
{C.GREEN}{C.BOLD}
 ╔══════════════════════════════════════════════════════════════╗
 ║                   Setup Complete!                            ║
 ╚══════════════════════════════════════════════════════════════╝
{C.NC}
  {C.BOLD}Market:{C.NC}     {profile.get('displayName', 'Unknown')}
  {C.BOLD}Mode:{C.NC}       {profile.get('mode', 'research')}
  {C.BOLD}Symbols:{C.NC}    {', '.join(profile.get('symbols', {}).get('pinned', []))}
  {C.BOLD}Provider:{C.NC}   {profile.get('dataProvider', {}).get('adapter', 'unknown')}
  {C.BOLD}Compliance:{C.NC} {profile.get('compliance', {}).get('type', 'none')}

  {C.BOLD}Next steps:{C.NC}
    1. Run health check:  {C.CYAN}python scripts/quant-team/health-check.py{C.NC}
    2. Download data:     {C.CYAN}python scripts/quant-team/download-data.py --help{C.NC}
    3. Launch team:       {C.CYAN}./scripts/quant-team/spawn-quant-team.sh{C.NC}
""")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="QuantStream Setup Wizard")
    parser.add_argument("--reconfigure", action="store_true", help="Re-run wizard even if profile exists")
    parser.add_argument("--profile", type=str, help="Switch to an existing profile by name")
    args = parser.parse_args()

    # Quick profile switch
    if args.profile:
        switch_profile(args.profile)
        return

    # Skip if already configured
    if ACTIVE_PROFILE.exists() and not args.reconfigure:
        with open(ACTIVE_PROFILE) as f:
            existing = json.load(f)
        print(f"\n  {C.GREEN}\u2713{C.NC} Active profile exists: {C.BOLD}{existing.get('displayName', 'Unknown')}{C.NC}")
        print(f"  {C.DIM}Run with --reconfigure to change settings.{C.NC}")
        print(f"  {C.DIM}Run with --profile <name> to switch profiles.{C.NC}\n")
        return

    banner()

    # Step 1: Market selection
    markets = step_market_selection()

    # For multi-market, run steps 2-5 per market and merge
    profiles = []
    for market in markets:
        provider = step_exchange_provider(market)
        symbols = step_symbol_discovery(market, provider)
        mode = step_mode() if market == markets[0] else profiles[0].get("mode", "research")
        compliance = step_compliance(market)
        profile = build_profile(market, provider, symbols, mode, compliance)
        profiles.append(profile)

    # Save primary profile (first market) as active
    primary = profiles[0]
    if len(profiles) > 1:
        primary["additionalMarkets"] = profiles[1:]

    save_env_keys(primary)
    save_profile(primary)
    print_summary(primary)

    # Also save individual market profiles for switching
    for p in profiles:
        market_file = PROFILES_DIR / f"{p['profileId']}.json"
        with open(market_file, "w") as f:
            json.dump(p, f, indent=2)


if __name__ == "__main__":
    main()
