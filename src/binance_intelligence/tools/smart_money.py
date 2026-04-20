"""Smart Money Radar (6-factor composite).

Combines 6 data sources into individual factor scores (-1 to +1),
then produces a weighted composite score (0-100).

Factors:
  1. Top Trader Position Ratio ··· are top traders net long or short?
  2. Top Trader Account Ratio ··· what fraction of top accounts are long?
  3. Global L/S Account Ratio ··· retail sentiment
  4. Taker Buy/Sell Ratio ··· aggressive market orders direction
  5. Open Interest Trend ··· is money flowing in or out?
  6. Price Momentum ··· recent price change direction
"""

import asyncio
import statistics
from typing import Any

from ..client import BinanceClient, DEFAULT_SYMBOLS


def _normalize_ratio(value: float, neutral: float = 1.0) -> float:
    """Normalize a ratio around a neutral point to [-1, +1]."""
    if neutral == 0:
        return 0.0
    deviation = (value - neutral) / neutral
    return max(-1.0, min(1.0, deviation * 2))


def _trend_score(values: list[float]) -> float:
    """Score trend direction as -1 to +1 based on recent vs older average."""
    if len(values) < 4:
        return 0.0
    mid = len(values) // 2
    old_avg = statistics.mean(values[:mid])
    new_avg = statistics.mean(values[mid:])
    if old_avg == 0:
        return 0.0
    change = (new_avg - old_avg) / old_avg
    return max(-1.0, min(1.0, change * 5))


async def smart_money_radar(
    client: BinanceClient,
    symbols: list[str] | None = None,
) -> dict[str, Any]:
    """Compute 6-factor smart money score for each symbol."""
    symbols = symbols or DEFAULT_SYMBOLS

    async def _analyze(symbol: str) -> dict:
        try:
            pos_ratio, acc_ratio, global_ratio, taker, oi_hist, klines = (
                await asyncio.gather(
                    client.top_long_short_position_ratio(symbol, "4h", 30),
                    client.top_long_short_account_ratio(symbol, "4h", 30),
                    client.global_long_short_account_ratio(symbol, "4h", 30),
                    client.taker_buy_sell_ratio(symbol, "4h", 30),
                    client.open_interest_hist(symbol, "4h", 30),
                    client.klines(symbol, "4h", 30),
                )
            )
        except Exception as e:
            return {"symbol": symbol, "error": str(e)}

        # Factor 1: Top trader position ratio
        pos_values = [float(r["longShortRatio"]) for r in pos_ratio]
        f1 = _normalize_ratio(pos_values[-1], 1.0) if pos_values else 0.0

        # Factor 2: Top trader account ratio
        acc_values = [float(r["longShortRatio"]) for r in acc_ratio]
        f2 = _normalize_ratio(acc_values[-1], 1.0) if acc_values else 0.0

        # Factor 3: Global L/S account ratio
        global_values = [float(r["longShortRatio"]) for r in global_ratio]
        f3 = _normalize_ratio(global_values[-1], 1.0) if global_values else 0.0

        # Factor 4: Taker buy/sell ratio
        taker_values = [float(r["buySellRatio"]) for r in taker]
        f4 = _normalize_ratio(taker_values[-1], 1.0) if taker_values else 0.0

        # Factor 5: OI trend
        oi_values = [float(o["sumOpenInterest"]) for o in oi_hist]
        f5 = _trend_score(oi_values)

        # Factor 6: Price momentum
        closes = [float(k[4]) for k in klines]
        f6 = _trend_score(closes)

        # Weighted composite (map from -1..+1 range to 0..100)
        weights = [0.20, 0.15, 0.10, 0.20, 0.20, 0.15]
        factors = [f1, f2, f3, f4, f5, f6]
        raw = sum(w * f for w, f in zip(weights, factors))
        composite = max(0.0, min(100.0, (raw + 1) * 50))

        return {
            "symbol": symbol,
            "factors": {
                "top_position_ratio": round(f1, 3),
                "top_account_ratio": round(f2, 3),
                "global_ls_ratio": round(f3, 3),
                "taker_ratio": round(f4, 3),
                "oi_trend": round(f5, 3),
                "price_momentum": round(f6, 3),
            },
            "composite": round(composite, 1),
            "bias": "BULLISH" if composite >= 60 else "BEARISH" if composite <= 40 else "NEUTRAL",
        }

    results = await asyncio.gather(*[_analyze(s) for s in symbols])
    valid = [r for r in results if "error" not in r]
    valid.sort(key=lambda x: x["composite"], reverse=True)

    return {
        "tool": "smart_money_radar",
        "count": len(valid),
        "results": valid,
        "errors": [r for r in results if "error" in r],
    }
