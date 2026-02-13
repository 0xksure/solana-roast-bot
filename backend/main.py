"""Solana Roast Bot — FastAPI backend."""

import json
import os
import re
import time
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.roaster.card_generator import generate_card
from backend.roaster.roast_engine import generate_roast
from backend.roaster.wallet_analyzer import analyze_wallet

app = FastAPI(title="Solana Roast Bot")

# --- Config ---
CACHE_TTL = 3600  # 1 hour
RATE_LIMIT = 10  # per IP per hour
STATS_FILE = Path(__file__).parent.parent / "data" / "stats.json"
STATIC_DIR = Path(__file__).parent / "static"

# --- In-memory stores ---
roast_cache: dict[str, dict] = {}  # wallet -> {roast, timestamp}
rate_limits: dict[str, list[float]] = defaultdict(list)  # ip -> [timestamps]


# --- Helpers ---
def _load_stats() -> dict:
    try:
        return json.loads(STATS_FILE.read_text())
    except Exception:
        return {"total_roasts": 0, "wallets": {}}


def _save_stats(stats: dict):
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATS_FILE.write_text(json.dumps(stats))


def _check_rate_limit(ip: str) -> bool:
    now = time.time()
    rate_limits[ip] = [t for t in rate_limits[ip] if now - t < 3600]
    return len(rate_limits[ip]) < RATE_LIMIT


def _record_rate_limit(ip: str):
    rate_limits[ip].append(time.time())


def _get_cached(wallet: str) -> dict | None:
    entry = roast_cache.get(wallet)
    if entry and time.time() - entry["timestamp"] < CACHE_TTL:
        return entry["roast"]
    return None


def _set_cache(wallet: str, roast: dict):
    roast_cache[wallet] = {"roast": roast, "timestamp": time.time()}


WALLET_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def _validate_wallet(wallet: str) -> str:
    wallet = wallet.strip()
    if not WALLET_RE.match(wallet):
        raise HTTPException(status_code=400, detail="Invalid Solana wallet address")
    return wallet


# --- Routes ---


class RoastRequest(BaseModel):
    wallet: str


@app.post("/api/roast")
async def api_roast(req: RoastRequest, request: Request):
    wallet = _validate_wallet(req.wallet)
    ip = request.client.host if request.client else "unknown"

    if not _check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    # Check cache
    cached = _get_cached(wallet)
    if cached:
        return cached

    try:
        analysis = await analyze_wallet(wallet)
        roast = await generate_roast(analysis)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Roast failed: {str(e)}")

    _set_cache(wallet, roast)
    _record_rate_limit(ip)

    # Update stats
    stats = _load_stats()
    stats["total_roasts"] = stats.get("total_roasts", 0) + 1
    stats["wallets"][wallet] = stats["wallets"].get(wallet, 0) + 1
    _save_stats(stats)

    return roast


@app.get("/api/roast/{wallet}/image")
async def api_roast_image(wallet: str):
    wallet = _validate_wallet(wallet)
    cached = _get_cached(wallet)
    if not cached:
        raise HTTPException(status_code=404, detail="Roast not found. Generate one first.")

    png = generate_card(cached, wallet)
    return Response(content=png, media_type="image/png")


@app.get("/api/stats")
async def api_stats():
    stats = _load_stats()
    top_wallets = sorted(stats.get("wallets", {}).items(), key=lambda x: x[1], reverse=True)[:10]
    return {
        "total_roasts": stats.get("total_roasts", 0),
        "top_wallets": [{"wallet": w, "count": c} for w, c in top_wallets],
    }


@app.get("/api/recent")
async def api_recent():
    """Return recent cached roasts (titles + scores only)."""
    recent = []
    now = time.time()
    for wallet, entry in sorted(roast_cache.items(), key=lambda x: x[1]["timestamp"], reverse=True)[:10]:
        if now - entry["timestamp"] < CACHE_TTL:
            r = entry["roast"]
            recent.append({
                "title": r.get("title", ""),
                "degen_score": r.get("degen_score", 0),
                "summary": r.get("summary", ""),
            })
    return recent


def _og_html(wallet: str, roast: dict, base_url: str = "") -> str:
    title = roast.get("title", "Solana Roast Bot")
    summary = roast.get("summary", "Get your Solana wallet roasted!")
    score = roast.get("degen_score", 0)
    lines_html = "".join(f'<div class="roast-line">{line}</div>' for line in roast.get("roast_lines", []))
    stats = roast.get("wallet_stats", {})

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Solana Roast Bot 🔥</title>
<meta property="og:title" content="{title} — Solana Roast Bot 🔥">
<meta property="og:description" content="{summary}">
<meta property="og:image" content="{base_url}/api/roast/{wallet}/image">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title} — Solana Roast Bot 🔥">
<meta name="twitter:description" content="{summary}">
<meta name="twitter:image" content="{base_url}/api/roast/{wallet}/image">
<script>
// Redirect to main page with wallet pre-loaded
window.location.href = '/?wallet={wallet}';
</script>
</head>
<body style="background:#0a0515;color:#fff;font-family:sans-serif;padding:40px;text-align:center;">
<h1>🔥 {title}</h1>
<p>{summary}</p>
<p>Degen Score: {score}/100</p>
{lines_html}
<p><a href="/?wallet={wallet}" style="color:#ff7832;">View Full Roast →</a></p>
</body>
</html>"""


@app.get("/api/roast/{wallet}", response_class=HTMLResponse)
async def api_roast_page(wallet: str, request: Request):
    wallet = _validate_wallet(wallet)
    cached = _get_cached(wallet)
    if not cached:
        # Redirect to main page
        return HTMLResponse(
            f'<html><head><script>window.location.href="/?wallet={wallet}";</script></head></html>'
        )
    base_url = str(request.base_url).rstrip("/")
    return HTMLResponse(_og_html(wallet, cached, base_url))


@app.get("/robots.txt")
async def robots():
    return Response(content="User-agent: *\nAllow: /\n", media_type="text/plain")


# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/{wallet}")
async def wallet_page(wallet: str, request: Request):
    """Catch-all for shareable wallet URLs."""
    if wallet in ("favicon.ico", "robots.txt") or wallet.startswith("api/") or wallet.startswith("static/"):
        raise HTTPException(status_code=404)
    try:
        wallet = _validate_wallet(wallet)
    except HTTPException:
        raise HTTPException(status_code=404)
    cached = _get_cached(wallet)
    if cached:
        base_url = str(request.base_url).rstrip("/")
        return HTMLResponse(_og_html(wallet, cached, base_url))
    return FileResponse(str(STATIC_DIR / "index.html"))
