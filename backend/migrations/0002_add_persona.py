from yoyo import step

steps = [
    step(
        "ALTER TABLE roasts ADD COLUMN persona TEXT NOT NULL DEFAULT 'degen'",
        "ALTER TABLE roasts DROP COLUMN persona"
    )
]
