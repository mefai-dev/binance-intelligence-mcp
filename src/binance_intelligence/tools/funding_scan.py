"""Funding Rate Scanner.

Fetches premiumIndex (all symbols) + fundingInfo to produce a funding rate
heatmap: rate%, annualized APR, mark/index premium, minutes to next funding,
and direction for every futures pair. Sorted by absolute rate.
"""

import asyncio
import time
from typing import Any

from ..client import BinanceClient


async def scan_funding_rates(
    client: BinanceClient,
    top_n: int = 20,
) -> dict[str, Any]:
    """Scan all futures pairs for current funding rates.

    Returns ranked list sorted by absolute funding rate.
    """
    premium_data, funding_info_data = await asyncio.gather(
        client.premium_index_all(),
        client.funding_info(),
    )

    # Build lookup for funding info (interval, cap, floor)
    info_map: dict[str, dict] = {}
    for fi in funding_info_data:
        info_map[fi["symbol"]] = fi

    now_ms = int(time.time() * 1000)
    results = []

    for item in premium_data:
        symbol = item.get("symbol", "")
        rate = float(item.get("lastFundingRate", 0))
        mark = float(item.get("markPrice", 0))
        index_price = float(item.get("indexPrice", 0))
        next_funding_ms = int(item.get("nextFundingTime", 0))

        if mark == 0 or index_price == 0:
            continue

        # Premium = (mark - index) / index
        premium_pct = (mark - index_price) / index_price * 100

        # Minutes to next funding
        mins_to_next = max(0, (next_funding_ms - now_ms) / 60000)

        # Funding info details
        info = info_map.get(symbol, {})
        interval_hours = int(info.get("fundingIntervalHours", 8))

        # Annualized APR = rate * (24/interval) * 365
        periods_per_day = 24 / interval_hours if interval_hours > 0 else 3
        annualized_apr = rate * periods_per_day * 365 * 100

        # Direction
        if rate > 0.0001:
            direction = "LONGS_PAY"
        elif rate < -0.0001:
            direction = "SHORTS_PAY"
        else:
            direction = "NEUTRAL"

        results.append({
            "symbol": symbol,
            "funding_rate": round(rate * 100, 6),  # as percentage
            "annualized_apr": round(annualized_apr, 2),
            "mark_price": round(mark, 4),
            "index_price": round(index_price, 4),
            "premium_pct": round(premium_pct, 4),
            "mins_to_next_funding": round(mins_to_next, 1),
            "interval_hours": interval_hours,
            "direction": direction,
        })

    # Sort by absolute rate descending
    results.sort(key=lambda x: abs(x["funding_rate"]), reverse=True)

    # Summary statistics
    rates = [r["funding_rate"] for r in results]
    positive_count = sum(1 for r in rates if r > 0)
    negative_count = sum(1 for r in rates if r < 0)
    neutral_count = sum(1 for r in rates if r == 0)
    avg_rate = sum(rates) / len(rates) if rates else 0

    top_results = results[:top_n]

    return {
        "tool": "scan_funding_rates",
        "total_symbols": len(results),
        "showing": len(top_results),
        "summary": {
            "avg_rate_pct": round(avg_rate, 6),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "most_positive": results[0]["symbol"] if results and results[0]["funding_rate"] > 0 else (
                next((r["symbol"] for r in results if r["funding_rate"] > 0), None)
            ),
            "most_negative": next(
                (r["symbol"] for r in results if r["funding_rate"] < 0), None
            ),
        },
        "results": top_results,
    }
