"""Solana Roast Bot — FastAPI backend."""

import asyncio
import html
import json
import os
import re
import time
import traceback
from collections import defaultdict
from pathlib import Path

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

# Initialize Sentry
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FastApiIntegration(), StarletteIntegration()],
        traces_sample_rate=0.2,
        environment=os.environ.get("ENVIRONMENT", "production"),
    )

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.roaster.card_generator import generate_card
from backend.roaster.roast_engine import generate_roast
from backend.roaster.wallet_analyzer import analyze_wallet

app = FastAPI(title="Solana Roast Bot")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Config ---
CACHE_TTL = 3600
RATE_LIMIT = 10  # per IP+wallet per hour
RATE_LIMIT_GLOBAL = 30  # per IP per hour
STATS_FILE = Path(__file__).parent.parent / "data" / "stats.json"
STATIC_DIR = Path(__file__).parent / "static"
ROAST_TIMEOUT = 30  # seconds

# --- In-memory stores ---
roast_cache: dict[str, dict] = {}
rate_limits: dict[str, list[float]] = defaultdict(list)

WALLET_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")

FUNNY_ERRORS = [
    "Even the blockchain doesn't want to talk about this wallet 💀",
    "This wallet is so bad our AI refused to roast it 🤖",
    "The Solana validators collectively agreed to pretend this wallet doesn't exist",
    "Our roast engine caught fire trying to process this dumpster fire 🔥",
    "Error 420: Too much copium detected",
]


# --- Helpers ---
def _load_stats() -> dict:
    try:
        return json.loads(STATS_FILE.read_text())
    except Exception:
        return {"total_roasts": 0, "wallets": {}}


def _save_stats(stats: dict):
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATS_FILE.write_text(json.dumps(stats))


def _check_rate_limit(ip: str, wallet: str) -> bool:
    now = time.time()
    # Per IP+wallet
    key = f"{ip}:{wallet}"
    rate_limits[key] = [t for t in rate_limits[key] if now - t < 3600]
    if len(rate_limits[key]) >= RATE_LIMIT:
        return False
    # Per IP global
    rate_limits[ip] = [t for t in rate_limits[ip] if now - t < 3600]
    if len(rate_limits[ip]) >= RATE_LIMIT_GLOBAL:
        return False
    return True


def _record_rate_limit(ip: str, wallet: str):
    now = time.time()
    rate_limits[f"{ip}:{wallet}"].append(now)
    rate_limits[ip].append(now)


def _get_cached(wallet: str) -> dict | None:
    entry = roast_cache.get(wallet)
    if entry and time.time() - entry["timestamp"] < CACHE_TTL:
        return entry["roast"]
    return None


def _set_cache(wallet: str, roast: dict):
    roast_cache[wallet] = {"roast": roast, "timestamp": time.time()}


def _validate_wallet(wallet: str) -> str:
    wallet = wallet.strip()
    if len(wallet) < 32 or len(wallet) > 44:
        raise HTTPException(status_code=400, detail="Invalid Solana wallet address — wrong length")
    if not WALLET_RE.match(wallet):
        raise HTTPException(status_code=400, detail="Invalid Solana wallet address")
    return wallet


def _funny_error() -> str:
    import random
    return random.choice(FUNNY_ERRORS)


# --- Routes ---


class RoastRequest(BaseModel):
    wallet: str


@app.post("/api/roast")
async def api_roast(req: RoastRequest, request: Request):
    wallet = _validate_wallet(req.wallet)
    ip = request.client.host if request.client else "unknown"

    if not _check_rate_limit(ip, wallet):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Touch some grass and try again later. 🌱")

    # Check cache
    cached = _get_cached(wallet)
    if cached:
        return cached

    try:
        analysis = await asyncio.wait_for(analyze_wallet(wallet), timeout=ROAST_TIMEOUT)
        roast = await asyncio.wait_for(generate_roast(analysis), timeout=ROAST_TIMEOUT)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Roast timed out — this wallet is too complex even for us 🕐")
    except Exception as e:
        traceback.print_exc()
        print(f"❌ Roast failed for {wallet}: {e}")
        sentry_sdk.capture_exception(e)
        sentry_sdk.set_context("wallet", {"address": wallet})
        raise HTTPException(status_code=500, detail=_funny_error())

    _set_cache(wallet, roast)
    _record_rate_limit(ip, wallet)

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

    try:
        png = generate_card(cached, wallet)
    except Exception:
        raise HTTPException(status_code=500, detail="Card generation failed")

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
    title = html.escape(roast.get("title", "Solana Roast Bot"))
    summary = html.escape(roast.get("summary", "Get your Solana wallet roasted!"))
    score = int(roast.get("degen_score", 0))
    safe_wallet = html.escape(wallet)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Solana Roast Bot 🔥</title>
<meta property="og:title" content="{title} — Solana Roast Bot 🔥">
<meta property="og:description" content="{summary}">
<meta property="og:image" content="{html.escape(base_url)}/api/roast/{safe_wallet}/image">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title} — Solana Roast Bot 🔥">
<meta name="twitter:description" content="{summary}">
<meta name="twitter:image" content="{html.escape(base_url)}/api/roast/{safe_wallet}/image">
<meta name="description" content="Solana wallet roast — degen score {score}/100. {summary}">
<script>window.location.href='/?wallet={safe_wallet}';</script>
</head>
<body style="background:#0a0515;color:#fff;font-family:sans-serif;padding:40px;text-align:center;">
<h1>🔥 {title}</h1>
<p>{summary}</p>
<p>Degen Score: {score}/100</p>
<p><a href="/?wallet={safe_wallet}" style="color:#ff7832;">View Full Roast →</a></p>
</body>
</html>"""


@app.get("/api/roast/{wallet}", response_class=HTMLResponse)
async def api_roast_page(wallet: str, request: Request):
    wallet = _validate_wallet(wallet)
    cached = _get_cached(wallet)
    if not cached:
        safe = html.escape(wallet)
        return HTMLResponse(
            f'<html><head><script>window.location.href="/?wallet={safe}";</script></head></html>'
        )
    base_url = str(request.base_url).rstrip("/")
    return HTMLResponse(_og_html(wallet, cached, base_url))


@app.get("/robots.txt")
async def robots():
    return Response(content="User-agent: *\nAllow: /\n", media_type="text/plain")


# Mount static files (serves built React app assets + images)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")
app.mount("/img", StaticFiles(directory=str(STATIC_DIR / "img")), name="img")


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/{wallet}")
async def wallet_page(wallet: str, request: Request):
    if wallet in ("favicon.ico", "robots.txt") or wallet.startswith("api/") or wallet.startswith("static/") or wallet.startswith("assets/") or wallet.startswith("img/"):
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
