"""Tests for wallet analyzer."""
import pytest
from backend.roaster.wallet_analyzer import (
    _analyze_signatures,
    _analyze_tokens,
    _analyze_swaps,
    _analyze_timeline,
    _analyze_graveyard,
    _extract_swaps_from_tx,
    _build_net_worth_timeline,
    _build_protocol_stats,
    _build_loss_by_token,
    _build_loss_by_period,
    _build_activity_heatmap,
    MARKET_EVENTS,
    SOL_PRICE_HISTORY,
)


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


# --- Swap Analysis Tests ---

def test_analyze_swaps_empty():
    result = _analyze_swaps([])
    assert result["total_swaps_detected"] == 0
    assert result["estimated_pnl_sol"] == 0
    assert result["biggest_loss"] is None
    assert result["biggest_win"] is None


def test_analyze_swaps_with_trades():
    swaps = [
        {
            "timestamp": 1700000000,
            "token_in": {"mint": "SOL_MINT", "symbol": "SOL", "amount": 5.0},
            "token_out": {"mint": "BONK_MINT", "symbol": "BONK", "amount": 1000000},
            "sol_change": -5.0,
        },
        {
            "timestamp": 1700100000,
            "token_in": {"mint": "BONK_MINT", "symbol": "BONK", "amount": 500000},
            "token_out": {"mint": "SOL_MINT", "symbol": "SOL", "amount": 2.0},
            "sol_change": 2.0,
        },
    ]
    result = _analyze_swaps(swaps)
    assert result["total_swaps_detected"] == 2
    assert result["estimated_pnl_sol"] == -3.0  # spent 5, got 2 back
    assert result["biggest_loss"] is not None
    assert result["biggest_loss"]["token"] == "BONK"
    assert result["biggest_loss"]["sol_spent"] == 5.0
    assert result["biggest_win"] is not None
    assert result["biggest_win"]["token"] == "BONK"
    assert result["biggest_win"]["sol_received"] == 2.0
    assert result["win_rate"] == 1.0  # 1 sell = 1 win out of 1


def test_analyze_swaps_all_buys():
    swaps = [
        {
            "timestamp": 1700000000,
            "token_in": {"mint": "SOL_MINT", "symbol": "SOL", "amount": 10.0},
            "token_out": {"mint": "MEME_MINT", "symbol": "MEME", "amount": 99999},
            "sol_change": -10.0,
        },
    ]
    result = _analyze_swaps(swaps)
    assert result["estimated_pnl_sol"] == -10.0
    assert result["win_rate"] == 0


# --- Timeline Tests ---

def test_analyze_timeline_empty():
    result = _analyze_timeline([])
    assert result["active_periods"] == []
    assert result["peak_activity_period"] is None
    assert result["joined_during"] is None


def test_analyze_timeline_with_market_events():
    # Simulate wallet active during FTX collapse (Nov 2022) and memecoin season (Jan 2024)
    import time
    from datetime import datetime, timezone

    # Nov 2022 timestamps
    nov_2022_base = int(datetime(2022, 11, 15, tzinfo=timezone.utc).timestamp())
    jan_2024_base = int(datetime(2024, 1, 15, tzinfo=timezone.utc).timestamp())

    sigs = []
    for i in range(10):
        sigs.append({"signature": f"nov{i}", "blockTime": nov_2022_base + i * 3600, "err": None})
    for i in range(20):
        sigs.append({"signature": f"jan{i}", "blockTime": jan_2024_base + i * 3600, "err": None})

    result = _analyze_timeline(sigs)
    assert len(result["active_periods"]) == 2
    assert result["peak_activity_period"]["period"] == "2024-01"
    assert result["peak_activity_period"]["tx_count"] == 20

    # Should have joined during FTX collapse
    assert result["joined_during"]["period"] == "2022-11"
    assert "FTX" in result["joined_during"].get("event", "")

    # Should detect the gap between Nov 2022 and Jan 2024
    assert len(result["inactive_gaps"]) >= 1
    gap = result["inactive_gaps"][0]
    assert gap["months"] >= 12


