from yoyo import step

steps = [
    step(
        """
        CREATE TABLE IF NOT EXISTS telegram_roasts (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            username TEXT,
            wallet_address TEXT NOT NULL,
            persona TEXT NOT NULL DEFAULT 'degen',
            created_at REAL NOT NULL
        )
        """,
        "DROP TABLE IF EXISTS telegram_roasts"
    ),
    step(
        "CREATE INDEX IF NOT EXISTS idx_tg_roasts_user ON telegram_roasts(user_id)",
        "DROP INDEX IF EXISTS idx_tg_roasts_user"
    ),
    step(
        "CREATE INDEX IF NOT EXISTS idx_tg_roasts_chat ON telegram_roasts(chat_id)",
        "DROP INDEX IF EXISTS idx_tg_roasts_chat"
    ),
]
