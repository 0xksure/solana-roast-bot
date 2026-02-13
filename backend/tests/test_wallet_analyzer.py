"""Tests for wallet analyzer."""
import pytest
from backend.roaster.wallet_analyzer import _analyze_signatures, _analyze_tokens


def test_analyze_signatures_empty():
    result = _analyze_signatures([])
    assert result["total"] == 0
    assert result["failed"] == 0


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


def test_analyze_tokens():
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
    result = _analyze_tokens(accounts)
    assert len(result) == 2
    assert result[0]["symbol"] == "BONK"
    assert result[0]["is_memecoin"] is True