def test_analyze_timeline_joined_at_top():
    from datetime import datetime, timezone

    nov_2021_base = int(datetime(2021, 11, 10, tzinfo=timezone.utc).timestamp())
    sigs = [{"signature": f"s{i}", "blockTime": nov_2021_base + i * 3600, "err": None} for i in range(5)]

    result = _analyze_timeline(sigs)
    assert result["joined_during"]["period"] == "2021-11"
    assert result["joined_during"]["roast"] == "Bought the absolute top"


# --- Graveyard Tests ---

def test_analyze_graveyard():
    token_list = {
        "KNOWN_MINT": {"symbol": "BONK", "name": "Bonk"},
    }
    accounts = [
        # Unknown token with balance = graveyard
        {"account": {"data": {"parsed": {"info": {
            "mint": "DEAD_TOKEN_ABCDEF123",
            "tokenAmount": {"uiAmount": 50000, "decimals": 9}
        }}}}},
        # Known token with dust = graveyard
        {"account": {"data": {"parsed": {"info": {
            "mint": "KNOWN_MINT",
            "tokenAmount": {"uiAmount": 0.001, "decimals": 6}
        }}}}},
        # Zero balance = not counted
        {"account": {"data": {"parsed": {"info": {
            "mint": "ZERO_MINT",
            "tokenAmount": {"uiAmount": 0, "decimals": 9}
        }}}}},
    ]
    result = _analyze_graveyard(accounts, token_list)
    assert result["graveyard_tokens"] == 2  # unknown + dust known
    assert len(result["graveyard_names"]) == 2


def test_analyze_graveyard_empty():
    result = _analyze_graveyard([], {})
    assert result["graveyard_tokens"] == 0
    assert result["graveyard_names"] == []


# --- Extract Swaps Tests ---

def test_extract_swaps_non_swap_tx():
    """Non-swap transaction should return empty list."""
    tx = {
        "blockTime": 1700000000,
        "transaction": {"message": {"instructions": [{"programId": "11111111111111111111111111111111"}], "accountKeys": []}},
        "meta": {"innerInstructions": [], "preTokenBalances": [], "postTokenBalances": [], "preBalances": [], "postBalances": []},
    }
    result = _extract_swaps_from_tx(tx, "WALLET123", {})
    assert result == []


def test_extract_swaps_jupiter_swap():
    """Jupiter swap should be detected."""
    wallet = "WALLETxyz"
    tx = {
        "blockTime": 1700000000,
        "transaction": {
            "message": {
                "instructions": [
                    {"programId": "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"}
                ],
                "accountKeys": [wallet, "OTHER"],
            },
        },
        "meta": {
            "innerInstructions": [],
            "preTokenBalances": [
                {"owner": wallet, "mint": "TOKEN_A", "uiTokenAmount": {"uiAmount": 100}},
            ],
            "postTokenBalances": [
                {"owner": wallet, "mint": "TOKEN_A", "uiTokenAmount": {"uiAmount": 50}},
                {"owner": wallet, "mint": "TOKEN_B", "uiTokenAmount": {"uiAmount": 200}},
            ],
            "preBalances": [1000000000, 500000000],
            "postBalances": [900000000, 600000000],
        },
    }
    token_list = {
        "TOKEN_A": {"symbol": "USDC", "name": "USD Coin"},
        "TOKEN_B": {"symbol": "BONK", "name": "Bonk"},
    }
    result = _extract_swaps_from_tx(tx, wallet, token_list)
    assert len(result) == 1
    swap = result[0]
    assert swap["timestamp"] == 1700000000
    assert swap["token_in"]["symbol"] == "USDC"
    assert swap["token_out"]["symbol"] == "BONK"


def test_market_events_keys():
    """Verify market events have correct format."""
    for key, val in MARKET_EVENTS.items():
        assert len(key) == 7  # YYYY-MM
        assert "-" in key
        assert "event" in val
        assert "sentiment" in val


# --- Net Worth Timeline Tests ---

def test_build_net_worth_timeline_empty():
    result = _build_net_worth_timeline([], [], "WALLET")
    assert result == []


def test_build_net_worth_timeline_basic():
    from datetime import datetime, timezone
    ts_base = int(datetime(2024, 1, 15, tzinfo=timezone.utc).timestamp())
    sigs = [{"blockTime": ts_base + i * 3600, "signature": f"s{i}"} for i in range(5)]
    result = _build_net_worth_timeline(sigs, [], "WALLET")
    # Now returns continuous timeline from first month to current month
    assert len(result) >= 1
    assert result[0]["month"] == "2024-01"
    assert result[0]["tx_count"] == 5
    assert result[0]["sol_price_usd"] == 95.0  # from SOL_PRICE_HISTORY


