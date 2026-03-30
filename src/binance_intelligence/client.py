"""Async Binance API client — public endpoints only, no API key needed."""

import asyncio
import os
from typing import Any

import aiohttp

SPOT_BASE = "https://api.binance.com"
FUTURES_BASE = "https://fapi.binance.com"

# Default symbols used across tools
DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT", "LINKUSDT", "LTCUSDT",
]

# Proxy routing for geo-restricted environments
# Maps Binance API path prefixes to proxy base URLs
_PROXY_FRANKFURT = os.environ.get("MEFAI_PROXY_FRANKFURT", "")
_PROXY_AUTOTRADE = os.environ.get("MEFAI_PROXY_AUTOTRADE", "")
_PROXY_TESTNET = "https://testnet.binancefuture.com"

# Path → (proxy_base, rewritten_path_or_None)
_PROXY_ROUTES: dict[str, tuple[str, str | None]] = {
    "/fapi/v1/klines": (_PROXY_FRANKFURT, "/fapi/klines"),
    "/fapi/v1/premiumIndex": (_PROXY_FRANKFURT, "/fapi/premiumIndex"),
    "/fapi/v1/fundingInfo": (_PROXY_AUTOTRADE, None),
    "/fapi/v1/fundingRate": (_PROXY_AUTOTRADE, None),
    "/fapi/v1/aggTrades": (_PROXY_TESTNET, None),
    "/fapi/v1/depth": (_PROXY_TESTNET, None),
    "/futures/data/openInterestHist": (_PROXY_AUTOTRADE, None),
    "/futures/data/topLongShortPositionRatio": (_PROXY_AUTOTRADE, None),
    "/futures/data/topLongShortAccountRatio": (_PROXY_AUTOTRADE, None),
    "/futures/data/globalLongShortAccountRatio": (_PROXY_FRANKFURT, None),
    "/futures/data/takerlongshortRatio": (_PROXY_AUTOTRADE, None),
}


class BinanceClient:
    """Async Binance API client for public market data endpoints.

    All endpoints used are public and require no API key.
    Rate limiting is enforced via an asyncio Semaphore.

    If ``proxy_base`` is set (or BINANCE_PROXY env var), proxy routing is
    enabled for all futures requests to bypass geo-restrictions.
    """

    def __init__(self, max_concurrent: int = 10, proxy_base: str | None = None):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._session: aiohttp.ClientSession | None = None
        self._use_proxies = bool(proxy_base or os.environ.get("BINANCE_PROXY", ""))

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, base: str, path: str, params: dict | None = None) -> Any:
        session = await self._get_session()
        # Try proxy routing for futures requests when proxies are enabled
        if self._use_proxies and base == FUTURES_BASE and path in _PROXY_ROUTES:
            proxy_base, rewritten = _PROXY_ROUTES[path]
            proxy_url = f"{proxy_base}{rewritten or path}"
            try:
                async with self._semaphore:
                    async with session.get(proxy_url, params=params) as resp:
                        if resp.status == 200:
                            return await resp.json()
            except Exception:
                pass  # Fall through to direct API
        async with self._semaphore:
            async with session.get(f"{base}{path}", params=params) as resp:
                resp.raise_for_status()
                return await resp.json()

    # ── Spot endpoints ──

    async def spot_klines(
        self, symbol: str, interval: str = "4h", limit: int = 30
    ) -> list[list]:
        """Fetch spot klines/candlestick data."""
        return await self._request(
            SPOT_BASE, "/api/v3/klines",
            {"symbol": symbol, "interval": interval, "limit": limit},
        )

    # ── Futures endpoints ──

    async def klines(
        self, symbol: str, interval: str = "4h", limit: int = 30
    ) -> list[list]:
        """Fetch futures klines/candlestick data."""
        return await self._request(
            FUTURES_BASE, "/fapi/v1/klines",
            {"symbol": symbol, "interval": interval, "limit": limit},
        )

    async def agg_trades(self, symbol: str, limit: int = 500) -> list[dict]:
        """Fetch recent aggregate trades."""
        return await self._request(
            FUTURES_BASE, "/fapi/v1/aggTrades",
            {"symbol": symbol, "limit": limit},
        )

    async def depth(self, symbol: str, limit: int = 1000) -> dict:
        """Fetch order book depth."""
        return await self._request(
            FUTURES_BASE, "/fapi/v1/depth",
            {"symbol": symbol, "limit": limit},
        )

    async def premium_index_all(self) -> list[dict]:
        """Fetch premium index for all symbols (no symbol param)."""
        return await self._request(
            FUTURES_BASE, "/fapi/v1/premiumIndex", {},
        )

    async def funding_info(self) -> list[dict]:
        """Fetch funding rate info (cap, floor, interval) for all symbols."""
        return await self._request(
            FUTURES_BASE, "/fapi/v1/fundingInfo", {},
        )

    async def funding_rate_history(
        self, symbol: str, limit: int = 500
    ) -> list[dict]:
        """Fetch funding rate history for a symbol."""
        return await self._request(
            FUTURES_BASE, "/fapi/v1/fundingRate",
            {"symbol": symbol, "limit": limit},
        )

    async def premium_index(self, symbol: str) -> dict:
        """Fetch premium index (includes funding rate)."""
        return await self._request(
            FUTURES_BASE, "/fapi/v1/premiumIndex",
            {"symbol": symbol},
        )

    async def open_interest_hist(
        self, symbol: str, period: str = "4h", limit: int = 30
    ) -> list[dict]:
        """Fetch open interest statistics history."""
        return await self._request(
            FUTURES_BASE, "/futures/data/openInterestHist",
            {"symbol": symbol, "period": period, "limit": limit},
        )

    async def top_long_short_position_ratio(
        self, symbol: str, period: str = "4h", limit: int = 30
    ) -> list[dict]:
        """Fetch top trader long/short position ratio."""
        return await self._request(
            FUTURES_BASE, "/futures/data/topLongShortPositionRatio",
            {"symbol": symbol, "period": period, "limit": limit},
        )

    async def top_long_short_account_ratio(
        self, symbol: str, period: str = "4h", limit: int = 30
    ) -> list[dict]:
        """Fetch top trader long/short account ratio."""
        return await self._request(
            FUTURES_BASE, "/futures/data/topLongShortAccountRatio",
            {"symbol": symbol, "period": period, "limit": limit},
        )

    async def global_long_short_account_ratio(
        self, symbol: str, period: str = "4h", limit: int = 30
    ) -> list[dict]:
        """Fetch global long/short account ratio."""
        return await self._request(
            FUTURES_BASE, "/futures/data/globalLongShortAccountRatio",
            {"symbol": symbol, "period": period, "limit": limit},
        )

    async def taker_buy_sell_ratio(
        self, symbol: str, period: str = "4h", limit: int = 30
    ) -> list[dict]:
        """Fetch taker buy/sell volume ratio."""
        return await self._request(
            FUTURES_BASE, "/futures/data/takerlongshortRatio",
            {"symbol": symbol, "period": period, "limit": limit},
        )


WEIGHT_LIMITS = {
    "klines": 2,
    "depth": 5,
    "trades": 2,
    "ticker": 2,
    "avgPrice": 2,
}

def estimate_weight(endpoint: str, params: dict = None) -> int:
    """Estimate the request weight for rate limit tracking."""
    base = WEIGHT_LIMITS.get(endpoint, 1)
    if params and "limit" in params:
        limit = int(params["limit"])
        if limit > 500:
            base *= 2
        if limit > 1000:
            base *= 5
    return base
