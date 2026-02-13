"""Database layer — uses PostgreSQL if DATABASE_URL is set, otherwise SQLite."""

import json
import os
import time
from pathlib import Path

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# --------------- PostgreSQL ---------------
if DATABASE_URL:
    import psycopg2
    import psycopg2.extras

    def _get_conn():
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn

    def init_db():
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wallet_analyses (
                wallet TEXT PRIMARY KEY,
                analysis_json TEXT NOT NULL,
                created_at DOUBLE PRECISION NOT NULL,
                updated_at DOUBLE PRECISION NOT NULL
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS roasts (
                id SERIAL PRIMARY KEY,
                wallet TEXT NOT NULL,
                roast_json TEXT NOT NULL,
                created_at DOUBLE PRECISION NOT NULL
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_roasts_wallet ON roasts(wallet);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_roasts_created ON roasts(created_at DESC);
        """)
        conn.commit()
        conn.close()

    ANALYSIS_TTL = 86400

    def get_cached_analysis(wallet: str) -> dict | None:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT analysis_json, updated_at FROM wallet_analyses WHERE wallet = %s", (wallet,))
        row = cur.fetchone()
        conn.close()
        if row and (time.time() - row[1]) < ANALYSIS_TTL:
            return json.loads(row[0])
        return None

    def save_analysis(wallet: str, analysis: dict):
        now = time.time()
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO wallet_analyses (wallet, analysis_json, created_at, updated_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT(wallet) DO UPDATE SET analysis_json=%s, updated_at=%s
        """, (wallet, json.dumps(analysis), now, now, json.dumps(analysis), now))
        conn.commit()
        conn.close()

    def save_roast(wallet: str, roast: dict):
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO roasts (wallet, roast_json, created_at) VALUES (%s, %s, %s)",
            (wallet, json.dumps(roast), time.time())
        )
        conn.commit()
        conn.close()

    def get_roast_history(wallet: str, limit: int = 10) -> list:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT roast_json, created_at FROM roasts WHERE wallet = %s ORDER BY created_at DESC LIMIT %s",
            (wallet, limit)
        )
        rows = cur.fetchall()
        conn.close()
        return [{"roast": json.loads(r[0]), "created_at": r[1]} for r in rows]

    def get_recent_roasts(limit: int = 20) -> list:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT wallet, roast_json, created_at FROM roasts ORDER BY created_at DESC LIMIT %s",
            (limit,)
        )
        rows = cur.fetchall()
        conn.close()
        return [{
            "wallet": r[0],
            "title": json.loads(r[1]).get("title", ""),
            "degen_score": json.loads(r[1]).get("degen_score", 0),
            "summary": json.loads(r[1]).get("summary", ""),
            "created_at": r[2],
        } for r in rows]

    def get_stats() -> dict:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM roasts")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT wallet) FROM roasts")
        unique = cur.fetchone()[0]
        cur.execute("SELECT AVG((roast_json::json->>'degen_score')::float) FROM roasts")
        avg_score = cur.fetchone()[0]
        conn.close()
        return {"total_roasts": total, "unique_wallets": unique, "avg_degen_score": round(avg_score or 0, 1)}

    def get_leaderboard(limit: int = 10) -> list:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT ON (wallet) wallet, roast_json, created_at,
                   (roast_json::json->>'degen_score')::float as score
            FROM roasts
            ORDER BY wallet, score DESC
        """)
        all_rows = cur.fetchall()
        conn.close()
        all_rows.sort(key=lambda r: r[3] or 0, reverse=True)
        return [{
            "wallet": r[0],
            "title": json.loads(r[1]).get("title", ""),
            "degen_score": r[3],
            "created_at": r[2],
        } for r in all_rows[:limit]]

    def get_percentile(score: int) -> float:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM roasts")
        total = cur.fetchone()[0]
        if total == 0:
            conn.close()
            return 50.0
        cur.execute(
            "SELECT COUNT(*) FROM roasts WHERE (roast_json::json->>'degen_score')::float < %s",
            (score,)
        )
        below = cur.fetchone()[0]
        conn.close()
        return round((below / total) * 100, 1)


# --------------- SQLite (local dev) ---------------
else:
    import sqlite3

    DB_PATH = Path(os.environ.get("DB_PATH", str(Path(__file__).parent.parent.parent / "data" / "roasts.db")))

    def _get_conn():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_db():
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

    ANALYSIS_TTL = 86400

    def get_cached_analysis(wallet: str) -> dict | None:
        conn = _get_conn()
        row = conn.execute(
            "SELECT analysis_json, updated_at FROM wallet_analyses WHERE wallet = ?", (wallet,)
        ).fetchone()
        conn.close()
        if row and (time.time() - row["updated_at"]) < ANALYSIS_TTL:
            return json.loads(row["analysis_json"])
        return None

    def save_analysis(wallet: str, analysis: dict):
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
        conn = _get_conn()
        conn.execute(
            "INSERT INTO roasts (wallet, roast_json, created_at) VALUES (?, ?, ?)",
            (wallet, json.dumps(roast), time.time())
        )
        conn.commit()
        conn.close()

    def get_roast_history(wallet: str, limit: int = 10) -> list:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT roast_json, created_at FROM roasts WHERE wallet = ? ORDER BY created_at DESC LIMIT ?",
            (wallet, limit)
        ).fetchall()
        conn.close()
        return [{"roast": json.loads(r["roast_json"]), "created_at": r["created_at"]} for r in rows]

    def get_recent_roasts(limit: int = 20) -> list:
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
        conn = _get_conn()
        total = conn.execute("SELECT COUNT(*) as c FROM roasts").fetchone()["c"]
        unique = conn.execute("SELECT COUNT(DISTINCT wallet) as c FROM roasts").fetchone()["c"]
        avg_score = conn.execute(
            "SELECT AVG(json_extract(roast_json, '$.degen_score')) as avg FROM roasts"
        ).fetchone()["avg"]
        conn.close()
        return {"total_roasts": total, "unique_wallets": unique, "avg_degen_score": round(avg_score or 0, 1)}

    def get_leaderboard(limit: int = 10) -> list:
        conn = _get_conn()
        rows = conn.execute("""
            SELECT wallet, roast_json, created_at,
                   json_extract(roast_json, '$.degen_score') as score
            FROM roasts
            ORDER BY score DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [{
            "wallet": r["wallet"],
            "title": json.loads(r["roast_json"]).get("title", ""),
            "degen_score": r["score"],
            "created_at": r["created_at"],
        } for r in rows]

    def get_percentile(score: int) -> float:
        conn = _get_conn()
        total = conn.execute("SELECT COUNT(*) as c FROM roasts").fetchone()["c"]
        if total == 0:
            conn.close()
            return 50.0
        below = conn.execute(
            "SELECT COUNT(*) as c FROM roasts WHERE json_extract(roast_json, '$.degen_score') < ?",
            (score,)
        ).fetchone()["c"]
        conn.close()
        return round((below / total) * 100, 1)
