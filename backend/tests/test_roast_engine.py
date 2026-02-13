"""Tests for roast engine."""
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from backend.roaster.roast_engine import _build_prompt, generate_roast

MOCK_ANALYSIS = {
    "wallet": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    "sol_balance": 12.5,
    "sol_usd": 2500.0,
    "sol_price": 200.0,
    "token_count": 8,
    "top_tokens": [{"symbol": "BONK", "amount": 5000000, "is_memecoin": True, "mint": "x", "decimals": 5}],
    "helius_tokens": [],
    "dust_tokens": 3,
    "memecoin_count": 2,
    "transaction_count": 142,
    "failed_transactions": 12,
    "wallet_age_days": 365,
    "first_tx_date": "2024-01-01T00:00:00+00:00",
    "swap_count": 45,
    "protocols_used": ["Jupiter", "Raydium"],
    "nft_activity": 5,
    "tx_types": {"SWAP": 45, "TRANSFER": 80},
    "has_helius": True,
}


def test_build_prompt():
    prompt = _build_prompt(MOCK_ANALYSIS)
    assert "12.5 SOL" in prompt
    assert "142" in prompt
    assert "BONK" in prompt
    assert "Jupiter" in prompt


@pytest.mark.asyncio
async def test_generate_roast():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({
        "title": "The Bonk Bro",
        "roast_lines": ["Line 1", "Line 2", "Line 3"],
        "degen_score": 72,
        "score_explanation": "Test explanation",
        "summary": "Test summary"
    }))]

    with patch("backend.roaster.roast_engine.anthropic.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        result = await generate_roast(MOCK_ANALYSIS)
        assert result["title"] == "The Bonk Bro"
        assert len(result["roast_lines"]) == 3
        assert result["degen_score"] == 72
        assert "wallet_stats" in result
