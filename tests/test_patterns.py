"""Tests for the Candlestick Pattern Scanner."""

import pytest
from unittest.mock import AsyncMock

from binance_intelligence.tools.patterns import scan_candlestick_patterns, _candle, _detect_patterns
from tests.conftest import (
    make_klines, make_bullish_engulfing_klines,
    make_hammer_klines, make_doji_klines, make_three_soldiers_klines,
)


class TestCandleParsing:
    def test_parse_candle(self):
        k = [0, "100", "110", "90", "105", "1000", 0, "0", 0, "0", "0", "0"]
        c = _candle(k)
        assert c["open"] == 100
        assert c["high"] == 110
        assert c["low"] == 90
        assert c["close"] == 105
        assert c["body"] == 5
        assert c["range"] == 20
        assert c["bullish"] is True
        assert c["bearish"] is False

    def test_parse_bearish_candle(self):
        k = [0, "100", "110", "90", "95", "1000", 0, "0", 0, "0", "0", "0"]
        c = _candle(k)
        assert c["bullish"] is False
        assert c["bearish"] is True
        assert c["body"] == 5

    def test_upper_lower_wick(self):
        k = [0, "100", "110", "90", "105", "1000", 0, "0", 0, "0", "0", "0"]
        c = _candle(k)
        assert c["upper_wick"] == 5   # 110 - 105
        assert c["lower_wick"] == 10  # 100 - 90


class TestPatternDetection:
    def test_detect_doji(self):
        klines = make_doji_klines()
        candles = [_candle(k) for k in klines]
        patterns = _detect_patterns(candles)
        dojis = [p for p in patterns if p["pattern"] == "DOJI"]
        assert len(dojis) >= 1
        assert dojis[-1]["direction"] == "NEUTRAL"
        assert dojis[-1]["confidence"] > 50

    def test_detect_hammer(self):
        klines = make_hammer_klines()
        candles = [_candle(k) for k in klines]
        patterns = _detect_patterns(candles)
        hammers = [p for p in patterns if p["pattern"] == "HAMMER"]
        assert len(hammers) >= 1
        assert hammers[0]["direction"] == "BULLISH"

    def test_detect_bullish_engulfing(self):
        klines = make_bullish_engulfing_klines()
        candles = [_candle(k) for k in klines]
        patterns = _detect_patterns(candles)
        engulfing = [p for p in patterns if p["pattern"] == "BULLISH_ENGULFING"]
        assert len(engulfing) >= 1
        assert engulfing[0]["direction"] == "BULLISH"

    def test_detect_three_white_soldiers(self):
        klines = make_three_soldiers_klines()
        candles = [_candle(k) for k in klines]
        patterns = _detect_patterns(candles)
        soldiers = [p for p in patterns if p["pattern"] == "THREE_WHITE_SOLDIERS"]
        assert len(soldiers) >= 1
        assert soldiers[0]["direction"] == "BULLISH"

    def test_no_patterns_in_flat(self):
        # Flat candles with equal open/close should mostly produce dojis at most
        klines = []
        for i in range(10):
            klines.append([0, "100", "100.01", "99.99", "100", "1000", 0, "0", 0, "0", "0", "0"])
        candles = [_candle(k) for k in klines]
        patterns = _detect_patterns(candles)
        # Only dojis should be detected
        non_doji = [p for p in patterns if p["pattern"] != "DOJI"]
        assert len(non_doji) == 0

    def test_empty_candles(self):
        patterns = _detect_patterns([])
        assert patterns == []

    def test_two_candles_insufficient(self):
        klines = make_klines(2)
        candles = [_candle(k) for k in klines]
        patterns = _detect_patterns(candles)
        assert patterns == []


class TestScanCandlestickPatterns:
    @pytest.mark.asyncio
    async def test_basic_output_structure(self, mock_client):
        result = await scan_candlestick_patterns(mock_client, ["BTCUSDT"])
        assert result["tool"] == "scan_candlestick_patterns"
        assert result["interval"] == "4h"
        assert result["count"] == 1
        assert "results" in result

    @pytest.mark.asyncio
    async def test_result_fields(self, mock_client):
        result = await scan_candlestick_patterns(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        assert "symbol" in r
        assert "interval" in r
        assert "candles_analyzed" in r
        assert "patterns_found" in r
        assert "patterns" in r

    @pytest.mark.asyncio
    async def test_custom_interval(self, mock_client):
        result = await scan_candlestick_patterns(mock_client, ["BTCUSDT"], interval="1h")
        assert result["interval"] == "1h"

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_client):
        mock_client.klines = AsyncMock(side_effect=Exception("err"))
        result = await scan_candlestick_patterns(mock_client, ["BTCUSDT"])
        assert result["count"] == 0
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_multiple_symbols(self, mock_client):
        result = await scan_candlestick_patterns(mock_client, ["BTCUSDT", "ETHUSDT"])
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_results_sorted_by_patterns_found(self, mock_client):
        result = await scan_candlestick_patterns(
            mock_client, ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        )
        counts = [r["patterns_found"] for r in result["results"]]
        assert counts == sorted(counts, reverse=True)
