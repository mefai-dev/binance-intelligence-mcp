"""Smart Accumulation Detector.

Combines klines, open interest history, premium index, and taker buy/sell ratio
to produce a composite accumulation score (0-100) per symbol.

Sub-scores:
  - volume_surge: Current volume vs 20-period moving average
  - oi_buildup: Linear regression slope of open interest (normalized)
  - stealth_mode: How close funding rate is to zero (quiet accumulation signal)
  - buyer_aggression: Taker buy ratio deviation from neutral (0.5)
"""

import asyncio
import statistics
from typing import Any

from ..client import BinanceClient, DEFAULT_SYMBOLS


def _linear_slope(values: list[float]) -> float:
    """Compute linear regression slope for a series."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = statistics.mean(values)
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


async def detect_accumulation(
    client: BinanceClient,
    symbols: list[str] | None = None,
) -> dict[str, Any]:
    """Detect smart accumulation across symbols.

    Returns a dict with per-symbol scores and a sorted ranking.
    """
    symbols = symbols or DEFAULT_SYMBOLS

    async def _analyze(symbol: str) -> dict:
        try:
            klines, oi_hist, premium, taker = await asyncio.gather(
                client.klines(symbol, "4h", 30),
                client.open_interest_hist(symbol, "4h", 30),
                client.premium_index(symbol),
                client.taker_buy_sell_ratio(symbol, "4h", 30),
            )
        except Exception as e:
            return {"symbol": symbol, "error": str(e)}

        # Volume surge: current volume / 20-period average
        volumes = [float(k[5]) for k in klines]  # k[5] = volume
        if len(volumes) < 2:
            return {"symbol": symbol, "error": "insufficient data"}

        avg_vol = statistics.mean(volumes[-20:]) if len(volumes) >= 20 else statistics.mean(volumes)
        current_vol = volumes[-1]
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
        volume_surge = _clamp((vol_ratio - 0.5) * 50, 0, 100)

        # OI buildup: slope of open interest values
        oi_values = [float(o["sumOpenInterest"]) for o in oi_hist]
        if oi_values:
            slope = _linear_slope(oi_values)
            mean_oi = statistics.mean(oi_values) if oi_values else 1.0
            normalized_slope = (slope / mean_oi * 100) if mean_oi > 0 else 0.0
            oi_buildup = _clamp(50 + normalized_slope * 500, 0, 100)
        else:
            oi_buildup = 50.0

        # Stealth mode: funding rate close to zero = stealth accumulation
        if isinstance(premium, list):
            premium = premium[0] if premium else {}
        funding_rate = float(premium.get("lastFundingRate", 0)) if isinstance(premium, dict) else 0.0
        stealth_mode = _clamp(100 - abs(funding_rate) * 10000, 0, 100)

        # Buyer aggression: taker buy ratio > 0.5 = buyers dominant
        taker_ratios = [float(t["buyVol"]) / (float(t["buyVol"]) + float(t["sellVol"]))
                        for t in taker
                        if float(t["buyVol"]) + float(t["sellVol"]) > 0]
        if taker_ratios:
            latest_ratio = taker_ratios[-1]
            buyer_aggression = _clamp((latest_ratio - 0.3) * 250, 0, 100)
        else:
            buyer_aggression = 50.0

        # Composite: weighted average
        composite = (
            volume_surge * 0.25
            + oi_buildup * 0.30
            + stealth_mode * 0.20
            + buyer_aggression * 0.25
        )

        return {
            "symbol": symbol,
            "scores": {
                "volume_surge": round(volume_surge, 1),
                "oi_buildup": round(oi_buildup, 1),
                "stealth_mode": round(stealth_mode, 1),
                "buyer_aggression": round(buyer_aggression, 1),
            },
            "composite": round(composite, 1),
            "signal": "STRONG" if composite >= 70 else "MODERATE" if composite >= 45 else "WEAK",
        }

    results = await asyncio.gather(*[_analyze(s) for s in symbols])
    valid = [r for r in results if "error" not in r]
    valid.sort(key=lambda x: x["composite"], reverse=True)

    return {
        "tool": "detect_accumulation",
        "count": len(valid),
        "results": valid,
        "errors": [r for r in results if "error" in r],
    }
