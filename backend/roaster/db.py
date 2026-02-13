import sqlite3
import json
import time
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "roasts.db"

def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS wallet_analyses (
            wallet TEXT PRIMARY KEY,
            analysis_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS roasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet TEXT NOT NULL,
            roast_json TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_roasts_wallet ON roasts(wallet);
        CREATE INDEX IF NOT EXISTS idx_roasts_created ON roasts(created_at DESC);
    """)
    conn.close()

# Analysis cache TTL: 24 hours
ANALYSIS_TTL = 86400

def get_cached_analysis(wallet: str) -> dict | None:
    """Get cached wallet analysis if fresh enough."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT analysis_json, updated_at FROM wallet_analyses WHERE wallet = ?",
        (wallet,)
    ).fetchone()
    conn.close()
    if row and (time.time() - row["updated_at"]) < ANALYSIS_TTL:
        return json.loads(row["analysis_json"])
    return None

def save_analysis(wallet: str, analysis: dict):
    """Cache wallet analysis."""
    now = time.time()
    conn = _get_conn()
    conn.execute(
        """INSERT INTO wallet_analyses (wallet, analysis_json, created_at, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(wallet) DO UPDATE SET analysis_json=?, updated_at=?""",
        (wallet, json.dumps(analysis), now, now, json.dumps(analysis), now)
    )
    conn.commit()
    conn.close()

def save_roast(wallet: str, roast: dict):
    """Save a roast to history."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO roasts (wallet, roast_json, created_at) VALUES (?, ?, ?)",
        (wallet, json.dumps(roast), time.time())
    )
    conn.commit()
    conn.close()

def get_roast_history(wallet: str, limit: int = 10) -> list:
    """Get past roasts for a wallet."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT roast_json, created_at FROM roasts WHERE wallet = ? ORDER BY created_at DESC LIMIT ?",
        (wallet, limit)
    ).fetchall()
    conn.close()
    return [{"roast": json.loads(r["roast_json"]), "created_at": r["created_at"]} for r in rows]

def get_recent_roasts(limit: int = 20) -> list:
    """Get most recent roasts across all wallets (for the feed)."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT wallet, roast_json, created_at FROM roasts ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [{
        "wallet": r["wallet"],
        "title": json.loads(r["roast_json"]).get("title", ""),
        "degen_score": json.loads(r["roast_json"]).get("degen_score", 0),
        "summary": json.loads(r["roast_json"]).get("summary", ""),
        "created_at": r["created_at"],
    } for r in rows]

def get_stats() -> dict:
    """Get overall stats."""
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) as c FROM roasts").fetchone()["c"]
    unique = conn.execute("SELECT COUNT(DISTINCT wallet) as c FROM roasts").fetchone()["c"]
    conn.close()
    return {"total_roasts": total, "unique_wallets": unique}
