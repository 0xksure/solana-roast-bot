"""Tests for wallet analyzer."""
import pytest
from backend.roaster.wallet_analyzer import _analyze_signatures, _analyze_tokens


def test_analyze_signatures_empty():
    result = _analyze_signatures([])
    assert result["total"] == 0
    assert result["failed"] == 0
    assert result["late_night_txs"] == 0
    assert result["burst_count"] == 0


def test_analyze_signatures():
    sigs = [
        {"signature": "a", "blockTime": 1000, "err": None},
        {"signature": "b", "blockTime": 2000, "err": {"InstructionError": []}},
        {"signature": "c", "blockTime": 3000, "err": None},
    ]
    result = _analyze_signatures(sigs)
    assert result["total"] == 3
    assert result["failed"] == 1
    assert result["first_ts"] == 1000
    assert result["last_ts"] == 3000
    assert isinstance(result["hour_distribution"], dict)


def test_analyze_signatures_burst_detection():
    """Test burst detection with 5 txs in 5 minutes."""
    sigs = [{"signature": str(i), "blockTime": 1000 + i * 50, "err": None} for i in range(6)]
    result = _analyze_signatures(sigs)
    assert result["burst_count"] > 0


def test_analyze_tokens_with_token_list():
    token_list = {
        "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": {"symbol": "BONK", "name": "Bonk"},
    }
    accounts = [
        {"account": {"data": {"parsed": {"info": {
            "mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
            "tokenAmount": {"uiAmount": 1000000, "decimals": 5}
        }}}}},
        {"account": {"data": {"parsed": {"info": {
            "mint": "SomeOtherMint123",
            "tokenAmount": {"uiAmount": 0.0001, "decimals": 9}
        }}}}},
    ]
    result = _analyze_tokens(accounts, token_list)
    assert len(result) == 2
    assert result[0]["symbol"] == "BONK"
    assert result[0]["is_known"] is True
    assert result[1]["symbol"] == "SHITCOIN"
    assert result[1]["is_known"] is False


def test_analyze_tokens_empty():
    result = _analyze_tokens([], {})
    assert result == []
