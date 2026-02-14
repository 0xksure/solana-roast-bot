"""FairScale API client — reputation scoring for Solana wallets."""

import logging
import os
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

FAIRSCALE_BASE_URL = "https://api.fairscale.xyz"
FAIRSCALE_API_KEY = os.environ.get("FAIRSCALE_API_KEY", "")
CACHE_TTL = 3600  # 1 hour

# In-memory hot cache
_cache: dict[str, dict] = {}


def _is_configured() -> bool:
    return bool(FAIRSCALE_API_KEY)


async def get_fairscore(wallet: str) -> Optional[dict]:
    """Fetch full FairScale score for a wallet. Returns None if unavailable."""
    if not _is_configured():
        logger.debug("FairScale API key not configured, skipping")
        return None

    # Check hot cache
    cached = _cache.get(wallet)
    if cached and time.time() - cached.get("_cached_at", 0) < CACHE_TTL:
        return cached

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{FAIRSCALE_BASE_URL}/score",
                params={"wallet": wallet},
                headers={"fairkey": FAIRSCALE_API_KEY},
            )
            if resp.status_code == 429:
                logger.warning("FairScale rate limited")
                return cached  # Return stale cache if available
            resp.raise_for_status()
            data = resp.json()
            data["_cached_at"] = time.time()
            _cache[wallet] = data
            return data
    except Exception as e:
        logger.error(f"FairScale API error: {e}")
        return cached  # Graceful degradation


async def get_fairscore_quick(wallet: str) -> Optional[int]:
    """Fetch just the FairScore integer (lightweight endpoint)."""
    if not _is_configured():
        return None

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{FAIRSCALE_BASE_URL}/fairScore",
                params={"wallet": wallet},
                headers={"fairkey": FAIRSCALE_API_KEY},
            )
            resp.raise_for_status()
            return resp.json().get("fair_score")
    except Exception:
        return None


def format_for_roast(data: dict) -> str:
    """Format FairScale data as context string for the AI roast prompt."""
    if not data:
        return ""

    parts = [
        f"\n--- REPUTATION DATA (FairScale) ---",
        f"FairScore: {data.get('fairscore', 'N/A')} (base: {data.get('fairscore_base', 'N/A')})",
        f"Social Score: {data.get('social_score', 'N/A')}",
        f"Reputation Tier: {data.get('tier', 'unknown').upper()}",
    ]

    badges = data.get("badges", [])
    if badges:
        badge_str = ", ".join(b.get("label", b.get("id", "?")) for b in badges)
        parts.append(f"Badges: {badge_str}")

    features = data.get("features", {})
    if features:
        parts.append(f"Wallet Age: {features.get('wallet_age_days', '?')} days")
        parts.append(f"Active Days: {features.get('active_days', '?')}")
        parts.append(f"TX Count: {features.get('tx_count', '?')}")
        if features.get("native_sol_percentile"):
            parts.append(f"SOL Holdings Percentile: {features['native_sol_percentile']:.0%}")

    parts.append(
        "Use this reputation data to contrast with their degen behavior. "
        "A high FairScore + high degen = 'trusted degen'. "
        "Low FairScore + high degen = 'anonymous ape'. "
        "High FairScore + low degen = 'boring but respectable'. "
        "Make it funny."
    )

    return "\n".join(parts)
