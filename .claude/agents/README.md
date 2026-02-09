# Sigma-Quant Agent Registry

Autonomous strategy research factory agent system. 44 agents organized by pipeline stage.

## Pipeline Architecture

```
RESEARCHER (14)  ->  CONVERTER (7)  ->  BACKTESTER (10)  ->  OPTIMIZER (13)
  Ideas & Alpha      PineScript->Py     Walk-Forward         Base Hit, Deploy
```

## Quick Reference

| Need | Agent |
|------|-------|
| Find trading ideas (futures) | `quant-idea-hunter` |
| Find trading ideas (crypto) | `quant-crypto-researcher` |
| Convert PineScript | `quant-pine-parser` -> `quant-pandas-adapter` |
| Run backtest | `quant-walk-forward` |
| Base Hit optimization | `quant-base-hit` -> `quant-loss-mfe` |
| Prop firm compliance | `quant-prop-firm-validator` |
| Exchange compliance (crypto) | `quant-exchange-validator` |
| Deploy to Freqtrade | `quant-freqtrade-deployer` |
| Risk modeling (crypto) | `quant-risk-modeler` |
| Funding rate analysis | `quant-funding-analyzer` |
| Liquidation tracking | `quant-liquidation-tracker` |
| On-chain signals | `quant-onchain-researcher` |
| Market making | `quant-market-maker` |
| Cross-exchange arb | `quant-arb-detector` |

---

## Researcher Agents (14)

Idea discovery, hypothesis generation, and alpha research.

| Agent | Description | Skills | Model |
|-------|-------------|--------|-------|
| `quant-idea-hunter` | Search web for trading ideas via EXA MCP | quant-research-methodology | sonnet |
| `quant-crypto-researcher` | Crypto idea hunting -- CryptoQuant, Glassnode, DeFi Llama | quant-crypto-research, quant-crypto-indicators | sonnet |
| `quant-funding-analyzer` | Funding rate mean-reversion, carry costs, delta-neutral | quant-funding-rate-strategies, quant-crypto-cost-modeling | sonnet |
| `quant-liquidation-tracker` | Liquidation cascade detection, OI divergence, heatmaps | quant-liquidation-analysis, quant-order-flow-analysis | sonnet |
| `quant-onchain-researcher` | On-chain signal aggregation -- SOPR, MVRV, exchange flows | quant-crypto-indicators | sonnet |
| `quant-market-maker` | Avellaneda-Stoikov for crypto perps, spread optimization | quant-market-making, quant-order-flow-analysis | sonnet |
| `quant-arb-detector` | Cross-exchange arbitrage, fee-adjusted profitability | quant-cross-exchange-arb, quant-data-abstraction | sonnet |
| `quant-combo-finder` | Find complementary indicator pairs (non-correlated signals) | quant-research-methodology | sonnet |
| `quant-hypothesis-writer` | Formulate testable hypotheses with edge rationale | quant-hypothesis-generation | sonnet |
| `quant-paper-analyzer` | Parse academic papers, extract trading methods | quant-research-methodology | sonnet |
| `quant-pattern-learner` | Load pattern files (what-works/what-fails) into context | quant-pattern-knowledge | sonnet |
| `quant-queue-pusher` | Atomic queue writes (hypothesis + conversion queues) | quant-queue-coordination | sonnet |
| `quant-tv-scraper` | Scrape TradingView indicators, extract PineScript | quant-pinescript-patterns | sonnet |
| `quant-edge-validator` | Pre-validate economic rationale before backtesting | quant-research-methodology | sonnet |

## Converter Agents (7)

PineScript-to-Python conversion pipeline.

| Agent | Description | Skills | Model |
|-------|-------------|--------|-------|
| `quant-pine-parser` | Parse PineScript into AST, extract structural components | quant-pinescript-patterns | sonnet |
| `quant-pandas-adapter` | Map PineScript functions to pandas-ta equivalents | quant-pinescript-patterns | sonnet |
| `quant-signal-extractor` | Convert visual patterns to buy/sell signal logic | quant-pinescript-patterns | sonnet |
| `quant-class-wrapper` | Generate Python indicator class with standard interface | quant-pinescript-patterns | sonnet |
| `quant-test-writer` | Generate pytest tests for converted indicators | quant-indicator-testing | sonnet |
| `quant-conversion-pusher` | Push converted indicator to backtest queue | quant-queue-coordination | sonnet |
| `quant-readme-gen` | Generate documentation for converted indicators | quant-pinescript-patterns | sonnet |

