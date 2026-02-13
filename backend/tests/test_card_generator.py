"""Tests for card generator."""
from backend.roaster.card_generator import generate_card, _truncate_wallet


def test_truncate_wallet():
    assert _truncate_wallet("7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU") == "7xKX...gAsU"
    assert _truncate_wallet("short") == "short"


def test_generate_card():
    roast = {
        "title": "The Paper-Handed Degen",
        "roast_lines": ["Line 1", "Line 2", "Line 3"],
        "degen_score": 85,
        "score_explanation": "You're beyond saving",
        "summary": "A true degen"
    }
    png = generate_card(roast, "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU")
    assert isinstance(png, bytes)
    assert len(png) > 1000
    # PNG magic bytes
    assert png[:8] == b'\x89PNG\r\n\x1a\n'
