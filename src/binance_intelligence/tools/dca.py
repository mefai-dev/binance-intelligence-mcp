"""DCA Backtester.

Backtests a Dollar-Cost Averaging strategy against lump-sum investing
using historical daily kline data.

Computes:
  - Total invested amount
  - Total units accumulated (DCA vs lump-sum)
  - Current portfolio value
  - ROI percentage for both strategies
  - Comparison and winner declaration
"""

from typing import Any

from ..client import BinanceClient


async def backtest_dca(
    client: BinanceClient,
    symbol: str = "BTCUSDT",
    amount_per_interval: float = 100.0,
    interval_days: int = 7,
    total_days: int = 365,
) -> dict[str, Any]:
    """Backtest DCA vs lump-sum strategy.

    Args:
        symbol: Trading pair
        amount_per_interval: USD amount to invest each interval
        interval_days: Days between each purchase (e.g., 7 = weekly)
        total_days: Total lookback period in days
    """
    if interval_days < 1:
        return {"tool": "backtest_dca", "error": "interval_days must be >= 1"}
    if total_days < interval_days:
        return {"tool": "backtest_dca", "error": "total_days must be >= interval_days"}

    limit = min(total_days, 1000)  # Binance kline limit

    try:
        klines = await client.klines(symbol, "1d", limit)
    except Exception as e:
        return {"tool": "backtest_dca", "symbol": symbol, "error": str(e)}

    if len(klines) < 2:
        return {"tool": "backtest_dca", "symbol": symbol, "error": "insufficient data"}

    closes = [float(k[4]) for k in klines]
    current_price = closes[-1]
    start_price = closes[0]

    # DCA simulation
    dca_units = 0.0
    dca_invested = 0.0
    dca_buys = 0
    buy_prices = []

    for i in range(0, len(closes), interval_days):
        price = closes[i]
        units = amount_per_interval / price
        dca_units += units
        dca_invested += amount_per_interval
        dca_buys += 1
        buy_prices.append(price)

    dca_value = dca_units * current_price
    dca_roi = ((dca_value - dca_invested) / dca_invested * 100) if dca_invested > 0 else 0
    dca_avg_price = dca_invested / dca_units if dca_units > 0 else 0

    # Lump-sum simulation (invest total amount at start)
    lump_invested = dca_invested  # Same total investment for fair comparison
    lump_units = lump_invested / start_price
    lump_value = lump_units * current_price
    lump_roi = ((lump_value - lump_invested) / lump_invested * 100) if lump_invested > 0 else 0

    # Determine winner
    if dca_roi > lump_roi:
        winner = "DCA"
        advantage_pct = dca_roi - lump_roi
    elif lump_roi > dca_roi:
        winner = "LUMP_SUM"
        advantage_pct = lump_roi - dca_roi
    else:
        winner = "TIE"
        advantage_pct = 0

    # Price stats over the period
    price_min = min(closes)
    price_max = max(closes)
    price_change_pct = ((current_price - start_price) / start_price * 100) if start_price > 0 else 0

    return {
        "tool": "backtest_dca",
        "symbol": symbol,
        "period": {
            "total_days": len(closes),
            "interval_days": interval_days,
            "total_buys": dca_buys,
        },
        "dca": {
            "total_invested": round(dca_invested, 2),
            "total_units": round(dca_units, 6),
            "avg_buy_price": round(dca_avg_price, 4),
            "current_value": round(dca_value, 2),
            "profit_loss": round(dca_value - dca_invested, 2),
            "roi_pct": round(dca_roi, 2),
        },
        "lump_sum": {
            "total_invested": round(lump_invested, 2),
            "buy_price": start_price,
            "total_units": round(lump_units, 6),
            "current_value": round(lump_value, 2),
            "profit_loss": round(lump_value - lump_invested, 2),
            "roi_pct": round(lump_roi, 2),
        },
        "comparison": {
            "winner": winner,
            "advantage_pct": round(advantage_pct, 2),
        },
        "price_stats": {
            "start_price": start_price,
            "current_price": current_price,
            "min_price": price_min,
            "max_price": price_max,
            "price_change_pct": round(price_change_pct, 2),
        },
    }