## Backtester Agents (10)

Walk-forward backtesting, validation, and metrics.

| Agent | Description | Skills | Model |
|-------|-------------|--------|-------|
| `quant-walk-forward` | Execute walk-forward optimization with rolling windows | quant-walk-forward-validation | sonnet |
| `quant-mfe-tracker` | Track Maximum Favorable Excursion per trade | quant-base-hit-analysis | sonnet |
| `quant-metrics-calc` | Calculate Sharpe, Sortino, max DD, win rate, etc. | quant-metrics-calculation | sonnet |
| `quant-cost-validator` | Validate trading costs are properly included | quant-cost-modeling | sonnet |
| `quant-oos-analyzer` | Calculate out-of-sample performance decay (IS vs OOS) | quant-overfitting-detection | sonnet |
| `quant-sample-validator` | Validate sufficient trade count for significance | quant-overfitting-detection | sonnet |
| `quant-overfit-checker` | Detect overfitting signals, auto-reject suspicious results | quant-overfitting-detection | sonnet |
| `quant-regime-detector` | Classify market regime during backtest period | quant-research-methodology | sonnet |
| `quant-reject-router` | Route failed strategies to rejected/ with failure logs | quant-artifact-routing | sonnet |
| `quant-results-logger` | Log all backtest results to output directory | quant-artifact-routing | sonnet |

## Optimizer Agents (13)

Post-backtest optimization, compliance, and deployment.

| Agent | Description | Skills | Model |
|-------|-------------|--------|-------|
| `quant-base-hit` | Calculate cash exit using Russian Doll framework | quant-base-hit-analysis | sonnet |
| `quant-loss-mfe` | Analyze losing trade MFE for optimal cash exit points | quant-base-hit-analysis | sonnet |
| `quant-coarse-grid` | Coarse parameter grid search for initial optimization | quant-parameter-optimization | sonnet |
| `quant-perturb-tester` | Test +/-20% parameter perturbation for robustness | quant-robustness-testing | sonnet |
| `quant-prop-firm-validator` | Test strategy against 14 prop firms | quant-prop-firm-compliance | sonnet |
| `quant-exchange-validator` | Exchange risk rule validation (leverage tiers, liquidation) | quant-exchange-compliance | sonnet |
| `quant-risk-modeler` | Crypto risk -- EVT VaR, liquidation cascade risk, fat tails | quant-liquidation-analysis, quant-exchange-compliance | sonnet |
| `quant-freqtrade-deployer` | Deploy to Freqtrade paper trading (IStrategy conversion) | quant-freqtrade-bridge | sonnet |
| `quant-firm-ranker` | Rank best prop firms for strategy compatibility | quant-prop-firm-compliance | sonnet |
| `quant-artifact-builder` | Build complete strategy package with all artifacts | quant-artifact-routing | sonnet |
| `quant-config-gen` | Generate strategy configuration files for deployment | quant-artifact-routing | sonnet |
| `quant-promo-router` | Route strategy to output based on quality tier | quant-artifact-routing | sonnet |
| `quant-notifier` | ElevenLabs voice notifications for pipeline events | quant-session-management | sonnet |

---

## Crypto Agents Summary

9 agents specifically designed for crypto perpetual futures trading across CEX (Binance, Bybit, OKX) and DEX (Hyperliquid).

| Agent | Domain | lib/crypto/ Module |
|-------|--------|--------------------|
| `quant-crypto-researcher` | Idea discovery | -- |
| `quant-funding-analyzer` | Funding rate strategies | `funding_rate_service.py` |
| `quant-liquidation-tracker` | Liquidation cascade detection | `liquidation_service.py` |
| `quant-onchain-researcher` | On-chain signal aggregation | `onchain_service.py` |
| `quant-market-maker` | Avellaneda-Stoikov market making | `market_maker_engine.py` |
| `quant-arb-detector` | Cross-exchange arbitrage | `arbitrage_detector.py` |
| `quant-exchange-validator` | Exchange compliance validation | `exchange_validator.py` |
| `quant-risk-modeler` | EVT VaR, fat-tail risk modeling | `risk_modeler.py` |
| `quant-freqtrade-deployer` | Freqtrade IStrategy deployment | `freqtrade_bridge.py` |

