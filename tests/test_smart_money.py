"""Tests for the Smart Money Radar."""

import pytest
from unittest.mock import AsyncMock

from binance_intelligence.tools.smart_money import (
    smart_money_radar, _normalize_ratio, _trend_score,
)


class TestHelpers:
    def test_normalize_ratio_neutral(self):
        assert _normalize_ratio(1.0, 1.0) == 0.0

    def test_normalize_ratio_above(self):
        result = _normalize_ratio(1.5, 1.0)
        assert result == pytest.approx(1.0)

    def test_normalize_ratio_below(self):
        result = _normalize_ratio(0.5, 1.0)
        assert result == pytest.approx(-1.0)

    def test_normalize_ratio_clamped(self):
        result = _normalize_ratio(3.0, 1.0)
        assert result == 1.0
        result = _normalize_ratio(0.0, 1.0)
        assert result == -1.0

    def test_normalize_ratio_zero_neutral(self):
        assert _normalize_ratio(1.0, 0.0) == 0.0

    def test_trend_score_flat(self):
        assert _trend_score([1, 1, 1, 1, 1, 1]) == 0.0

    def test_trend_score_rising(self):
        score = _trend_score([1, 2, 3, 4, 5, 6, 7, 8])
        assert score > 0

    def test_trend_score_falling(self):
        score = _trend_score([8, 7, 6, 5, 4, 3, 2, 1])
        assert score < 0

    def test_trend_score_too_few(self):
        assert _trend_score([1, 2, 3]) == 0.0

    def test_trend_score_clamped(self):
        score = _trend_score([1, 1, 1, 1, 100, 100, 100, 100])
        assert -1.0 <= score <= 1.0


class TestSmartMoneyRadar:
    @pytest.mark.asyncio
    async def test_basic_output_structure(self, mock_client):
        result = await smart_money_radar(mock_client, ["BTCUSDT"])
        assert result["tool"] == "smart_money_radar"
        assert result["count"] == 1
        assert "results" in result

    @pytest.mark.asyncio
    async def test_result_has_factors(self, mock_client):
        result = await smart_money_radar(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        assert "factors" in r
        assert "composite" in r
        assert "bias" in r
        factors = r["factors"]
        assert "top_position_ratio" in factors
        assert "top_account_ratio" in factors
        assert "global_ls_ratio" in factors
        assert "taker_ratio" in factors
        assert "oi_trend" in factors
        assert "price_momentum" in factors

    @pytest.mark.asyncio
    async def test_factors_in_range(self, mock_client):
        result = await smart_money_radar(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        for key, val in r["factors"].items():
            assert -1.0 <= val <= 1.0, f"{key} out of range: {val}"

    @pytest.mark.asyncio
    async def test_composite_in_range(self, mock_client):
        result = await smart_money_radar(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        assert 0 <= r["composite"] <= 100

    @pytest.mark.asyncio
    async def test_bias_labels(self, mock_client):
        result = await smart_money_radar(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        assert r["bias"] in ("BULLISH", "BEARISH", "NEUTRAL")

    @pytest.mark.asyncio
    async def test_multiple_symbols(self, mock_client):
        result = await smart_money_radar(mock_client, ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
        assert result["count"] == 3

    @pytest.mark.asyncio
    async def test_default_symbols(self, mock_client):
        result = await smart_money_radar(mock_client)
        assert result["count"] == 12

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_client):
        mock_client.top_long_short_position_ratio = AsyncMock(
            side_effect=Exception("fail")
        )
        result = await smart_money_radar(mock_client, ["BTCUSDT"])
        assert result["count"] == 0
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_results_sorted_by_composite(self, mock_client):
        result = await smart_money_radar(mock_client, ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
        composites = [r["composite"] for r in result["results"]]
        assert composites == sorted(composites, reverse=True)

    @pytest.mark.asyncio
    async def test_bullish_bias(self, mock_client):
        # All ratios strongly bullish
        mock_client.top_long_short_position_ratio = AsyncMock(return_value=[
            {"longShortRatio": "2.0", "timestamp": "0"} for _ in range(30)
        ])
        mock_client.top_long_short_account_ratio = AsyncMock(return_value=[
            {"longShortRatio": "2.0", "timestamp": "0"} for _ in range(30)
        ])
        mock_client.global_long_short_account_ratio = AsyncMock(return_value=[
            {"longShortRatio": "2.0", "timestamp": "0"} for _ in range(30)
        ])
        mock_client.taker_buy_sell_ratio = AsyncMock(return_value=[
            {"buySellRatio": "2.0", "timestamp": "0"} for _ in range(30)
        ])
        result = await smart_money_radar(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        assert r["bias"] == "BULLISH"
        assert r["composite"] > 60
