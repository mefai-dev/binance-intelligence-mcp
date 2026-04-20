# binance-intelligence-mcp

[![CI](https://github.com/mefai-dev/binance-intelligence-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/mefai-dev/binance-intelligence-mcp/actions/workflows/ci.yml)


MCP server providing 12 computed intelligence tools for Binance. Unlike raw API wrappers, each tool combines multiple Binance endpoints into derived analytics ··· accumulation detection, whale tracking, market impact simulation, smart money radar, candlestick pattern scanning, correlation matrix, regime classification, DCA backtesting, funding rate scanning, funding extremes detection, funding history analysis, and basis spread scanning.

**No API keys needed** ··· all tools use public Binance endpoints.

## Installation

```bash
pip install binance-intelligence-mcp
```

Or install from source:

```bash
git clone https://github.com/mefai-dev/binance-intelligence-mcp.git
cd binance-intelligence-mcp
pip install .
```

## Quick Start

Run the server:

```bash
binance-intelligence-mcp
# or
python -m binance_intelligence
```

### MCP Client Configuration

Add to your MCP client config:

```json
{
  "mcpServers": {
    "binance-intelligence": {
      "command": "binance-intelligence-mcp"
    }
  }
}
```

Or with Python module:

```json
{
  "mcpServers": {
    "binance-intelligence": {
      "command": "python",
      "args": ["-m", "binance_intelligence"]
    }
  }
}
```

## Tools

| # | Tool | Description | Endpoints Used |
|---|------|-------------|----------------|
| 1 | `detect_accumulation` | Smart accumulation detector with 4 sub-scores | klines, openInterestHist, premiumIndex, takerBuySellRatio |
| 2 | `scan_whale_trades` | Large trade scanner with tier classification | aggTrades |
| 3 | `simulate_market_impact` | Order book walk simulator for slippage analysis | depth |
| 4 | `smart_money_radar` | 6-factor smart money composite score | topLongShortPositionRatio, topLongShortAccountRatio, globalLongShortAccountRatio, takerBuySellRatio, openInterestHist, klines |
| 5 | `scan_candlestick_patterns` | Classic pattern detection with confidence scores | klines |
| 6 | `compute_correlation_matrix` | Pearson correlation between trading pairs | klines |
| 7 | `classify_market_regime` | ADX and ATR based regime classification | klines, premiumIndex |
| 8 | `backtest_dca` | DCA vs lump sum backtester | klines |
| 9 | `scan_funding_rates` | Funding rate heatmap across all futures pairs | premiumIndex, fundingInfo |
| 10 | `detect_funding_extremes` | Extreme funding rate arbitrage opportunities | premiumIndex, fundingInfo |
| 11 | `analyze_funding_history` | Historical funding rate analysis for a symbol | fundingRate |
| 12 | `scan_basis_spread` | Spot futures basis spread (contango/backwardation) | premiumIndex |

### Tool Details

#### 1. `detect_accumulation`

Detects smart accumulation by combining volume analysis, open interest trends, funding rate proximity, and taker buy/sell ratio into a composite score (0-100).

**Parameters:**
- `symbols` (list[str], optional): Trading pairs. Default: top 12 futures pairs.

**Sub scores:**
- `volume_surge`: Current volume vs 20-period average
- `oi_buildup`: Open interest linear regression trend
- `stealth_mode`: Funding rate closeness to zero
- `buyer_aggression`: Taker buy ratio above neutral

**Example output:**
```json
{
  "tool": "detect_accumulation",
  "count": 3,
  "results": [
    {
      "symbol": "ETHUSDT",
      "scores": {
        "volume_surge": 72.5,
        "oi_buildup": 65.3,
        "stealth_mode": 89.0,
        "buyer_aggression": 58.2
      },
      "composite": 70.1,
      "signal": "STRONG"
    }
  ]
}
```

#### 2. `scan_whale_trades`

Scans recent aggregate trades to identify large orders. Classifies by tier: Dolphin ($50K-$250K), Whale ($250K-$1M), Mega (>$1M).

**Parameters:**
- `symbols` (list[str], optional): Trading pairs. Default: top 6 pairs.
- `min_usd` (float, optional): Minimum trade size. Default: 50000.

**Example output:**
```json
{
  "tool": "scan_whale_trades",
  "results": [
    {
      "symbol": "BTCUSDT",
      "trade_count": 15,
      "total_buy_usd": 2450000,
      "total_sell_usd": 1230000,
      "net_pressure_usd": 1220000,
      "net_direction": "BUY",
      "biggest_trade": {
        "usd_value": 1200000,
        "side": "BUY",
        "tier": "MEGA"
      },
      "tiers": {"dolphin": 8, "whale": 5, "mega": 2}
    }
  ]
}
```

#### 3. `simulate_market_impact`

Walks the live order book to simulate how a large market order would execute.

**Parameters:**
- `symbol` (str): Trading pair. Default: "BTCUSDT".
- `side` (str): "BUY" or "SELL".
- `amount_usd` (float): Order size in USD. Default: 100000.

**Example output:**
```json
{
  "tool": "simulate_market_impact",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "levels_consumed": 12,
  "avg_fill_price": 67542.30,
  "worst_fill_price": 67580.00,
  "slippage_pct": 0.056,
  "impact_rating": "MODERATE"
}
```

#### 4. `smart_money_radar`

Combines 6 independent data factors into a composite score (0-100).

**Parameters:**
- `symbols` (list[str], optional): Default: top 12 pairs.

**Factors (each scored -1 to +1):**
1. Top trader position ratio
2. Top trader account ratio
3. Global long/short account ratio
4. Taker buy/sell ratio
5. Open interest trend
6. Price momentum

#### 5. `scan_candlestick_patterns`

Detects classic candlestick patterns with confidence scores.

**Parameters:**
- `symbols` (list[str], optional): Default: top 12 pairs.
- `interval` (str): "1h" or "4h". Default: "4h".

**Detected patterns:** Hammer, Inverted Hammer, Bullish/Bearish Engulfing, Doji, Morning/Evening Star, Three White Soldiers, Three Black Crows.

#### 6. `compute_correlation_matrix`

Computes Pearson correlation coefficients between close prices of multiple symbols.

**Parameters:**
- `symbols` (list[str], optional): 2-20 pairs. Default: top 8.
- `interval` (str): Default: "4h".
- `limit` (int): Lookback periods. Default: 90.

#### 7. `classify_market_regime`

Classifies each symbol into one of four regimes using ADX, ATR, and volume analysis.

**Parameters:**
- `symbols` (list[str], optional): Default: top 12 pairs.

**Regimes:**
- `TRENDING`: Strong directional movement (ADX >= 25)
- `RANGING`: Low directional movement
- `VOLATILE_BREAKOUT`: High ADX + high ATR
- `LOW_ACTIVITY`: Low volume and volatility

#### 8. `backtest_dca`

Backtests Dollar-Cost Averaging vs lump sum investing over historical data.

**Parameters:**
- `symbol` (str): Default: "BTCUSDT".
- `amount_per_interval` (float): USD per purchase. Default: 100.
- `interval_days` (int): Days between purchases. Default: 7 (weekly).
- `total_days` (int): Historical lookback. Default: 365.

#### 9. `scan_funding_rates`

Scans all futures pairs for current funding rates, producing a heatmap sorted by absolute rate.

**Parameters:**
- `top_n` (int, optional): Number of results. Default: 20.

**Output includes:** rate%, annualized APR, mark/index premium, minutes to next funding, direction (LONGS_PAY/SHORTS_PAY/NEUTRAL).

#### 10. `detect_funding_extremes`

Detects extreme funding rates across all pairs with severity classification and arbitrage hints.

**Severity levels:** ELEVATED (>0.03%), HIGH (>0.05%), EXTREME (>0.1%)

**Output includes:** severity, opportunity score, urgency (IMMINENT/SOON/UPCOMING), arbitrage hint.

#### 11. `analyze_funding_history`

Analyzes historical funding rates for a single symbol with comprehensive statistics.

**Parameters:**
- `symbol` (str): Default: "BTCUSDT".
- `limit` (int): Historical periods. Default: 500.

**Output includes:** average/median/std dev, trend direction, cumulative cost, annualized cost, volatility score (0-100), distribution.

#### 12. `scan_basis_spread`

Scans spot-futures basis spread across all pairs, identifying contango and backwardation.

**Parameters:**
- `top_n` (int, optional): Number of results. Default: 20.

**Output includes:** basis%, state (CONTANGO/BACKWARDATION/FLAT), annualized basis from funding rates.

## Architecture

```
··�·····················································································································································�
··�                 MCP Client                       ··�
··�         (any MCP-compatible client)              ··�
···························································�····························································································�
                   ··� stdio (JSON-RPC)
··�·······················································��····························································································�
··�              server.py (FastMCP)                  ··�
··�        12 @mcp.tool() functions                  ··�
···························································�····························································································�
                   ··�
··�·······················································��····························································································�
··�              tools/*.py                          ··�
··�   Pure async functions with scoring algorithms   ··�
··�                                                  ··�
··�  accumulation ··� whale    ··� impact   ··� smart_money ··�
··�  patterns     ··� correlation ··� regime ··� dca        ··�
···························································�····························································································�
                   ··�
··�·······················································��····························································································�
··�            client.py (BinanceClient)             ··�
··�   Async aiohttp ··� Rate limiting ··� No API key     ··�
···························································�····························································································�
                   ··� HTTPS
··�·······················································��····························································································�
··�         Binance Public API                       ··�
··�   api.binance.com ··� fapi.binance.com             ··�
························································································································································�
```

## Binance Endpoints Used

All endpoints are **public** and require no authentication:

| Endpoint | Type | Used By |
|----------|------|---------|
| `/fapi/v1/klines` | Futures | accumulation, smart_money, patterns, correlation, regime, dca |
| `/fapi/v1/aggTrades` | Futures | whale |
| `/fapi/v1/depth` | Futures | impact |
| `/fapi/v1/premiumIndex` | Futures | accumulation, regime, funding_scan, funding_extremes, basis_spread |
| `/futures/data/openInterestHist` | Futures | accumulation, smart_money |
| `/futures/data/topLongShortPositionRatio` | Futures | smart_money |
| `/futures/data/topLongShortAccountRatio` | Futures | smart_money |
| `/futures/data/globalLongShortAccountRatio` | Futures | smart_money |
| `/futures/data/takerlongshortRatio` | Futures | accumulation, smart_money |
| `/fapi/v1/fundingInfo` | Futures | funding_scan, funding_extremes |
| `/fapi/v1/fundingRate` | Futures | funding_history |
| `/api/v3/klines` | Spot | (available) |

## Development

```bash
git clone https://github.com/mefai-dev/binance-intelligence-mcp.git
cd binance-intelligence-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e . pytest pytest-asyncio
```

Run tests:

```bash
pytest tests/ -v
```

All tests are mock-based ··· no API keys or network access needed.

## License

MIT