### Crypto Skill Coverage

| Skill | Used By |
|-------|---------|
| `quant-crypto-research` | quant-crypto-researcher |
| `quant-crypto-indicators` | quant-crypto-researcher, quant-onchain-researcher |
| `quant-crypto-cost-modeling` | quant-funding-analyzer |
| `quant-exchange-compliance` | quant-exchange-validator, quant-risk-modeler |
| `quant-market-making` | quant-market-maker |
| `quant-liquidation-analysis` | quant-liquidation-tracker, quant-risk-modeler |
| `quant-funding-rate-strategies` | quant-funding-analyzer |
| `quant-order-flow-analysis` | quant-liquidation-tracker, quant-market-maker |
| `quant-hyperliquid-adapter` | (available for any crypto agent) |
| `quant-freqtrade-bridge` | quant-freqtrade-deployer |
| `quant-cross-exchange-arb` | quant-arb-detector |

---

## All Skills (29)

| Skill | Domain |
|-------|--------|
| `quant-artifact-routing` | Strategy lifecycle routing |
| `quant-base-hit-analysis` | Russian Doll / MFE optimization |
| `quant-cost-modeling` | Futures cost models ($2.50/side) |
| `quant-cross-exchange-arb` | CEX/DEX arbitrage detection |
| `quant-crypto-cost-modeling` | Crypto fee models (maker/taker) |
| `quant-crypto-indicators` | On-chain + CEX/DEX indicators |
| `quant-crypto-research` | Crypto alpha discovery |
| `quant-data-abstraction` | Unified data layer (CCXT/Databento) |
| `quant-exchange-compliance` | Exchange risk rules |
| `quant-freqtrade-bridge` | Freqtrade IStrategy conversion |
| `quant-funding-rate-strategies` | Funding rate mean reversion |
| `quant-hyperliquid-adapter` | Hyperliquid DEX integration |
| `quant-hypothesis-generation` | Hypothesis card creation |
| `quant-indicator-testing` | Indicator accuracy testing |
| `quant-liquidation-analysis` | Cascade detection & OI analysis |
| `quant-market-making` | Avellaneda-Stoikov framework |
| `quant-metrics-calculation` | Sharpe, Sortino, DD, PBO |
| `quant-order-flow-analysis` | CVD, order flow imbalance |
| `quant-overfitting-detection` | OOS decay, overfit red flags |
| `quant-parameter-optimization` | Grid search, coarse tuning |
| `quant-pattern-knowledge` | What-works / what-fails patterns |
| `quant-pinescript-patterns` | PineScript AST patterns |
| `quant-prop-firm-compliance` | 14 prop firm rule sets |
| `quant-queue-coordination` | Atomic queue file operations |
| `quant-research-methodology` | De Prado / Chan methodology |
| `quant-robustness-testing` | Perturbation, stability checks |
| `quant-session-management` | Session state, notifications |
| `quant-walk-forward-validation` | Rolling window WF methodology |
| `renaissance-quant-principles` | RenTech-inspired principles |

---

## Project Structure

```
SigmaQuantStream/
  .claude/
    agents/          # 44 agent definitions (this directory)
    skills/          # 29 skill directories
    settings.json    # Tool permissions
  lib/
    crypto/          # Crypto exchange adapters & services
    indicators/      # Converted indicators
    strategies/      # Strategy implementations
  scripts/           # Research pipeline scripts
  output/            # Backtest results, artifacts
  queues/            # Hypothesis & conversion queues
  profiles/          # Market profiles (futures, crypto-cex, crypto-dex)
```

## Invocation

```bash
# Spawn any agent via Claude Code
claude --agent quant-crypto-researcher "Find funding rate strategies for BTC perps"
claude --agent quant-walk-forward "Backtest strategy at lib/strategies/funding_mr.py"
claude --agent quant-base-hit "Optimize backtest at output/funding_mr_results.json"
```
