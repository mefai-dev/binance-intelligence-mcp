"""Market Regime Classifier.

Classifies market regime using ADX, ATR, and volume analysis:
  - Trending (high ADX, directional movement)
  - Ranging (low ADX, low volatility)
  - Volatile Breakout (high ATR, expanding volume)
  - Low Activity (low volume, low ATR)

Also reports funding rate for futures context.
"""

import asyncio
import statistics
from typing import Any

from ..client import BinanceClient, DEFAULT_SYMBOLS


def _true_range(candles: list[dict]) -> list[float]:
    """Compute True Range series from candle dicts."""
    tr = []
    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        prev_c = candles[i - 1]["close"]
        tr.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    return tr


def _smoothed_avg(values: list[float], period: int = 14) -> list[float]:
    """Wilder's smoothing (exponential-like)."""
    if len(values) < period:
        return [statistics.mean(values)] if values else [0.0]
    result = [statistics.mean(values[:period])]
    for v in values[period:]:
        result.append((result[-1] * (period - 1) + v) / period)
    return result


def _compute_adx(candles: list[dict], period: int = 14) -> dict:
    """Compute ADX, +DI, -DI from candle data."""
    if len(candles) < period + 2:
        return {"adx": 0, "plus_di": 0, "minus_di": 0}

    plus_dm = []
    minus_dm = []
    tr = []

    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        prev_h = candles[i - 1]["high"]
        prev_l = candles[i - 1]["low"]
        prev_c = candles[i - 1]["close"]

        up_move = h - prev_h
        down_move = prev_l - l

        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0)
        tr.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))

    smooth_tr = _smoothed_avg(tr, period)
    smooth_plus = _smoothed_avg(plus_dm, period)
    smooth_minus = _smoothed_avg(minus_dm, period)

    # Use the last smoothed values
    atr_val = smooth_tr[-1] if smooth_tr else 1
    plus_di = (smooth_plus[-1] / atr_val * 100) if atr_val > 0 else 0
    minus_di = (smooth_minus[-1] / atr_val * 100) if atr_val > 0 else 0

    di_sum = plus_di + minus_di
    dx = abs(plus_di - minus_di) / di_sum * 100 if di_sum > 0 else 0

    # ADX = smoothed DX (simplified: use dx directly for single value)
    return {
        "adx": round(dx, 2),
        "plus_di": round(plus_di, 2),
        "minus_di": round(minus_di, 2),
    }


async def classify_market_regime(
    client: BinanceClient,
    symbols: list[str] | None = None,
) -> dict[str, Any]:
    """Classify market regime for each symbol."""
    symbols = symbols or DEFAULT_SYMBOLS

    async def _classify(symbol: str) -> dict:
        try:
            klines, premium = await asyncio.gather(
                client.klines(symbol, "1h", 168),
                client.premium_index(symbol),
            )
        except Exception as e:
            return {"symbol": symbol, "error": str(e)}

        candles = [
            {"open": float(k[1]), "high": float(k[2]),
             "low": float(k[3]), "close": float(k[4]),
             "volume": float(k[5])}
            for k in klines
        ]

        if len(candles) < 20:
            return {"symbol": symbol, "error": "insufficient data"}

        # ADX computation
        adx_data = _compute_adx(candles)
        adx = adx_data["adx"]

        # ATR (14-period)
        tr_values = _true_range(candles)
        atr = statistics.mean(tr_values[-14:]) if len(tr_values) >= 14 else (
            statistics.mean(tr_values) if tr_values else 0
        )
        avg_price = statistics.mean([c["close"] for c in candles[-14:]])
        atr_pct = (atr / avg_price * 100) if avg_price > 0 else 0

        # Volume trend
        volumes = [c["volume"] for c in candles]
        recent_vol = statistics.mean(volumes[-24:]) if len(volumes) >= 24 else statistics.mean(volumes)
        older_vol = statistics.mean(volumes[-72:-24]) if len(volumes) >= 72 else (
            statistics.mean(volumes[:len(volumes) // 2]) if len(volumes) >= 2 else recent_vol
        )
        vol_change = ((recent_vol - older_vol) / older_vol * 100) if older_vol > 0 else 0

        # Funding rate (premium may be a dict or list depending on API response)
        if isinstance(premium, list):
            premium = premium[0] if premium else {}
        funding = float(premium.get("lastFundingRate", 0)) if isinstance(premium, dict) else 0.0

        # Classification logic
        if adx >= 40 and atr_pct >= 1.5:
            regime = "VOLATILE_BREAKOUT"
        elif adx >= 25:
            regime = "TRENDING"
        elif atr_pct < 0.5 and abs(vol_change) < 20:
            regime = "LOW_ACTIVITY"
        else:
            regime = "RANGING"

        # Direction for trending
        direction = None
        if regime in ("TRENDING", "VOLATILE_BREAKOUT"):
            direction = "UP" if adx_data["plus_di"] > adx_data["minus_di"] else "DOWN"

        return {
            "symbol": symbol,
            "regime": regime,
            "direction": direction,
            "indicators": {
                "adx": adx_data["adx"],
                "plus_di": adx_data["plus_di"],
                "minus_di": adx_data["minus_di"],
                "atr": round(atr, 4),
                "atr_pct": round(atr_pct, 3),
                "volume_change_pct": round(vol_change, 2),
                "funding_rate": round(funding, 6),
            },
        }

    results = await asyncio.gather(*[_classify(s) for s in symbols])
    valid = [r for r in results if "error" not in r]

    # Group by regime
    regime_groups = {}
    for r in valid:
        regime = r["regime"]
        if regime not in regime_groups:
            regime_groups[regime] = []
        regime_groups[regime].append(r["symbol"])

    return {
        "tool": "classify_market_regime",
        "count": len(valid),
        "regime_summary": regime_groups,
        "results": valid,
        "errors": [r for r in results if "error" in r],
    }
