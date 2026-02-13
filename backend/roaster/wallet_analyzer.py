"""Wallet analyzer — fetches on-chain data for a Solana wallet."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import httpx

SOLANA_RPC = "https://api.mainnet-beta.solana.com"
SOL_MINT = "So11111111111111111111111111111111111111112"

# --- Token list cache ---
_token_cache: dict[str, dict] = {}
_token_cache_ts: float = 0
TOKEN_CACHE_TTL = 6 * 3600  # 6 hours

KNOWN_PROGRAMS = {
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "Jupiter",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "Orca",
    "MERLuDFBMmsHnsBPZw2sDQZHvXFMwp8EdjudcU2HKky": "Mercurial",
    "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY": "Phoenix",
    "TSWAPaqyCSx2KABk68Shruf4rp7CxcNi8hAsbdwmHbN": "Tensor",
    "M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K": "Magic Eden",
    "MarBmsSgKXdrN1egZf5sqe1TMai9K1rChYNDJgjq7aD": "Marinade",
    "11111111111111111111111111111111": "System",
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA": "Token Program",
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL": "ATA Program",
}


async def _fetch_token_list(client: httpx.AsyncClient) -> dict[str, dict]:
    """Fetch and cache Solana token list. Returns {mint: {symbol, name}}."""
    global _token_cache, _token_cache_ts
    if _token_cache and time.time() - _token_cache_ts < TOKEN_CACHE_TTL:
        return _token_cache

    try:
        r = await client.get(
            "https://cdn.jsdelivr.net/gh/solana-labs/token-list@main/src/tokens/solana.tokenlist.json",
            timeout=15,
        )
        data = r.json()
        tokens = data.get("tokens", [])
        cache = {}
        for t in tokens:
            if t.get("chainId") == 101:  # mainnet
                cache[t["address"]] = {"symbol": t.get("symbol", ""), "name": t.get("name", "")}
        _token_cache = cache
        _token_cache_ts = time.time()
        return cache
    except Exception:
        return _token_cache or {}


async def _rpc(client: httpx.AsyncClient, method: str, params: list | None = None) -> Any:
    r = await client.post(
        SOLANA_RPC,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []},
        timeout=15,
    )
    data = r.json()
    if "error" in data:
        raise Exception(f"RPC error: {data['error']}")
    return data.get("result")


async def _get_sol_balance(client: httpx.AsyncClient, wallet: str) -> float:
    result = await _rpc(client, "getBalance", [wallet])
    return (result or {}).get("value", 0) / 1e9


async def _get_sol_price(client: httpx.AsyncClient) -> float:
    """Get SOL price with fallback chain."""
    # CoinGecko (reliable, no auth needed)
    try:
        r = await client.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd",
            timeout=10,
        )
        data = r.json()
        price = float(data["solana"]["usd"])
        if price > 0:
            return price
    except Exception:
        pass

    # Jupiter v2 (may need auth now)
    try:
        r = await client.get(f"https://api.jup.ag/price/v2?ids={SOL_MINT}", timeout=10)
        data = r.json()
        price = float(data["data"][SOL_MINT]["price"])
        if price > 0:
            return price
    except Exception:
        pass

    return 0.0


async def _get_signatures(client: httpx.AsyncClient, wallet: str, limit: int = 1000) -> list:
    result = await _rpc(client, "getSignaturesForAddress", [wallet, {"limit": limit}])
    return result or []


async def _get_token_accounts(client: httpx.AsyncClient, wallet: str) -> list:
    result = await _rpc(
        client,
        "getTokenAccountsByOwner",
        [wallet, {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}, {"encoding": "jsonParsed"}],
    )
    return (result or {}).get("value", [])


async def _get_recent_transactions(client: httpx.AsyncClient, signatures: list, limit: int = 10) -> list:
    """Fetch details of recent transactions to analyze programs used."""
    txns = []
    for sig in signatures[:limit]:
        try:
            result = await _rpc(client, "getTransaction", [
                sig["signature"],
                {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
            ])
            if result:
                txns.append(result)
        except Exception:
            continue
    return txns


def _analyze_signatures(sigs: list) -> dict:
    if not sigs:
        return {"total": 0, "failed": 0, "first_ts": None, "last_ts": None,
                "hour_distribution": {}, "txs_per_day": 0, "burst_count": 0, "late_night_txs": 0}

    failed = sum(1 for s in sigs if s.get("err") is not None)
    timestamps = [s["blockTime"] for s in sigs if s.get("blockTime")]

    # Time-of-day analysis
    hour_dist: dict[int, int] = {}
    for ts in timestamps:
        hour = datetime.fromtimestamp(ts, tz=timezone.utc).hour
        hour_dist[hour] = hour_dist.get(hour, 0) + 1

    # Late night count (0-5 AM UTC)
    late_night_txs = sum(hour_dist.get(h, 0) for h in range(0, 6))

    # Txs per day
    txs_per_day = 0
    if timestamps and len(timestamps) > 1:
        span_days = max((max(timestamps) - min(timestamps)) / 86400, 1)
        txs_per_day = round(len(timestamps) / span_days, 1)

    # Burst detection (5+ txs within 5 minutes)
    burst_count = 0
    sorted_ts = sorted(timestamps)
    for i in range(len(sorted_ts) - 4):
        if sorted_ts[i + 4] - sorted_ts[i] < 300:
            burst_count += 1

    return {
        "total": len(sigs),
        "failed": failed,
        "first_ts": min(timestamps) if timestamps else None,
        "last_ts": max(timestamps) if timestamps else None,
        "hour_distribution": hour_dist,
        "late_night_txs": late_night_txs,
        "txs_per_day": txs_per_day,
        "burst_count": burst_count,
    }


def _analyze_tokens(accounts: list, token_list: dict) -> list:
    tokens = []
    for acc in accounts:
        info = acc.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
        token_amount = info.get("tokenAmount", {})
        amount = float(token_amount.get("uiAmount") or 0)
        if amount <= 0:
            continue
        mint = info.get("mint", "")
        token_info = token_list.get(mint)
        if token_info:
            symbol = token_info["symbol"]
            is_known = True
        else:
            symbol = "SHITCOIN"
            is_known = False
        tokens.append({
            "mint": mint,
            "amount": amount,
            "decimals": token_amount.get("decimals", 0),
            "symbol": symbol,
            "is_known": is_known,
        })
    return sorted(tokens, key=lambda t: t["amount"], reverse=True)


def _analyze_recent_txns(txns: list) -> dict:
    """Analyze recent transactions for programs used."""
    programs_used: dict[str, int] = {}
    swap_count = 0
    nft_count = 0

    for tx in txns:
        msg = tx.get("transaction", {}).get("message", {})
        instructions = msg.get("instructions", [])
        for ix in instructions:
            program_id = ix.get("programId", "")
            name = KNOWN_PROGRAMS.get(program_id, "")
            if name:
                programs_used[name] = programs_used.get(name, 0) + 1
            if name in ("Jupiter", "Raydium", "Orca"):
                swap_count += 1
            if name in ("Tensor", "Magic Eden"):
                nft_count += 1

        # Also check inner instructions
        meta = tx.get("meta", {})
        for inner in (meta.get("innerInstructions") or []):
            for ix in inner.get("instructions", []):
                program_id = ix.get("programId", "")
                name = KNOWN_PROGRAMS.get(program_id, "")
                if name:
                    programs_used[name] = programs_used.get(name, 0) + 1

    return {
        "programs_used": programs_used,
        "swap_count": swap_count,
        "nft_activity": nft_count,
    }


async def analyze_wallet(wallet: str) -> dict:
    """Main entry point — returns full wallet analysis dict."""
    async with httpx.AsyncClient() as client:
        # Parallel fetches
        balance_task = _get_sol_balance(client, wallet)
        price_task = _get_sol_price(client)
        sigs_task = _get_signatures(client, wallet)
        tokens_task = _get_token_accounts(client, wallet)
        token_list_task = _fetch_token_list(client)

        results = await asyncio.gather(
            balance_task, price_task, sigs_task, tokens_task, token_list_task,
            return_exceptions=True,
        )

        sol_balance = results[0] if not isinstance(results[0], Exception) else 0.0
        sol_price = results[1] if not isinstance(results[1], Exception) else 0.0
        signatures = results[2] if not isinstance(results[2], Exception) else []
        token_accounts = results[3] if not isinstance(results[3], Exception) else []
        token_list = results[4] if not isinstance(results[4], Exception) else {}

        sig_analysis = _analyze_signatures(signatures)
        token_list_parsed = _analyze_tokens(token_accounts, token_list)

        # Fetch recent transactions for program analysis
        txn_analysis = {"programs_used": {}, "swap_count": 0, "nft_activity": 0}
        if signatures:
            try:
                recent_txns = await _get_recent_transactions(client, signatures, limit=10)
                txn_analysis = _analyze_recent_txns(recent_txns)
            except Exception:
                pass

        # Wallet age
        wallet_age_days = None
        if sig_analysis["first_ts"]:
            wallet_age_days = (time.time() - sig_analysis["first_ts"]) / 86400

        # Token stats
        dust_count = sum(1 for t in token_list_parsed if t["amount"] < 1)
        known_count = sum(1 for t in token_list_parsed if t["is_known"])
        shitcoin_count = sum(1 for t in token_list_parsed if not t["is_known"])
        failure_rate = round(sig_analysis["failed"] / sig_analysis["total"] * 100, 1) if sig_analysis["total"] > 0 else 0

        return {
            "wallet": wallet,
            "sol_balance": round(sol_balance, 4),
            "sol_usd": round(sol_balance * sol_price, 2),
            "sol_price": round(sol_price, 2),
            "token_count": len(token_list_parsed),
            "top_tokens": token_list_parsed[:10],
            "dust_tokens": dust_count,
            "known_token_count": known_count,
            "shitcoin_count": shitcoin_count,
            "transaction_count": sig_analysis["total"],
            "failed_transactions": sig_analysis["failed"],
            "failure_rate": failure_rate,
            "wallet_age_days": round(wallet_age_days) if wallet_age_days else None,
            "first_tx_date": datetime.fromtimestamp(sig_analysis["first_ts"], tz=timezone.utc).isoformat() if sig_analysis["first_ts"] else None,
            "late_night_txs": sig_analysis.get("late_night_txs", 0),
            "txs_per_day": sig_analysis.get("txs_per_day", 0),
            "burst_count": sig_analysis.get("burst_count", 0),
            "hour_distribution": sig_analysis.get("hour_distribution", {}),
            "swap_count": txn_analysis.get("swap_count", 0),
            "protocols_used": list(txn_analysis.get("programs_used", {}).keys()),
            "nft_activity": txn_analysis.get("nft_activity", 0),
            "is_empty": sol_balance == 0 and len(token_list_parsed) == 0 and sig_analysis["total"] == 0,
        }
