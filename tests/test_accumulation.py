"""Tests for the Smart Accumulation Detector."""

import pytest
from unittest.mock import AsyncMock

from binance_intelligence.tools.accumulation import detect_accumulation, _linear_slope, _clamp
from tests.conftest import make_klines


class TestHelpers:
    def test_linear_slope_flat(self):
        assert _linear_slope([1, 1, 1, 1]) == 0.0

    def test_linear_slope_positive(self):
        slope = _linear_slope([1, 2, 3, 4, 5])
        assert slope == pytest.approx(1.0)

    def test_linear_slope_negative(self):
        slope = _linear_slope([5, 4, 3, 2, 1])
        assert slope == pytest.approx(-1.0)

    def test_linear_slope_single(self):
        assert _linear_slope([5]) == 0.0

    def test_linear_slope_empty(self):
        assert _linear_slope([]) == 0.0

    def test_clamp_within_range(self):
        assert _clamp(50) == 50.0

    def test_clamp_below(self):
        assert _clamp(-10) == 0.0

    def test_clamp_above(self):
        assert _clamp(200) == 100.0

    def test_clamp_custom_range(self):
        assert _clamp(5, 0, 10) == 5
        assert _clamp(-1, 0, 10) == 0
        assert _clamp(15, 0, 10) == 10


class TestDetectAccumulation:
    @pytest.mark.asyncio
    async def test_basic_output_structure(self, mock_client):
        result = await detect_accumulation(mock_client, ["BTCUSDT"])
        assert result["tool"] == "detect_accumulation"
        assert result["count"] == 1
        assert len(result["results"]) == 1
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_result_has_scores(self, mock_client):
        result = await detect_accumulation(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        assert "scores" in r
        assert "composite" in r
        assert "signal" in r
        scores = r["scores"]
        assert "volume_surge" in scores
        assert "oi_buildup" in scores
        assert "stealth_mode" in scores
        assert "buyer_aggression" in scores

    @pytest.mark.asyncio
    async def test_scores_in_range(self, mock_client):
        result = await detect_accumulation(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        for key, val in r["scores"].items():
            assert 0 <= val <= 100, f"{key} out of range: {val}"
        assert 0 <= r["composite"] <= 100

    @pytest.mark.asyncio
    async def test_signal_labels(self, mock_client):
        result = await detect_accumulation(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        assert r["signal"] in ("STRONG", "MODERATE", "WEAK")

    @pytest.mark.asyncio
    async def test_multiple_symbols(self, mock_client):
        result = await detect_accumulation(mock_client, ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
        assert result["count"] == 3

    @pytest.mark.asyncio
    async def test_default_symbols(self, mock_client):
        result = await detect_accumulation(mock_client)
        assert result["count"] == 12  # DEFAULT_SYMBOLS has 12

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_client):
        mock_client.klines = AsyncMock(side_effect=Exception("API error"))
        result = await detect_accumulation(mock_client, ["BTCUSDT"])
        assert result["count"] == 0
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_high_volume_surge(self, mock_client):
        # Volume 10x average = high volume surge
        klines = make_klines(30, 100, 0.5)
        klines[-1][5] = "50000"  # Spike last volume
        mock_client.klines = AsyncMock(return_value=klines)
        result = await detect_accumulation(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        assert r["scores"]["volume_surge"] > 50

    @pytest.mark.asyncio
    async def test_high_stealth_mode(self, mock_client):
        # Zero funding rate = max stealth
        mock_client.premium_index = AsyncMock(return_value={
            "lastFundingRate": "0.0",
        })
        result = await detect_accumulation(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        assert r["scores"]["stealth_mode"] == 100.0

    @pytest.mark.asyncio
    async def test_results_sorted_by_composite(self, mock_client):
        result = await detect_accumulation(mock_client, ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
        composites = [r["composite"] for r in result["results"]]
        assert composites == sorted(composites, reverse=True)

    @pytest.mark.asyncio
    async def test_insufficient_data(self, mock_client):
        mock_client.klines = AsyncMock(return_value=[make_klines(1)[0]])
        result = await detect_accumulation(mock_client, ["BTCUSDT"])
        # Should still handle gracefully (either error or low score)
        assert result["count"] >= 0
