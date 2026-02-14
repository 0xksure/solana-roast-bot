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
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
        conn.autocommit = False
        return conn

    def init_db():
        # PostgreSQL tables are managed by yoyo-migrations (see migrate.py)
        pass

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

    def save_fairscale_score(wallet: str, data: dict):
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO fairscale_scores (wallet, fairscore, fairscore_base, social_score, tier, badges, features, fetched_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(wallet) DO UPDATE SET
                fairscore=%s, fairscore_base=%s, social_score=%s, tier=%s, badges=%s, features=%s, fetched_at=%s
        """, (
            wallet, data.get("fairscore"), data.get("fairscore_base"), data.get("social_score"),
            data.get("tier"), json.dumps(data.get("badges", [])), json.dumps(data.get("features", {})), time.time(),
            data.get("fairscore"), data.get("fairscore_base"), data.get("social_score"),
            data.get("tier"), json.dumps(data.get("badges", [])), json.dumps(data.get("features", {})), time.time(),
        ))
        conn.commit()
        conn.close()

    def get_fairscale_score(wallet: str) -> dict | None:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT fairscore, fairscore_base, social_score, tier, badges, features, fetched_at FROM fairscale_scores WHERE wallet = %s", (wallet,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "fairscore": row[0], "fairscore_base": row[1], "social_score": row[2],
            "tier": row[3], "badges": json.loads(row[4] or "[]"), "features": json.loads(row[5] or "{}"),
            "fetched_at": row[6],
        }

    def get_reputation_leaderboard(limit: int = 20) -> list:
        """Top wallets by combined degen_score * fairscore."""
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT r.wallet,
                   (r.roast_json::json->>'degen_score')::float as degen,
                   f.fairscore, f.tier,
                   (r.roast_json::json->>'degen_score')::float * COALESCE(f.fairscore, 0) as combined
            FROM roasts r
            JOIN fairscale_scores f ON r.wallet = f.wallet
            WHERE f.fairscore IS NOT NULL
            ORDER BY combined DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return [{
            "wallet": r[0], "degen_score": r[1], "fairscore": r[2], "tier": r[3], "combined": r[4],
        } for r in rows]


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
            CREATE TABLE IF NOT EXISTS fairscale_scores (
                wallet TEXT PRIMARY KEY,
                fairscore REAL,
                fairscore_base REAL,
                social_score REAL,
                tier TEXT,
                badges TEXT,
                features TEXT,
                fetched_at REAL NOT NULL
            );
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

    def save_fairscale_score(wallet: str, data: dict):
        conn = _get_conn()
        conn.execute("""
            INSERT INTO fairscale_scores (wallet, fairscore, fairscore_base, social_score, tier, badges, features, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(wallet) DO UPDATE SET
                fairscore=?, fairscore_base=?, social_score=?, tier=?, badges=?, features=?, fetched_at=?
        """, (
            wallet, data.get("fairscore"), data.get("fairscore_base"), data.get("social_score"),
            data.get("tier"), json.dumps(data.get("badges", [])), json.dumps(data.get("features", {})), time.time(),
            data.get("fairscore"), data.get("fairscore_base"), data.get("social_score"),
            data.get("tier"), json.dumps(data.get("badges", [])), json.dumps(data.get("features", {})), time.time(),
        ))
        conn.commit()
        conn.close()

    def get_fairscale_score(wallet: str) -> dict | None:
        conn = _get_conn()
        row = conn.execute("SELECT fairscore, fairscore_base, social_score, tier, badges, features, fetched_at FROM fairscale_scores WHERE wallet = ?", (wallet,)).fetchone()
        conn.close()
        if not row:
            return None
        return {
            "fairscore": row["fairscore"], "fairscore_base": row["fairscore_base"],
            "social_score": row["social_score"], "tier": row["tier"],
            "badges": json.loads(row["badges"] or "[]"), "features": json.loads(row["features"] or "{}"),
            "fetched_at": row["fetched_at"],
        }

    def get_reputation_leaderboard(limit: int = 20) -> list:
        conn = _get_conn()
        rows = conn.execute("""
            SELECT r.wallet,
                   json_extract(r.roast_json, '$.degen_score') as degen,
                   f.fairscore, f.tier,
                   json_extract(r.roast_json, '$.degen_score') * COALESCE(f.fairscore, 0) as combined
            FROM roasts r
            JOIN fairscale_scores f ON r.wallet = f.wallet
            WHERE f.fairscore IS NOT NULL
            ORDER BY combined DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [{
            "wallet": r["wallet"], "degen_score": r["degen"], "fairscore": r["fairscore"],
            "tier": r["tier"], "combined": r["combined"],
        } for r in rows]