def test_build_net_worth_timeline_with_tx_balances():
    from datetime import datetime, timezone
    ts = int(datetime(2024, 3, 10, tzinfo=timezone.utc).timestamp())
    wallet = "WALLETxyz"
    sigs = [{"blockTime": ts, "signature": "s1"}]
    txns = [{
        "blockTime": ts,
        "transaction": {"message": {"accountKeys": [wallet], "instructions": []}},
        "meta": {"postBalances": [5_000_000_000], "innerInstructions": []},
    }]
    result = _build_net_worth_timeline(sigs, txns, wallet)
    # Continuous timeline from 2024-03 to now
    assert len(result) >= 1
    assert result[0]["estimated_sol"] == 5.0
    assert result[0]["estimated_usd"] == 5.0 * 185.0  # 2024-03 price


# --- Protocol Stats Tests ---

def test_build_protocol_stats_empty():
    assert _build_protocol_stats([]) == []


def test_build_protocol_stats():
    txns = [{
        "transaction": {"message": {"instructions": [
            {"programId": "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"},
            {"programId": "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"},  # duplicate in same tx
            {"programId": "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"},
        ]}},
        "meta": {"innerInstructions": []},
    }]
    result = _build_protocol_stats(txns)
    names = {r["name"] for r in result}
    assert "Jupiter" in names
    assert "Raydium" in names
    # Jupiter should count once per tx (deduped)
    jup = next(r for r in result if r["name"] == "Jupiter")
    assert jup["tx_count"] == 1


# --- Loss by Token Tests ---

def test_build_loss_by_token_empty():
    assert _build_loss_by_token([]) == []


def test_build_loss_by_token():
    swaps = [
        {"token_in": {"symbol": "SOL", "amount": 5.0}, "token_out": {"symbol": "BONK", "amount": 1000000}, "sol_change": -5.0},
        {"token_in": {"symbol": "SOL", "amount": 3.0}, "token_out": {"symbol": "BONK", "amount": 500000}, "sol_change": -3.0},
        {"token_in": {"symbol": "BONK", "amount": 500000}, "token_out": {"symbol": "SOL", "amount": 2.0}, "sol_change": 2.0},
    ]
    result = _build_loss_by_token(swaps)
    assert len(result) == 1  # BONK: 5+3-2 = 6 SOL net loss
    assert result[0]["token"] == "BONK"
    assert result[0]["sol_lost"] == 6.0


# --- Loss by Period Tests ---

def test_build_loss_by_period():
    from datetime import datetime, timezone
    ts = int(datetime(2024, 3, 15, tzinfo=timezone.utc).timestamp())
    swaps = [
        {"timestamp": ts, "sol_change": -5.0, "token_in": {"symbol": "SOL", "amount": 5.0}, "token_out": {"symbol": "BONK"}},
    ]
    result = _build_loss_by_period(swaps)
    assert len(result) == 1
    assert result[0]["month"] == "2024-03"
    assert result[0]["sol_lost"] == 5.0
    assert "BONK" in result[0].get("event", "")  # 2024-03 has BONK/WIF mania event


# --- Activity Heatmap Tests ---

def test_build_activity_heatmap_empty():
    assert _build_activity_heatmap([]) == {}


def test_build_activity_heatmap():
    from datetime import datetime, timezone
    # Jan 6, 2024 is a Saturday, 14:00 UTC
    ts = int(datetime(2024, 1, 6, 14, 0, tzinfo=timezone.utc).timestamp())
    sigs = [{"blockTime": ts}, {"blockTime": ts + 60}]
    result = _build_activity_heatmap(sigs)
    assert result.get("sat_14") == 2


def test_sol_price_history_coverage():
    """Ensure price history covers 2021-2026."""
    assert "2021-01" in SOL_PRICE_HISTORY
    assert "2026-02" in SOL_PRICE_HISTORY
    assert all(v > 0 for v in SOL_PRICE_HISTORY.values())
