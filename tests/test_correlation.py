"""Tests for the Pair Correlation Matrix."""

import pytest
from unittest.mock import AsyncMock

from binance_intelligence.tools.correlation import compute_correlation_matrix, _pearson_r
from tests.conftest import make_klines


class TestPearsonR:
    def test_perfect_positive(self):
        r = _pearson_r([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
        assert r == pytest.approx(1.0)

    def test_perfect_negative(self):
        r = _pearson_r([1, 2, 3, 4, 5], [5, 4, 3, 2, 1])
        assert r == pytest.approx(-1.0)

    def test_no_correlation(self):
        r = _pearson_r([1, 2, 3, 4, 5], [3, 3, 3, 3, 3])
        assert r == 0.0

    def test_short_series(self):
        assert _pearson_r([1, 2], [3, 4]) == 0.0

    def test_empty(self):
        assert _pearson_r([], []) == 0.0

    def test_unequal_length(self):
        r = _pearson_r([1, 2, 3, 4, 5], [1, 2, 3])
        assert -1.0 <= r <= 1.0

    def test_high_correlation(self):
        x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        y = [2, 4, 5, 8, 9, 12, 14, 15, 18, 20]
        r = _pearson_r(x, y)
        assert r > 0.95


class TestComputeCorrelationMatrix:
    @pytest.mark.asyncio
    async def test_basic_output_structure(self, mock_client):
        result = await compute_correlation_matrix(mock_client, ["BTCUSDT", "ETHUSDT"])
        assert result["tool"] == "compute_correlation_matrix"
        assert "matrix" in result
        assert "symbols" in result
        assert "strong_correlations" in result

    @pytest.mark.asyncio
    async def test_matrix_dimensions(self, mock_client):
        syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        result = await compute_correlation_matrix(mock_client, syms)
        matrix = result["matrix"]
        assert len(matrix) == 3
        for sym in syms:
            assert sym in matrix
            assert len(matrix[sym]) == 3

    @pytest.mark.asyncio
    async def test_diagonal_is_one(self, mock_client):
        result = await compute_correlation_matrix(mock_client, ["BTCUSDT", "ETHUSDT"])
        matrix = result["matrix"]
        for sym in result["symbols"]:
            assert matrix[sym][sym] == 1.0

    @pytest.mark.asyncio
    async def test_symmetric_matrix(self, mock_client):
        syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        result = await compute_correlation_matrix(mock_client, syms)
        matrix = result["matrix"]
        for a in syms:
            for b in syms:
                assert matrix[a][b] == matrix[b][a]

    @pytest.mark.asyncio
    async def test_too_few_symbols(self, mock_client):
        result = await compute_correlation_matrix(mock_client, ["BTCUSDT"])
        assert "error" in result

    @pytest.mark.asyncio
    async def test_default_symbols(self, mock_client):
        result = await compute_correlation_matrix(mock_client)
        assert len(result["symbols"]) == 8  # DEFAULT_SYMBOLS[:8]

    @pytest.mark.asyncio
    async def test_max_20_symbols(self, mock_client):
        syms = [f"SYM{i}USDT" for i in range(25)]
        result = await compute_correlation_matrix(mock_client, syms)
        assert len(result["symbols"]) <= 20

    @pytest.mark.asyncio
    async def test_strong_correlations_identified(self, mock_client):
        # Same data for all symbols = perfect correlation
        result = await compute_correlation_matrix(mock_client, ["BTCUSDT", "ETHUSDT"])
        # Should detect strong correlation since mock returns identical data
        strong = result["strong_correlations"]
        assert len(strong) >= 1
        assert strong[0]["correlation"] >= 0.7 or strong[0]["correlation"] <= -0.7

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_client):
        mock_client.klines = AsyncMock(side_effect=Exception("fail"))
        result = await compute_correlation_matrix(mock_client, ["BTCUSDT", "ETHUSDT"])
        assert "error" in result

    @pytest.mark.asyncio
    async def test_custom_interval_and_limit(self, mock_client):
        result = await compute_correlation_matrix(
            mock_client, ["BTCUSDT", "ETHUSDT"], interval="1h", limit=50
        )
        assert result["interval"] == "1h"
        assert result["lookback_periods"] == 50
