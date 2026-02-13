"""Tests for the SQLite database cache layer."""

import time
import pytest
from unittest.mock import patch
from backend.roaster import db


@pytest.fixture(autouse=True)
def use_temp_db(tmp_path):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_roasts.db"
    with patch.object(db, "DB_PATH", test_db):
        db.init_db()
        yield


def test_init_db_creates_tables(tmp_path):
    """Tables should exist after init."""
    conn = db._get_conn()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    conn.close()
    names = {r["name"] for r in tables}
    assert "wallet_analyses" in names
    assert "roasts" in names


def test_save_and_get_analysis():
    analysis = {"sol_balance": 42.0, "tokens": ["bonk"]}
    db.save_analysis("abc123", analysis)
    cached = db.get_cached_analysis("abc123")
    assert cached == analysis


def test_analysis_ttl_expiry():
    analysis = {"sol_balance": 1.0}
    db.save_analysis("expired_wallet", analysis)
    # Simulate expired TTL
    with patch.object(db, "ANALYSIS_TTL", 0):
        assert db.get_cached_analysis("expired_wallet") is None


def test_analysis_upsert():
    db.save_analysis("w1", {"v": 1})
    db.save_analysis("w1", {"v": 2})
    assert db.get_cached_analysis("w1") == {"v": 2}


def test_save_and_get_roast():
    roast = {"title": "Degen King", "degen_score": 85, "summary": "yolo"}
    db.save_roast("wallet1", roast)
    history = db.get_roast_history("wallet1")
    assert len(history) == 1
    assert history[0]["roast"]["title"] == "Degen King"
    assert "created_at" in history[0]


def test_roast_history_ordering():
    for i in range(5):
        db.save_roast("w", {"title": f"Roast {i}", "degen_score": i * 10})
    history = db.get_roast_history("w", limit=3)
    assert len(history) == 3
    assert history[0]["roast"]["title"] == "Roast 4"  # most recent first


def test_get_recent_roasts():
    db.save_roast("a", {"title": "A", "degen_score": 10, "summary": "a"})
    db.save_roast("b", {"title": "B", "degen_score": 90, "summary": "b"})
    recent = db.get_recent_roasts(limit=10)
    assert len(recent) == 2
    assert recent[0]["wallet"] == "b"
    assert recent[0]["title"] == "B"


def test_get_stats():
    assert db.get_stats() == {"total_roasts": 0, "unique_wallets": 0}
    db.save_roast("x", {"title": "X"})
    db.save_roast("x", {"title": "X2"})
    db.save_roast("y", {"title": "Y"})
    stats = db.get_stats()
    assert stats["total_roasts"] == 3
    assert stats["unique_wallets"] == 2


def test_no_cached_analysis_for_unknown_wallet():
    assert db.get_cached_analysis("nonexistent") is None


def test_empty_roast_history():
    assert db.get_roast_history("nonexistent") == []
