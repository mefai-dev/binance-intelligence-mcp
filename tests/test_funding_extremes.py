"""Tests for the funding extremes detector tool."""

import pytest
from unittest.mock import AsyncMock
import time

from binance_intelligence.client import BinanceClient
from binance_intelligence.tools.funding_extremes import (
    detect_funding_extremes,
    _classify_severity,
    _urgency,
)


class TestClassifySeverity:
    """Tests for severity classification."""

    def test_extreme_positive(self):
        assert _classify_severity(0.15) == "EXTREME"

    def test_high_positive(self):
        assert _classify_severity(0.06) == "HIGH"

    def test_elevated_positive(self):
        assert _classify_severity(0.035) == "ELEVATED"

    def test_normal_positive(self):
        assert _classify_severity(0.01) is None

    def test_high_negative(self):
        assert _classify_severity(-0.03) == "HIGH"

    def test_extreme_negative(self):
        assert _classify_severity(-0.06) == "EXTREME"

    def test_elevated_negative(self):
        assert _classify_severity(-0.02) == "HIGH"

    def test_normal_negative(self):
        assert _classify_severity(-0.01) is None

    def test_zero(self):
        assert _classify_severity(0.0) is None


class TestUrgency:
    """Tests for urgency classification."""

    def test_imminent(self):
        assert _urgency(30) == "IMMINENT"

    def test_soon(self):
        assert _urgency(120) == "SOON"

    def test_upcoming(self):
        assert _urgency(300) == "UPCOMING"

    def test_boundary_imminent(self):
        assert _urgency(59) == "IMMINENT"

    def test_boundary_soon(self):
        assert _urgency(60) == "SOON"

    def test_boundary_upcoming(self):
        assert _urgency(240) == "UPCOMING"


class TestDetectFundingExtremes:
    """Tests for detect_funding_extremes."""

    @pytest.fixture
    def extreme_client(self):
        """Client with data containing extreme funding rates."""
        client = BinanceClient()
        now_ms = int(time.time() * 1000)
        client.premium_index_all = AsyncMock(return_value=[
            {
                "symbol": "BTCUSDT", "lastFundingRate": "0.0001",
                "markPrice": "100.0", "indexPrice": "100.0",
                "nextFundingTime": str(now_ms + 3600000),
            },
            {
                "symbol": "EXTREMEUSDT", "lastFundingRate": "0.0015",
                "markPrice": "10.0", "indexPrice": "9.95",
                "nextFundingTime": str(now_ms + 1800000),
            },
            {
                "symbol": "HIGHUSDT", "lastFundingRate": "0.0006",
                "markPrice": "5.0", "indexPrice": "4.99",
                "nextFundingTime": str(now_ms + 600000),
            },
            {
                "symbol": "ELEVATEDUSDT", "lastFundingRate": "0.0004",
                "markPrice": "2.0", "indexPrice": "1.999",
                "nextFundingTime": str(now_ms + 7200000),
            },
            {
                "symbol": "NEGUSDT", "lastFundingRate": "-0.0006",
                "markPrice": "1.0", "indexPrice": "1.01",
                "nextFundingTime": str(now_ms + 14400000),
            },
        ])
        client.funding_info = AsyncMock(return_value=[
            {"symbol": "BTCUSDT", "fundingIntervalHours": 8},
            {"symbol": "EXTREMEUSDT", "fundingIntervalHours": 8},
            {"symbol": "HIGHUSDT", "fundingIntervalHours": 8},
            {"symbol": "ELEVATEDUSDT", "fundingIntervalHours": 8},
            {"symbol": "NEGUSDT", "fundingIntervalHours": 8},
        ])
        client.close = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_returns_tool_name(self, extreme_client):
        result = await detect_funding_extremes(extreme_client)
        assert result["tool"] == "detect_funding_extremes"

    @pytest.mark.asyncio
    async def test_filters_normal_rates(self, extreme_client):
        result = await detect_funding_extremes(extreme_client)
        symbols = [r["symbol"] for r in result["results"]]
        assert "BTCUSDT" not in symbols  # 0.01% is normal

    @pytest.mark.asyncio
    async def test_includes_extreme_rates(self, extreme_client):
        result = await detect_funding_extremes(extreme_client)
        symbols = [r["symbol"] for r in result["results"]]
        assert "EXTREMEUSDT" in symbols

    @pytest.mark.asyncio
    async def test_severity_classification(self, extreme_client):
        result = await detect_funding_extremes(extreme_client)
        extreme = next(r for r in result["results"] if r["symbol"] == "EXTREMEUSDT")
        assert extreme["severity"] == "EXTREME"

    @pytest.mark.asyncio
    async def test_sorted_by_score(self, extreme_client):
        result = await detect_funding_extremes(extreme_client)
        scores = [r["score"] for r in result["results"]]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_arbitrage_hint_positive(self, extreme_client):
        result = await detect_funding_extremes(extreme_client)
        extreme = next(r for r in result["results"] if r["symbol"] == "EXTREMEUSDT")
        assert "Short perp" in extreme["arbitrage_hint"]

    @pytest.mark.asyncio
    async def test_arbitrage_hint_negative(self, extreme_client):
        result = await detect_funding_extremes(extreme_client)
        neg = next(r for r in result["results"] if r["symbol"] == "NEGUSDT")
        assert "Long perp" in neg["arbitrage_hint"]

    @pytest.mark.asyncio
    async def test_severity_counts(self, extreme_client):
        result = await detect_funding_extremes(extreme_client)
        assert "severity_counts" in result
        assert isinstance(result["severity_counts"], dict)

    @pytest.mark.asyncio
    async def test_result_fields(self, extreme_client):
        result = await detect_funding_extremes(extreme_client)
        item = result["results"][0]
        assert "funding_rate_pct" in item
        assert "severity" in item
        assert "score" in item
        assert "urgency" in item
        assert "annualized_apr" in item
        assert "arbitrage_hint" in item

    @pytest.mark.asyncio
    async def test_urgency_imminent(self, extreme_client):
        result = await detect_funding_extremes(extreme_client)
        # HIGHUSDT has 600000ms = 10min → IMMINENT
        high = next(r for r in result["results"] if r["symbol"] == "HIGHUSDT")
        assert high["urgency"] == "IMMINENT"

    @pytest.mark.asyncio
    async def test_no_extremes(self):
        client = BinanceClient()
        client.premium_index_all = AsyncMock(return_value=[
            {"symbol": "BTCUSDT", "lastFundingRate": "0.0001",
             "markPrice": "100.0", "indexPrice": "100.0",
             "nextFundingTime": "0"},
        ])
        client.funding_info = AsyncMock(return_value=[])
        client.close = AsyncMock()
        result = await detect_funding_extremes(client)
        assert result["total_extreme"] == 0
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_negative_extreme_included(self, extreme_client):
        result = await detect_funding_extremes(extreme_client)
        symbols = [r["symbol"] for r in result["results"]]
        assert "NEGUSDT" in symbols
