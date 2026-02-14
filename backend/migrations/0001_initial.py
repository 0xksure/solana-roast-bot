from yoyo import step

steps = [
    step(
        """
        CREATE TABLE IF NOT EXISTS wallet_analyses (
            wallet TEXT PRIMARY KEY,
            analysis_json TEXT NOT NULL,
            created_at DOUBLE PRECISION NOT NULL,
            updated_at DOUBLE PRECISION NOT NULL
        );
        CREATE TABLE IF NOT EXISTS roasts (
            id SERIAL PRIMARY KEY,
            wallet TEXT NOT NULL,
            roast_json TEXT NOT NULL,
            created_at DOUBLE PRECISION NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_roasts_wallet ON roasts(wallet);
        CREATE INDEX IF NOT EXISTS idx_roasts_created ON roasts(created_at DESC);
        CREATE TABLE IF NOT EXISTS fairscale_scores (
            wallet TEXT PRIMARY KEY,
            fairscore DOUBLE PRECISION,
            fairscore_base DOUBLE PRECISION,
            social_score DOUBLE PRECISION,
            tier TEXT,
            badges TEXT,
            features TEXT,
            fetched_at DOUBLE PRECISION NOT NULL
        );
        """,
        """
        DROP TABLE IF EXISTS fairscale_scores;
        DROP TABLE IF EXISTS roasts;
        DROP TABLE IF EXISTS wallet_analyses;
        """
    )
]
