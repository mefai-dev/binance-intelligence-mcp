"""Pair Correlation Matrix.

Computes Pearson correlation coefficients between close prices
of multiple symbols over a configurable lookback period.
"""

import asyncio
import math
import statistics
from typing import Any

from ..client import BinanceClient, DEFAULT_SYMBOLS


def _pearson_r(x: list[float], y: list[float]) -> float:
    """Compute Pearson correlation coefficient between two equal-length series."""
    n = min(len(x), len(y))
    if n < 3:
        return 0.0
    x, y = x[:n], y[:n]
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)
    numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    denom_x = math.sqrt(sum((xi - x_mean) ** 2 for xi in x))
    denom_y = math.sqrt(sum((yi - y_mean) ** 2 for yi in y))
    if denom_x == 0 or denom_y == 0:
        return 0.0
    return numerator / (denom_x * denom_y)


async def compute_correlation_matrix(
    client: BinanceClient,
    symbols: list[str] | None = None,
    interval: str = "4h",
    limit: int = 90,
) -> dict[str, Any]:
    """Compute Pearson correlation matrix between symbols."""
    symbols = symbols or DEFAULT_SYMBOLS[:8]
    if len(symbols) < 2:
        return {"tool": "compute_correlation_matrix", "error": "need at least 2 symbols"}
    if len(symbols) > 20:
        symbols = symbols[:20]

    # Fetch all klines concurrently
    async def _fetch(symbol: str) -> tuple[str, list[float]]:
        try:
            klines = await client.klines(symbol, interval, limit)
            closes = [float(k[4]) for k in klines]
            return symbol, closes
        except Exception:
            return symbol, []

    fetched = await asyncio.gather(*[_fetch(s) for s in symbols])
    price_data = {sym: closes for sym, closes in fetched if closes}

    valid_symbols = [s for s in symbols if s in price_data]
    if len(valid_symbols) < 2:
        return {"tool": "compute_correlation_matrix", "error": "insufficient data"}

    # Build correlation matrix
    matrix = {}
    strong_pairs = []

    for i, sym_a in enumerate(valid_symbols):
        matrix[sym_a] = {}
        for j, sym_b in enumerate(valid_symbols):
            if i == j:
                matrix[sym_a][sym_b] = 1.0
            elif j < i:
                matrix[sym_a][sym_b] = matrix[sym_b][sym_a]
            else:
                r = _pearson_r(price_data[sym_a], price_data[sym_b])
                r = round(r, 4)
                matrix[sym_a][sym_b] = r
                if abs(r) >= 0.7:
                    strong_pairs.append({
                        "pair": f"{sym_a}/{sym_b}",
                        "correlation": r,
                        "type": "POSITIVE" if r > 0 else "NEGATIVE",
                    })

    strong_pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    return {
        "tool": "compute_correlation_matrix",
        "symbols": valid_symbols,
        "interval": interval,
        "lookback_periods": limit,
        "matrix": matrix,
        "strong_correlations": strong_pairs,
    }
