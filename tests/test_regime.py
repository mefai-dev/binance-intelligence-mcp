"""Tests for the Market Regime Classifier."""

import pytest
from unittest.mock import AsyncMock

from binance_intelligence.tools.regime import (
    classify_market_regime, _true_range, _smoothed_avg, _compute_adx,
)
from tests.conftest import make_klines


class TestTrueRange:
    def test_basic_true_range(self):
        candles = [
            {"open": 100, "high": 110, "low": 90, "close": 105},
            {"open": 105, "high": 115, "low": 95, "close": 100},
        ]
        tr = _true_range(candles)
        assert len(tr) == 1
        # max(115-95, |115-105|, |95-105|) = max(20, 10, 10) = 20
        assert tr[0] == 20

    def test_gap_up(self):
        candles = [
            {"open": 100, "high": 105, "low": 95, "close": 90},
            {"open": 110, "high": 120, "low": 108, "close": 115},
        ]
        tr = _true_range(candles)
        # max(120-108, |120-90|, |108-90|) = max(12, 30, 18) = 30
        assert tr[0] == 30

    def test_single_candle(self):
        candles = [{"open": 100, "high": 110, "low": 90, "close": 105}]
        tr = _true_range(candles)
        assert len(tr) == 0


class TestSmoothedAvg:
    def test_basic_smoothing(self):
        values = [10] * 20
        result = _smoothed_avg(values, 14)
        assert result[-1] == pytest.approx(10.0)

    def test_short_series(self):
        result = _smoothed_avg([5, 10], 14)
        assert len(result) == 1
        assert result[0] == pytest.approx(7.5)

    def test_empty(self):
        result = _smoothed_avg([], 14)
        assert result == [0.0]


class TestComputeADX:
    def test_trending_market(self):
        # Strong uptrend: each candle higher
        candles = []
        for i in range(30):
            p = 100 + i * 2
            candles.append({"open": p, "high": p + 3, "low": p - 1, "close": p + 2})
        adx = _compute_adx(candles)
        assert adx["adx"] > 0
        assert adx["plus_di"] > adx["minus_di"]

    def test_insufficient_data(self):
        candles = [
            {"open": 100, "high": 110, "low": 90, "close": 105},
        ] * 5
        adx = _compute_adx(candles)
        assert adx["adx"] == 0


class TestClassifyMarketRegime:
    @pytest.mark.asyncio
    async def test_basic_output_structure(self, mock_client):
        mock_client.klines = AsyncMock(return_value=make_klines(168, 100, 0.5))
        result = await classify_market_regime(mock_client, ["BTCUSDT"])
        assert result["tool"] == "classify_market_regime"
        assert result["count"] == 1
        assert "regime_summary" in result
        assert "results" in result

    @pytest.mark.asyncio
    async def test_result_fields(self, mock_client):
        mock_client.klines = AsyncMock(return_value=make_klines(168, 100, 0.5))
        result = await classify_market_regime(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        assert "symbol" in r
        assert "regime" in r
        assert "indicators" in r
        indicators = r["indicators"]
        assert "adx" in indicators
        assert "atr" in indicators
        assert "atr_pct" in indicators
        assert "volume_change_pct" in indicators
        assert "funding_rate" in indicators

    @pytest.mark.asyncio
    async def test_valid_regime_labels(self, mock_client):
        mock_client.klines = AsyncMock(return_value=make_klines(168, 100, 0.5))
        result = await classify_market_regime(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        assert r["regime"] in ("TRENDING", "RANGING", "VOLATILE_BREAKOUT", "LOW_ACTIVITY")

    @pytest.mark.asyncio
    async def test_regime_summary_groups(self, mock_client):
        mock_client.klines = AsyncMock(return_value=make_klines(168, 100, 0.5))
        result = await classify_market_regime(mock_client, ["BTCUSDT", "ETHUSDT"])
        summary = result["regime_summary"]
        total = sum(len(v) for v in summary.values())
        assert total == 2

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_client):
        mock_client.klines = AsyncMock(side_effect=Exception("fail"))
        result = await classify_market_regime(mock_client, ["BTCUSDT"])
        assert result["count"] == 0
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_insufficient_data(self, mock_client):
        mock_client.klines = AsyncMock(return_value=make_klines(5))
        result = await classify_market_regime(mock_client, ["BTCUSDT"])
        # Should handle gracefully
        assert result["count"] == 0 or result["count"] == 1

    @pytest.mark.asyncio
    async def test_direction_for_trending(self, mock_client):
        # Strong uptrend klines
        klines = make_klines(168, 100, 2.0)
        mock_client.klines = AsyncMock(return_value=klines)
        result = await classify_market_regime(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        if r["regime"] in ("TRENDING", "VOLATILE_BREAKOUT"):
            assert r["direction"] in ("UP", "DOWN")

    @pytest.mark.asyncio
    async def test_multiple_symbols(self, mock_client):
        mock_client.klines = AsyncMock(return_value=make_klines(168, 100, 0.5))
        result = await classify_market_regime(mock_client, ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
        assert result["count"] == 3
