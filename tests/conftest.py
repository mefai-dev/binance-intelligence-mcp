"""Shared fixtures and mock data for Binance Intelligence tests."""

import pytest
from unittest.mock import AsyncMock

from binance_intelligence.client import BinanceClient


def make_kline(
    open_: float = 100.0, high: float = 105.0, low: float = 95.0,
    close: float = 102.0, volume: float = 1000.0, timestamp: int = 1700000000000,
) -> list:
    """Create a single kline entry matching Binance format."""
    return [
        timestamp,       # 0: open time
        str(open_),      # 1: open
        str(high),       # 2: high
        str(low),        # 3: low
        str(close),      # 4: close
        str(volume),     # 5: volume
        timestamp + 3600000,  # 6: close time
        str(volume * close),  # 7: quote asset volume
        100,             # 8: number of trades
        str(volume * 0.6),    # 9: taker buy base volume
        str(volume * 0.6 * close),  # 10: taker buy quote volume
        "0",             # 11: ignore
    ]


def make_klines(count: int = 30, base_price: float = 100.0, trend: float = 0.5) -> list[list]:
    """Generate a series of klines with optional trend."""
    klines = []
    price = base_price
    for i in range(count):
        o = price
        c = price + trend
        h = max(o, c) + abs(trend) * 0.5 + 1
        l = min(o, c) - abs(trend) * 0.5 - 1
        vol = 1000 + i * 10
        klines.append(make_kline(o, h, l, c, vol, 1700000000000 + i * 14400000))
        price = c
    return klines


def make_bullish_engulfing_klines() -> list[list]:
    """Generate klines with a bullish engulfing pattern at the end."""
    klines = make_klines(10, 100.0, -0.5)
    # Previous: bearish candle
    klines.append(make_kline(98, 99, 95, 96, 1200, 1700000000000 + 10 * 14400000))
    # Current: bullish candle engulfing previous
    klines.append(make_kline(95, 102, 94, 101, 1500, 1700000000000 + 11 * 14400000))
    return klines


def make_hammer_klines() -> list[list]:
    """Generate klines with a hammer pattern at the end."""
    klines = make_klines(10, 100.0, -0.5)
    # Hammer: small body at top, long lower wick, tiny upper wick
    klines.append(make_kline(100, 100.2, 90, 100.5, 1000, 1700000000000 + 10 * 14400000))
    return klines


def make_doji_klines() -> list[list]:
    """Generate klines with a doji at the end."""
    klines = make_klines(10, 100.0, 0.5)
    # Doji: open ≈ close, wicks both sides
    klines.append(make_kline(100, 105, 95, 100.05, 800, 1700000000000 + 10 * 14400000))
    return klines


def make_three_soldiers_klines() -> list[list]:
    """Generate klines with three white soldiers at the end."""
    klines = make_klines(7, 100.0, -0.5)
    klines.append(make_kline(95, 98, 94, 97, 1000, 1700000000000 + 7 * 14400000))
    klines.append(make_kline(96, 101, 95.5, 100, 1100, 1700000000000 + 8 * 14400000))
    klines.append(make_kline(99, 104, 98.5, 103, 1200, 1700000000000 + 9 * 14400000))
    return klines


@pytest.fixture
def mock_client():
    """Create a BinanceClient with all methods mocked."""
    client = BinanceClient()
    client.klines = AsyncMock(return_value=make_klines(30))
    client.spot_klines = AsyncMock(return_value=make_klines(30))
    client.agg_trades = AsyncMock(return_value=[
        {"p": "100.0", "q": "600", "m": False, "T": 1700000000000},   # $60K buy
        {"p": "100.0", "q": "3000", "m": True, "T": 1700000001000},   # $300K sell
        {"p": "100.0", "q": "50", "m": False, "T": 1700000002000},    # $5K (below min)
        {"p": "100.0", "q": "12000", "m": False, "T": 1700000003000}, # $1.2M buy (mega)
        {"p": "100.0", "q": "800", "m": True, "T": 1700000004000},    # $80K sell
    ])
    client.depth = AsyncMock(return_value={
        "asks": [
            ["100.0", "10"], ["100.1", "20"], ["100.2", "30"],
            ["100.5", "50"], ["101.0", "100"], ["102.0", "200"],
        ],
        "bids": [
            ["99.9", "10"], ["99.8", "20"], ["99.7", "30"],
            ["99.5", "50"], ["99.0", "100"], ["98.0", "200"],
        ],
    })
    client.premium_index = AsyncMock(return_value={
        "symbol": "BTCUSDT",
        "lastFundingRate": "0.0001",
        "markPrice": "100.0",
        "indexPrice": "100.0",
    })
    client.open_interest_hist = AsyncMock(return_value=[
        {"sumOpenInterest": str(1000 + i * 10), "sumOpenInterestValue": str((1000 + i * 10) * 100),
         "timestamp": str(1700000000000 + i * 14400000)}
        for i in range(30)
    ])
    client.top_long_short_position_ratio = AsyncMock(return_value=[
        {"symbol": "BTCUSDT", "longShortRatio": str(1.2 + i * 0.01),
         "longAccount": "0.55", "shortAccount": "0.45",
         "timestamp": str(1700000000000 + i * 14400000)}
        for i in range(30)
    ])
    client.top_long_short_account_ratio = AsyncMock(return_value=[
        {"symbol": "BTCUSDT", "longShortRatio": str(1.1 + i * 0.01),
         "longAccount": "0.52", "shortAccount": "0.48",
         "timestamp": str(1700000000000 + i * 14400000)}
        for i in range(30)
    ])
    client.global_long_short_account_ratio = AsyncMock(return_value=[
        {"symbol": "BTCUSDT", "longShortRatio": str(0.9 + i * 0.01),
         "longAccount": "0.47", "shortAccount": "0.53",
         "timestamp": str(1700000000000 + i * 14400000)}
        for i in range(30)
    ])
    client.taker_buy_sell_ratio = AsyncMock(return_value=[
        {"buySellRatio": str(1.05 + i * 0.005),
         "buyVol": str(500 + i * 5), "sellVol": str(480 + i * 3),
         "timestamp": str(1700000000000 + i * 14400000)}
        for i in range(30)
    ])
    client.premium_index_all = AsyncMock(return_value=[
        {
            "symbol": "BTCUSDT", "lastFundingRate": "0.0001",
            "markPrice": "100.05", "indexPrice": "100.0",
            "nextFundingTime": str(int(__import__('time').time() * 1000) + 3600000),
        },
        {
            "symbol": "ETHUSDT", "lastFundingRate": "0.0005",
            "markPrice": "50.10", "indexPrice": "50.0",
            "nextFundingTime": str(int(__import__('time').time() * 1000) + 1800000),
        },
        {
            "symbol": "SOLUSDT", "lastFundingRate": "-0.0003",
            "markPrice": "19.95", "indexPrice": "20.0",
            "nextFundingTime": str(int(__import__('time').time() * 1000) + 7200000),
        },
        {
            "symbol": "DOGEUSDT", "lastFundingRate": "0.0012",
            "markPrice": "0.0802", "indexPrice": "0.0800",
            "nextFundingTime": str(int(__import__('time').time() * 1000) + 600000),
        },
        {
            "symbol": "XRPUSDT", "lastFundingRate": "-0.0008",
            "markPrice": "0.4990", "indexPrice": "0.5000",
            "nextFundingTime": str(int(__import__('time').time() * 1000) + 14400000),
        },
    ])
    client.funding_info = AsyncMock(return_value=[
        {"symbol": "BTCUSDT", "fundingIntervalHours": 8},
        {"symbol": "ETHUSDT", "fundingIntervalHours": 8},
        {"symbol": "SOLUSDT", "fundingIntervalHours": 8},
        {"symbol": "DOGEUSDT", "fundingIntervalHours": 4},
        {"symbol": "XRPUSDT", "fundingIntervalHours": 8},
    ])
    client.funding_rate_history = AsyncMock(return_value=[
        {"fundingRate": str(0.0001 + (i % 10) * 0.00005 - 0.0002),
         "fundingTime": str(1700000000000 + i * 28800000),
         "symbol": "BTCUSDT"}
        for i in range(100)
    ])
    client.close = AsyncMock()
    return client


@pytest.fixture
def sample_klines():
    """Return sample kline data."""
    return make_klines(30)


@pytest.fixture
def sample_depth():
    """Return sample order book."""
    return {
        "asks": [
            ["100.0", "10"], ["100.1", "20"], ["100.2", "30"],
            ["100.5", "50"], ["101.0", "100"], ["102.0", "200"],
        ],
        "bids": [
            ["99.9", "10"], ["99.8", "20"], ["99.7", "30"],
            ["99.5", "50"], ["99.0", "100"], ["98.0", "200"],
        ],
    }
