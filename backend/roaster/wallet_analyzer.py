"""Wallet analyzer — fetches on-chain data for a Solana wallet."""

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import os

import httpx

logger = logging.getLogger(__name__)

SOLANA_RPC = "https://api.mainnet-beta.solana.com"
SOL_MINT = "So11111111111111111111111111111111111111112"

# Helius for enhanced transaction history
HELIUS_API_KEY = "".join(os.environ.get("HELIUS_API_KEY", "").split())
HELIUS_BASE = f"https://api.helius.xyz/v0" if HELIUS_API_KEY else ""

# --- Token list cache ---
_token_cache: dict[str, dict] = {}
_token_cache_ts: float = 0
TOKEN_CACHE_TTL = 6 * 3600  # 6 hours

MAX_HELIUS_PAGES = int(os.environ.get("MAX_HELIUS_PAGES", "200"))
MAX_RPC_SIG_PAGES = int(os.environ.get("MAX_RPC_SIG_PAGES", "50"))

KNOWN_PROGRAMS = {
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "Jupiter",
    "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB": "Jupiter V4",
    "jCebN34bUfdeUYJT13J1yG16XWQpt5PDx6Mse9GUqhR": "Jupiter Limit Order",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium",
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK": "Raydium CLMM",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "Orca",
    "DjVE6JNiYqPL2QXyCUUh8rNjHrbz9hXHNYt99MQ59qw1": "Orca (Legacy)",
    "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin": "Serum/OpenBook",
    "MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA": "Marginfi",
    "So1endDq2YkqhipRh3WViPa8hdiSpxWy6z3Z6tMCpAo": "Solend",
    "MERLuDFBMmsHnsBPZw2sDQZHvXFMwp8EdjudcU2HKky": "Mercurial",
    "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY": "Phoenix",
    "TSWAPaqyCSx2KABk68Shruf4rp7CxcNi8hAsbdwmHbN": "Tensor",
    "M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K": "Magic Eden",
    "MarBmsSgKXdrN1egZf5sqe1TMai9K1rChYNDJgjq7aD": "Marinade",
    "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s": "Metaplex",
    "11111111111111111111111111111111": "System",
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA": "Token Program",
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL": "Associated Token",
    # DeFi
    "DRiFTiKWQGEhGJMFB9gNbFLo9LkB4W8UT1VeR5bHBygh": "Drift",
    "MEisE1HzehtrDpAAT8PnLHjpSSkRYakotTuJRPjTpo8": "Meteora",
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": "Pump.fun",
    "moonshineXmXLn2GKnFNRRRXHWJmFNBQYeVzGJEXHF3": "Moonshot",
    "srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX": "Serum V3",
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo": "Meteora DLMM",
    "StakesGhostwLxaVDuWmMdBQPEE9K3sNjHqRVpAfaz": "Stakenet",
    "jdswHyVGU9qmvSZqczSk6gCkJQPALmFLND5aTj7QjDu": "Jito",
    # NFT
    "CJsLwbP1iu5DuUikMin8LH9xfIRST3k45wfnwCSR1Gp": "Tensor cNFT",
    "hadeK9DLv9eA7ya5KCTqSvSvRZeJC3JgD5a9Y3CNbvu": "Hadeswap",
    # Governance
    "GovER5Lthms3bLBqWub97yVRqDfY73swg5bUCAGR12a": "Governance",
    "AutoSPBP5JYLNgFiNELqL88vHsqZBob77qBUWBEL5zn": "Autocrat/Futarchy",
    # Infrastructure
    "ComputeBudget111111111111111111111111111111": "Compute Budget",
    "AddressLookupTab1e1111111111111111111111111": "Address Lookup",
}

# Monthly average SOL prices (USD) — historical data
SOL_PRICE_HISTORY: dict[str, float] = {
    "2021-01": 3.5, "2021-02": 10.0, "2021-03": 15.0, "2021-04": 30.0,
    "2021-05": 40.0, "2021-06": 30.0, "2021-07": 28.0, "2021-08": 65.0,
    "2021-09": 150.0, "2021-10": 175.0, "2021-11": 220.0, "2021-12": 180.0,
    "2022-01": 130.0, "2022-02": 100.0, "2022-03": 95.0, "2022-04": 100.0,
    "2022-05": 50.0, "2022-06": 35.0, "2022-07": 38.0, "2022-08": 35.0,
    "2022-09": 33.0, "2022-10": 32.0, "2022-11": 14.0, "2022-12": 12.0,
    "2023-01": 12.0, "2023-02": 22.0, "2023-03": 20.0, "2023-04": 22.0,
    "2023-05": 20.0, "2023-06": 16.0, "2023-07": 24.0, "2023-08": 21.0,
    "2023-09": 20.0, "2023-10": 30.0, "2023-11": 55.0, "2023-12": 90.0,
    "2024-01": 95.0, "2024-02": 110.0, "2024-03": 185.0, "2024-04": 140.0,
    "2024-05": 160.0, "2024-06": 140.0, "2024-07": 155.0, "2024-08": 140.0,
    "2024-09": 135.0, "2024-10": 155.0, "2024-11": 230.0, "2024-12": 200.0,
    "2025-01": 210.0, "2025-02": 190.0, "2025-03": 175.0, "2025-04": 150.0,
    "2025-05": 165.0, "2025-06": 160.0, "2025-07": 170.0, "2025-08": 175.0,
    "2025-09": 180.0, "2025-10": 185.0, "2025-11": 190.0, "2025-12": 195.0,
    "2026-01": 200.0, "2026-02": 205.0,
}

SWAP_PROGRAMS = {
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
}

MARKET_EVENTS = {
    "2021-09": {"event": "Solana ATH run to $260", "sentiment": "peak euphoria"},
    "2021-11": {"event": "Solana hits $260 ATH", "sentiment": "top signal"},
    "2022-01": {"event": "Crypto winter begins", "sentiment": "denial"},
    "2022-05": {"event": "LUNA/UST collapse", "sentiment": "panic"},
    "2022-06": {"event": "3AC & Celsius collapse", "sentiment": "capitulation"},
    "2022-11": {"event": "FTX collapse, SOL drops to $8", "sentiment": "extinction level"},
    "2023-01": {"event": "SOL bottoms around $8-10", "sentiment": "max pain"},
    "2023-10": {"event": "SOL recovery begins, hits $30+", "sentiment": "cautious optimism"},
    "2023-12": {"event": "Solana DeFi renaissance, Jito airdrop", "sentiment": "FOMO returns"},
    "2024-01": {"event": "Jupiter airdrop, memecoin season begins", "sentiment": "full degen"},
    "2024-03": {"event": "SOL hits $200, BONK/WIF mania", "sentiment": "peak degen"},
    "2024-11": {"event": "Trump pump, SOL hits $260+", "sentiment": "new ATH euphoria"},
    "2025-01": {"event": "TRUMP memecoin launch", "sentiment": "peak memecoin mania"},
    "2025-06": {"event": "Market cooldown", "sentiment": "reality check"},
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

    try:
        r = await client.get(f"https://api.jup.ag/price/v2?ids={SOL_MINT}", timeout=10)
        data = r.json()
        price = float(data["data"][SOL_MINT]["price"])
        if price > 0:
            return price
    except Exception:
        pass

    return 0.0


async def _get_signatures(client: httpx.AsyncClient, wallet: str, limit: int = 1000, max_pages: int = MAX_RPC_SIG_PAGES) -> list:
    """Fetch transaction signatures with pagination for deeper history."""
    all_sigs = []
    before = None
    for _ in range(max_pages):
        opts = {"limit": limit}
        if before:
            opts["before"] = before
        result = await _rpc(client, "getSignaturesForAddress", [wallet, opts])
        if not result:
            break
        all_sigs.extend(result)
        if len(result) < limit:
            break  # No more pages
        before = result[-1].get("signature")
    return all_sigs


async def _get_helius_history(client: httpx.AsyncClient, wallet: str, max_pages: int = MAX_HELIUS_PAGES) -> list:
    """Fetch full parsed transaction history from Helius Enhanced API."""
    if not HELIUS_API_KEY:
        return []
    
    all_txns = []
    before_sig = ""
    url = f"{HELIUS_BASE}/addresses/{wallet}/transactions?api-key={HELIUS_API_KEY}"
    
    for page in range(max_pages):
        try:
            page_url = url
            if before_sig:
                page_url += f"&before={before_sig}"
            resp = await client.get(page_url, timeout=20)
            if resp.status_code == 429:
                logger.warning("Helius rate limited at page %d, waiting 2s", page)
                await asyncio.sleep(2)
                resp = await client.get(page_url, timeout=20)
            if resp.status_code != 200:
                logger.warning("Helius API returned %d at page %d", resp.status_code, page)
                break
            txns = resp.json()
            if not txns:
                break
            all_txns.extend(txns)
            before_sig = txns[-1].get("signature", "")
            if len(txns) < 100:  # Last page
                break
            await asyncio.sleep(0.1)  # Rate limit: 100ms between pages
        except Exception as e:
            logger.error("Helius fetch error at page %d: %s", page, e)
            break
    
    return all_txns


def _analyze_helius_txns(txns: list) -> dict:
    """Analyze Helius enhanced transaction data for richer insights."""
    swap_count = 0
    nft_count = 0
    programs = defaultdict(int)
    types = defaultdict(int)
    total_sol_moved = 0.0
    swaps = []
    
    for tx in txns:
        tx_type = tx.get("type", "UNKNOWN")
        types[tx_type] += 1
        
        if tx_type == "SWAP":
            swap_count += 1
            # Extract swap details from tokenTransfers
            sol_in = 0
            sol_out = 0
            for transfer in tx.get("tokenTransfers", []):
                if transfer.get("mint") == SOL_MINT:
                    amount = transfer.get("tokenAmount", 0)
                    if transfer.get("fromUserAccount") == tx.get("feePayer"):
                        sol_out += amount
                    else:
                        sol_in += amount
            swaps.append({
                "sol_in": sol_in, "sol_out": sol_out,
                "timestamp": tx.get("timestamp", 0),
                "signature": tx.get("signature", ""),
            })
        elif tx_type in ("NFT_SALE", "NFT_MINT", "NFT_LISTING", "NFT_BID"):
            nft_count += 1
        
        # Track programs (map to readable names) — use comprehensive registry
        from backend.roaster.program_registry import PROGRAM_ID_TO_NAME
        for inst in tx.get("instructions", []):
            pid = inst.get("programId", "")
            if pid:
                name = PROGRAM_ID_TO_NAME.get(pid) or KNOWN_PROGRAMS.get(pid, pid[:12] + "..." if len(pid) > 12 else pid)
                programs[name] += 1
        
        # Track native SOL transfers
        for nt in tx.get("nativeTransfers", []):
            total_sol_moved += abs(nt.get("amount", 0)) / 1e9
    
    # PnL from swaps
    wins = 0
    losses = 0
    total_pnl = 0
    biggest_win_val = 0
    biggest_loss_val = 0
    
    for s in swaps:
        net = s["sol_in"] - s["sol_out"]
        total_pnl += net
        if net > 0:
            wins += 1
            if net > biggest_win_val:
                biggest_win_val = net
        elif net < 0:
            losses += 1
            if abs(net) > biggest_loss_val:
                biggest_loss_val = abs(net)
    
    total_trades = wins + losses
    
    return {
        "swap_count": swap_count,
        "nft_count": nft_count,
        "programs": dict(programs),
        "tx_types": dict(types),
        "total_sol_moved": round(total_sol_moved, 2),
        "total_swaps_detected": len(swaps),
        "estimated_pnl_sol": round(total_pnl, 4),
        "win_rate": round(wins / total_trades * 100, 1) if total_trades > 0 else 0,
        "biggest_win": round(biggest_win_val, 4) if biggest_win_val else None,
        "biggest_loss": round(biggest_loss_val, 4) if biggest_loss_val else None,
        "total_sol_volume": round(sum(s["sol_out"] for s in swaps), 2),
    }


async def _get_token_accounts(client: httpx.AsyncClient, wallet: str) -> list:
    result = await _rpc(
        client,
        "getTokenAccountsByOwner",
        [wallet, {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}, {"encoding": "jsonParsed"}],
    )
    return (result or {}).get("value", [])


async def _get_transaction_parsed(client: httpx.AsyncClient, signature: str) -> dict | None:
    """Fetch a single parsed transaction with timeout."""
    try:
        result = await _rpc(client, "getTransaction", [
            signature,
            {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
        ])
        return result
    except Exception:
        return None


async def _get_recent_transactions(client: httpx.AsyncClient, signatures: list, limit: int = 20) -> list:
    """Fetch details of recent transactions with rate limiting. Max 20 calls."""
    txns = []
    fetch_limit = min(limit, 20)
    for sig in signatures[:fetch_limit]:
        tx = await _get_transaction_parsed(client, sig["signature"])
        if tx:
            txns.append(tx)
        await asyncio.sleep(0.1)  # Rate limiting: 100ms between calls
    return txns


async def _get_sampled_transactions(client: httpx.AsyncClient, signatures: list, wallet: str, max_calls: int = 30) -> list:
    """Sample transactions across full wallet history for balance snapshots and protocol detection.

    Strategy: Pick the LAST transaction of each active month (for end-of-month balance).
    If more months than budget, evenly sample months.
    Always include the 10 most recent transactions for current data.
    """
    if not signatures:
        return []

    # Always include the 10 most recent signatures
    recent_budget = min(10, len(signatures))
    recent_sigs = set(s["signature"] for s in signatures[:recent_budget])

    # Group signatures by month, pick the LAST (oldest) signature per month for end-of-month balance
    monthly_last: dict[str, dict] = {}
    for sig in signatures:
        bt = sig.get("blockTime")
        if not bt:
            continue
        month_key = datetime.fromtimestamp(bt, tz=timezone.utc).strftime("%Y-%m")
        # Signatures are returned newest-first, so the last one we see per month is the oldest
        monthly_last[month_key] = sig

    # Budget for historical samples
    history_budget = max_calls - recent_budget
    sorted_months = sorted(monthly_last.keys())

    if len(sorted_months) <= history_budget:
        sampled_months = sorted_months
    else:
        # Evenly sample across months
        step = len(sorted_months) / history_budget
        sampled_months = []
        for i in range(history_budget):
            idx = int(i * step)
            sampled_months.append(sorted_months[idx])
        # Always include first and last month
        if sorted_months[0] not in sampled_months:
            sampled_months[0] = sorted_months[0]
        if sorted_months[-1] not in sampled_months:
            sampled_months[-1] = sorted_months[-1]

    # Collect all signatures to fetch (deduplicated)
    sigs_to_fetch: dict[str, bool] = {}
    for s in signatures[:recent_budget]:
        sigs_to_fetch[s["signature"]] = True
    for month in sampled_months:
        sig = monthly_last[month]
        sigs_to_fetch[sig["signature"]] = True

    # Fetch all selected transactions
    txns = []
    for sig_str in sigs_to_fetch:
        tx = await _get_transaction_parsed(client, sig_str)
        if tx:
            txns.append(tx)
        await asyncio.sleep(0.1)
    return txns


def _analyze_signatures(sigs: list) -> dict:
    if not sigs:
        return {"total": 0, "failed": 0, "first_ts": None, "last_ts": None,
                "hour_distribution": {}, "txs_per_day": 0, "burst_count": 0, "late_night_txs": 0}

    failed = sum(1 for s in sigs if s.get("err") is not None)
    timestamps = [s["blockTime"] for s in sigs if s.get("blockTime")]

    hour_dist: dict[int, int] = {}
    for ts in timestamps:
        hour = datetime.fromtimestamp(ts, tz=timezone.utc).hour
        hour_dist[hour] = hour_dist.get(hour, 0) + 1

    late_night_txs = sum(hour_dist.get(h, 0) for h in range(0, 6))

    txs_per_day = 0
    if timestamps and len(timestamps) > 1:
        span_days = max((max(timestamps) - min(timestamps)) / 86400, 1)
        txs_per_day = round(len(timestamps) / span_days, 1)

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


def _extract_swaps_from_tx(tx: dict, wallet: str, token_list: dict) -> list[dict]:
    """Extract swap info from a parsed transaction.

    Returns list of swap dicts with token_in, token_out, sol_amount, timestamp, etc.
    """
    swaps = []
    msg = tx.get("transaction", {}).get("message", {})
    meta = tx.get("meta", {})
    block_time = tx.get("blockTime")
    instructions = msg.get("instructions", [])

    # Check if this tx involves a swap program
    is_swap = False
    for ix in instructions:
        if ix.get("programId", "") in SWAP_PROGRAMS:
            is_swap = True
            break
    if not is_swap:
        # Also check inner instructions
        for inner in (meta.get("innerInstructions") or []):
            for ix in inner.get("instructions", []):
                if ix.get("programId", "") in SWAP_PROGRAMS:
                    is_swap = True
                    break
            if is_swap:
                break

    if not is_swap:
        return []

    # Analyze token balance changes (pre/post balances)
    pre_balances = meta.get("preTokenBalances") or []
    post_balances = meta.get("postTokenBalances") or []

    # Build balance diff by mint
    pre_map: dict[str, float] = {}
    post_map: dict[str, float] = {}

    for b in pre_balances:
        owner = b.get("owner", "")
        if owner == wallet:
            mint = b.get("mint", "")
            amt = float((b.get("uiTokenAmount") or {}).get("uiAmount") or 0)
            pre_map[mint] = pre_map.get(mint, 0) + amt

    for b in post_balances:
        owner = b.get("owner", "")
        if owner == wallet:
            mint = b.get("mint", "")
            amt = float((b.get("uiTokenAmount") or {}).get("uiAmount") or 0)
            post_map[mint] = post_map.get(mint, 0) + amt

    # Also check SOL balance change
    account_keys = msg.get("accountKeys", [])
    wallet_idx = None
    for i, key in enumerate(account_keys):
        k = key if isinstance(key, str) else key.get("pubkey", "")
        if k == wallet:
            wallet_idx = i
            break

    sol_change = 0.0
    if wallet_idx is not None:
        pre_sol = (meta.get("preBalances") or [0] * (wallet_idx + 1))[wallet_idx] / 1e9
        post_sol = (meta.get("postBalances") or [0] * (wallet_idx + 1))[wallet_idx] / 1e9
        sol_change = post_sol - pre_sol

    # Determine what went in and what came out
    all_mints = set(list(pre_map.keys()) + list(post_map.keys()))
    token_in = None  # token spent
    token_out = None  # token received

    for mint in all_mints:
        diff = post_map.get(mint, 0) - pre_map.get(mint, 0)
        tinfo = token_list.get(mint, {})
        symbol = tinfo.get("symbol", mint[:8] + "...")

        if diff < -0.0001:  # spent
            token_in = {"mint": mint, "symbol": symbol, "amount": abs(diff)}
        elif diff > 0.0001:  # received
            token_out = {"mint": mint, "symbol": symbol, "amount": diff}

    # If SOL changed significantly and no token_in/out covers SOL
    if sol_change < -0.01 and not token_in:
        token_in = {"mint": SOL_MINT, "symbol": "SOL", "amount": abs(sol_change)}
    elif sol_change > 0.01 and not token_out:
        token_out = {"mint": SOL_MINT, "symbol": "SOL", "amount": sol_change}

    if token_in or token_out:
        swap = {
            "timestamp": block_time,
            "token_in": token_in,
            "token_out": token_out,
            "sol_change": round(sol_change, 6),
        }
        swaps.append(swap)

    return swaps


def _analyze_swaps(swaps: list) -> dict:
    """Analyze swap history for PnL, biggest wins/losses, win rate."""
    if not swaps:
        return {
            "total_swaps_detected": 0,
            "estimated_pnl_sol": 0,
            "biggest_loss": None,
            "biggest_win": None,
            "win_rate": 0,
            "total_sol_volume": 0,
        }

    total_sol_spent = 0.0  # SOL spent buying tokens
    total_sol_received = 0.0  # SOL received selling tokens
    total_sol_volume = 0.0
    wins = 0
    losses = 0

    biggest_loss = None
    biggest_loss_sol = 0
    biggest_win = None
    biggest_win_sol = 0

    for swap in swaps:
        sol_change = swap.get("sol_change", 0)
        total_sol_volume += abs(sol_change)

        token_in = swap.get("token_in")
        token_out = swap.get("token_out")

        # Buying token with SOL (SOL goes down)
        if token_in and token_in.get("symbol") == "SOL" and token_out:
            sol_spent = token_in.get("amount", 0)
            total_sol_spent += sol_spent
            # This is a buy — track it as potential loss
            if sol_spent > biggest_loss_sol:
                biggest_loss_sol = sol_spent
                biggest_loss = {
                    "token": token_out.get("symbol", "???"),
                    "sol_spent": round(sol_spent, 4),
                    "amount_received": round(token_out.get("amount", 0), 4),
                }

        # Selling token for SOL (SOL goes up)
        elif token_out and token_out.get("symbol") == "SOL" and token_in:
            sol_received = token_out.get("amount", 0)
            total_sol_received += sol_received
            wins += 1
            if sol_received > biggest_win_sol:
                biggest_win_sol = sol_received
                biggest_win = {
                    "token": token_in.get("symbol", "???"),
                    "sol_received": round(sol_received, 4),
                    "amount_sold": round(token_in.get("amount", 0), 4),
                }
        else:
            # Token-to-token swap, count as neutral
            if sol_change < -0.01:
                losses += 1
            elif sol_change > 0.01:
                wins += 1

    total_trades = wins + losses
    win_rate = round(wins / total_trades, 2) if total_trades > 0 else 0
    estimated_pnl = round(total_sol_received - total_sol_spent, 4)

    # Enrich biggest loss with loss percentage estimate
    if biggest_loss:
        biggest_loss["loss_pct"] = 99.9  # Assume worst — we can't check current value easily
        biggest_loss["current_value_sol"] = 0.0  # Conservative estimate

    if biggest_win:
        biggest_win["gain_pct"] = round((biggest_win_sol / max(0.001, biggest_loss_sol)) * 100, 1) if biggest_loss_sol > 0 else 0

    return {
        "total_swaps_detected": len(swaps),
        "estimated_pnl_sol": estimated_pnl,
        "biggest_loss": biggest_loss,
        "biggest_win": biggest_win,
        "win_rate": win_rate,
        "total_sol_volume": round(total_sol_volume, 4),
    }


def _analyze_timeline(sigs: list) -> dict:
    """Map wallet activity to market events timeline."""
    if not sigs:
        return {
            "active_periods": [],
            "peak_activity_period": None,
            "inactive_gaps": [],
            "joined_during": None,
        }

    timestamps = sorted([s["blockTime"] for s in sigs if s.get("blockTime")])
    if not timestamps:
        return {
            "active_periods": [],
            "peak_activity_period": None,
            "inactive_gaps": [],
            "joined_during": None,
        }

    # Group transactions by month (YYYY-MM)
    monthly_counts: dict[str, int] = defaultdict(int)
    for ts in timestamps:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        key = dt.strftime("%Y-%m")
        monthly_counts[key] += 1

    # Build active periods with market event mapping
    active_periods = []
    for period, count in sorted(monthly_counts.items()):
        entry: dict[str, Any] = {"period": period, "tx_count": count}
        if period in MARKET_EVENTS:
            entry["event"] = MARKET_EVENTS[period]["event"]
            entry["sentiment"] = MARKET_EVENTS[period]["sentiment"]
        active_periods.append(entry)

    # Peak activity period
    peak = max(active_periods, key=lambda x: x["tx_count"]) if active_periods else None

    # Joined during
    first_ts = timestamps[0]
    first_dt = datetime.fromtimestamp(first_ts, tz=timezone.utc)
    first_period = first_dt.strftime("%Y-%m")
    joined = {"period": first_period, "date": first_dt.isoformat()}
    if first_period in MARKET_EVENTS:
        joined["event"] = MARKET_EVENTS[first_period]["event"]
        joined["sentiment"] = MARKET_EVENTS[first_period]["sentiment"]
        # Generate roast based on when they joined
        sentiment = MARKET_EVENTS[first_period]["sentiment"]
        if sentiment in ("top signal", "peak euphoria", "peak degen", "peak memecoin mania"):
            joined["roast"] = "Bought the absolute top"
        elif sentiment in ("extinction level", "capitulation", "panic"):
            joined["roast"] = "Started during the apocalypse — brave or stupid"
        elif sentiment == "max pain":
            joined["roast"] = "Born in the darkness of max pain"
        elif sentiment in ("full degen", "FOMO returns"):
            joined["roast"] = "Classic FOMO entry"
        else:
            joined["roast"] = f"Joined during {MARKET_EVENTS[first_period]['event']}"
    else:
        # Find closest market event
        joined["roast"] = f"Joined in {first_period}"

    # Detect inactive gaps (months with 0 activity)
    if len(timestamps) >= 2:
        all_months = sorted(monthly_counts.keys())
        inactive_gaps = []
        for i in range(len(all_months) - 1):
            current = all_months[i]
            next_m = all_months[i + 1]
            # Parse months
            cy, cm = int(current[:4]), int(current[5:7])
            ny, nm = int(next_m[:4]), int(next_m[5:7])
            gap_months = (ny - cy) * 12 + (nm - cm) - 1
            if gap_months >= 2:
                # What events were missed during the gap?
                missed_events = []
                for event_period, event_data in MARKET_EVENTS.items():
                    ey, em = int(event_period[:4]), int(event_period[5:7])
                    event_total = ey * 12 + em
                    start_total = cy * 12 + cm
                    end_total = ny * 12 + nm
                    if start_total < event_total < end_total:
                        missed_events.append(event_data["event"])
                gap_entry: dict[str, Any] = {
                    "from": current,
                    "to": next_m,
                    "months": gap_months,
                }
                if missed_events:
                    gap_entry["events_missed"] = missed_events
                    gap_entry["event_missed"] = missed_events[0]
                inactive_gaps.append(gap_entry)
    else:
        inactive_gaps = []

    return {
        "active_periods": active_periods,
        "peak_activity_period": peak,
        "inactive_gaps": inactive_gaps,
        "joined_during": joined,
    }


def _analyze_graveyard(accounts: list, token_list: dict) -> dict:
    """Identify 'graveyard' tokens — held tokens with near-zero value or unknown."""
    graveyard_names = []
    for acc in accounts:
        info = acc.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
        token_amount = info.get("tokenAmount", {})
        amount = float(token_amount.get("uiAmount") or 0)
        mint = info.get("mint", "")
        token_info = token_list.get(mint)

        # Graveyard criteria: unknown token OR known token with dust amount
        if amount > 0:
            if not token_info:
                # Unknown token = likely dead/rugged
                graveyard_names.append(mint[:8] + "...")
            elif amount < 0.01 and token_info.get("symbol", "") not in ("SOL", "USDC", "USDT"):
                graveyard_names.append(token_info.get("symbol", mint[:8]))

    return {
        "graveyard_tokens": len(graveyard_names),
        "graveyard_names": graveyard_names[:20],  # Cap at 20 for display
    }


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


def _build_net_worth_timeline(sigs: list, sampled_txns: list, wallet: str) -> list:
    """Build monthly SOL balance from sampled transactions across full history.

    Uses postBalances from sampled txns for actual balance snapshots,
    then interpolates for months without a direct snapshot.
    """
    if not sigs:
        return []

    timestamps = sorted([s["blockTime"] for s in sigs if s.get("blockTime")])
    if not timestamps:
        return []

    # Count txs per month from signatures
    monthly_counts: dict[str, int] = defaultdict(int)
    for ts in timestamps:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        monthly_counts[dt.strftime("%Y-%m")] += 1

    # Extract SOL balances from sampled transactions, keyed by month
    # For each month, use the latest balance snapshot available
    month_balances: dict[str, float] = {}
    tx_by_month: dict[str, list[tuple[int, float]]] = defaultdict(list)

    for tx in sampled_txns:
        bt = tx.get("blockTime")
        if not bt:
            continue
        msg = tx.get("transaction", {}).get("message", {})
        meta = tx.get("meta", {})
        account_keys = msg.get("accountKeys", [])
        for i, key in enumerate(account_keys):
            k = key if isinstance(key, str) else key.get("pubkey", "")
            if k == wallet:
                post_bals = meta.get("postBalances") or []
                if i < len(post_bals):
                    month_key = datetime.fromtimestamp(bt, tz=timezone.utc).strftime("%Y-%m")
                    tx_by_month[month_key].append((bt, post_bals[i] / 1e9))
                break

    # Pick the latest balance per month
    for month_key, entries in tx_by_month.items():
        entries.sort(key=lambda x: x[0])
        month_balances[month_key] = entries[-1][1]  # latest timestamp's balance

    # Build continuous timeline from first month to current month
    first_dt = datetime.fromtimestamp(timestamps[0], tz=timezone.utc)
    now = datetime.now(tz=timezone.utc)
    all_months = []
    y, m = first_dt.year, first_dt.month
    while (y, m) <= (now.year, now.month):
        all_months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1

    # Interpolate: forward-fill from nearest known balance
    timeline = []
    last_known = 0.0
    for month_key in all_months:
        if month_key in month_balances:
            last_known = month_balances[month_key]

        sol_price = SOL_PRICE_HISTORY.get(month_key, 0)
        timeline.append({
            "month": month_key,
            "estimated_sol": round(last_known, 4),
            "tx_count": monthly_counts.get(month_key, 0),
            "sol_price_usd": sol_price,
            "estimated_usd": round(last_known * sol_price, 2),
        })

    return timeline


def _build_protocol_stats(recent_txns: list) -> list:
    """Count protocol interactions from parsed transactions."""
    protocol_counts: dict[str, int] = defaultdict(int)

    for tx in recent_txns:
        msg = tx.get("transaction", {}).get("message", {})
        meta = tx.get("meta", {})
        seen_in_tx: set[str] = set()

        all_instructions = list(msg.get("instructions", []))
        for inner in (meta.get("innerInstructions") or []):
            all_instructions.extend(inner.get("instructions", []))

        for ix in all_instructions:
            program_id = ix.get("programId", "")
            name = KNOWN_PROGRAMS.get(program_id)
            if name and name not in seen_in_tx:
                seen_in_tx.add(name)
                protocol_counts[name] += 1

    total = sum(protocol_counts.values())
    stats = []
    for name, count in sorted(protocol_counts.items(), key=lambda x: -x[1]):
        stats.append({
            "name": name,
            "tx_count": count,
            "pct": round(count / total * 100, 1) if total > 0 else 0,
        })
    return stats


def _build_loss_by_token(swaps: list) -> list:
    """Group losses by token."""
    token_losses: dict[str, dict] = {}  # symbol -> {sol_lost, trades}

    for swap in swaps:
        token_in = swap.get("token_in")
        token_out = swap.get("token_out")
        sol_change = swap.get("sol_change", 0)

        # Buying token with SOL = potential loss
        if token_in and token_in.get("symbol") == "SOL" and token_out:
            symbol = token_out.get("symbol", "???")
            if symbol not in token_losses:
                token_losses[symbol] = {"sol_lost": 0, "trades": 0}
            token_losses[symbol]["sol_lost"] += token_in.get("amount", 0)
            token_losses[symbol]["trades"] += 1

        # Selling token for SOL = recovery (reduce loss)
        elif token_out and token_out.get("symbol") == "SOL" and token_in:
            symbol = token_in.get("symbol", "???")
            if symbol not in token_losses:
                token_losses[symbol] = {"sol_lost": 0, "trades": 0}
            token_losses[symbol]["sol_lost"] -= token_out.get("amount", 0)
            token_losses[symbol]["trades"] += 1

    result = []
    for symbol, data in token_losses.items():
        if data["sol_lost"] > 0:  # Only include net losses
            result.append({
                "token": symbol,
                "sol_lost": round(data["sol_lost"], 4),
                "trades": data["trades"],
            })
    return sorted(result, key=lambda x: -x["sol_lost"])


def _build_loss_by_period(swaps: list) -> list:
    """Group losses by month."""
    monthly_losses: dict[str, float] = defaultdict(float)

    for swap in swaps:
        ts = swap.get("timestamp")
        sol_change = swap.get("sol_change", 0)
        if ts and sol_change < 0:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            key = dt.strftime("%Y-%m")
            monthly_losses[key] += abs(sol_change)

    result = []
    for month, loss in sorted(monthly_losses.items(), key=lambda x: -x[1]):
        entry: dict[str, Any] = {
            "month": month,
            "sol_lost": round(loss, 4),
        }
        if month in MARKET_EVENTS:
            entry["event"] = MARKET_EVENTS[month]["event"]
        result.append(entry)
    return result


def _build_activity_heatmap(sigs: list) -> dict:
    """Group transactions by day-of-week and hour."""
    heatmap: dict[str, int] = {}
    day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

    for sig in sigs:
        ts = sig.get("blockTime")
        if not ts:
            continue
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        day = day_names[dt.weekday()]
        hour = dt.hour
        key = f"{day}_{hour}"
        heatmap[key] = heatmap.get(key, 0) + 1

    return heatmap


def _build_net_worth_timeline_helius(txns: list, wallet: str, current_sol_balance: float = 0.0) -> list:
    """Build net worth timeline from Helius enhanced transactions.
    
    Strategy: Work BACKWARDS from the current known SOL balance.
    For each transaction (newest→oldest), reverse its effect on balance
    to reconstruct historical balances. This is accurate regardless of
    whether we have complete history — the recent end is always correct.
    
    Returns same shape as _build_net_worth_timeline for chart compatibility:
    [{month, estimated_sol, tx_count, sol_price_usd, estimated_usd}, ...]
    """
    monthly_tx_count: dict[str, int] = defaultdict(int)
    
    # Count txns per month
    for tx in txns:
        ts = tx.get("timestamp", 0)
        if ts:
            month = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m")
            monthly_tx_count[month] += 1
    
    if not monthly_tx_count:
        return []
    
    # Sort newest first for backward reconstruction
    sorted_txns = sorted(txns, key=lambda t: t.get("timestamp", 0), reverse=True)
    
    # Walk backwards: start at current balance and undo each transaction
    running = current_sol_balance
    # Store balance snapshots keyed by (year, month) — use the balance BEFORE
    # the first transaction of each month as the end-of-previous-month balance
    month_end_balances: dict[str, float] = {}
    
    current_month = datetime.now(tz=timezone.utc).strftime("%Y-%m")
    month_end_balances[current_month] = running
    
    prev_month = current_month
    for tx in sorted_txns:
        ts = tx.get("timestamp", 0)
        if not ts:
            continue
        tx_month = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m")
        
        # If we've moved to an earlier month, snapshot before undoing this tx
        if tx_month != prev_month:
            # The balance right now (before undoing this tx) is the end-of-prev_month
            # Actually: running currently = balance after all txns in prev_month are undone
            # Save end-of-tx_month balance (= balance just before we start undoing tx_month txns)
            if prev_month not in month_end_balances:
                month_end_balances[prev_month] = running
            prev_month = tx_month
        
        # Undo this transaction: reverse SOL flows
        for nt in tx.get("nativeTransfers", []):
            amount_sol = nt.get("amount", 0) / 1e9
            if nt.get("toUserAccount") == wallet:
                running -= amount_sol  # undo: we received, so subtract
            elif nt.get("fromUserAccount") == wallet:
                running += amount_sol  # undo: we sent, so add back
        
        # Undo wrapped SOL transfers
        for tt in tx.get("tokenTransfers", []):
            if tt.get("mint") == SOL_MINT:
                amount_sol = tt.get("tokenAmount", 0)
                if isinstance(amount_sol, (int, float)):
                    if tt.get("toUserAccount") == wallet:
                        running -= amount_sol
                    elif tt.get("fromUserAccount") == wallet:
                        running += amount_sol
        
        # Undo fee (add it back since it was subtracted)
        fee_lamports = tx.get("fee", 0)
        if fee_lamports and tx.get("feePayer") == wallet:
            running += fee_lamports / 1e9
        
        # Save balance for this month (updated as we process more txns in this month)
        month_end_balances[tx_month] = running
    
    # Build continuous timeline
    all_months_sorted = sorted(monthly_tx_count.keys())
    now = datetime.now(tz=timezone.utc)
    last_month = f"{now.year:04d}-{now.month:02d}"
    
    first = all_months_sorted[0]
    filled_months = []
    y, m = int(first[:4]), int(first[5:7])
    ly, lm = int(last_month[:4]), int(last_month[5:7])
    while (y, m) <= (ly, lm):
        filled_months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    
    # Forward-fill from known snapshots
    timeline = []
    last_known = 0.0
    for month_key in filled_months:
        if month_key in month_end_balances:
            last_known = month_end_balances[month_key]
        sol_price = SOL_PRICE_HISTORY.get(month_key, 0)
        timeline.append({
            "month": month_key,
            "estimated_sol": round(max(last_known, 0), 4),
            "tx_count": monthly_tx_count.get(month_key, 0),
            "sol_price_usd": sol_price,
            "estimated_usd": round(max(last_known, 0) * sol_price, 2),
        })
    
    return timeline


def _build_protocol_stats_helius(txns: list) -> list:
    """Build protocol stats from Helius enhanced transactions.
    
    Uses three layers of detection:
    1. Helius `source` field (covers major protocols)
    2. Instruction-level program ID matching against comprehensive registry
    3. Inner instruction program IDs (catches protocols invoked via CPI)
    """
    from backend.roaster.program_registry import (
        PROGRAM_ID_TO_NAME, HELIUS_SOURCE_MAP, INFRA_PROGRAMS,
    )
    
    protocol_counts: dict[str, int] = defaultdict(int)
    
    for tx in txns:
        source = tx.get("source", "UNKNOWN")
        seen_in_tx: set[str] = set()
        
        # Layer 1: Helius source field
        name = HELIUS_SOURCE_MAP.get(source, "")
        if name and name not in INFRA_PROGRAMS:
            seen_in_tx.add(name)
        elif source not in ("SYSTEM_PROGRAM", "UNKNOWN", "", "W_SOL"):
            readable = source.replace("_", " ").title()
            if readable not in INFRA_PROGRAMS:
                seen_in_tx.add(readable)
        
        # Layer 2: Instruction-level program ID matching
        for inst in tx.get("instructions", []):
            pid = inst.get("programId", "")
            prog_name = PROGRAM_ID_TO_NAME.get(pid) or KNOWN_PROGRAMS.get(pid)
            if prog_name and prog_name not in INFRA_PROGRAMS:
                seen_in_tx.add(prog_name)
            
            # Layer 3: Inner instructions (CPI calls)
            for inner in inst.get("innerInstructions", []):
                inner_pid = inner.get("programId", "")
                inner_name = PROGRAM_ID_TO_NAME.get(inner_pid) or KNOWN_PROGRAMS.get(inner_pid)
                if inner_name and inner_name not in INFRA_PROGRAMS:
                    seen_in_tx.add(inner_name)
        
        # Also check top-level accountData for program interactions
        for acc in tx.get("accountData", []):
            pid = acc.get("account", "")
            prog_name = PROGRAM_ID_TO_NAME.get(pid)
            if prog_name and prog_name not in INFRA_PROGRAMS:
                seen_in_tx.add(prog_name)
        
        for n in seen_in_tx:
            protocol_counts[n] += 1
    
    if not protocol_counts:
        return []
    
    total = sum(protocol_counts.values())
    return [
        {"name": n, "tx_count": c, "pct": round(c / total * 100, 1) if total > 0 else 0}
        for n, c in sorted(protocol_counts.items(), key=lambda x: -x[1])
    ][:25]


def _extract_swaps_from_helius(txns: list, wallet: str) -> list:
    """Extract swap-like records from Helius enhanced txns for loss/PnL charts."""
    swaps = []
    for tx in txns:
        if tx.get("type") != "SWAP":
            continue
        ts = tx.get("timestamp", 0)
        sol_in = 0.0
        sol_out = 0.0
        token_in_symbol = None
        token_out_symbol = None
        
        for transfer in tx.get("tokenTransfers", []):
            mint = transfer.get("mint", "")
            amount = transfer.get("tokenAmount", 0)
            from_acc = transfer.get("fromUserAccount", "")
            to_acc = transfer.get("toUserAccount", "")
            
            if mint == SOL_MINT or mint == "":
                if from_acc == wallet:
                    sol_out += amount
                elif to_acc == wallet:
                    sol_in += amount
            else:
                if from_acc == wallet:
                    token_in_symbol = mint[:8] + "..."
                elif to_acc == wallet:
                    token_out_symbol = mint[:8] + "..."
        
        # Also check native transfers for SOL
        for nt in tx.get("nativeTransfers", []):
            amount_sol = abs(nt.get("amount", 0)) / 1e9
            if nt.get("fromUserAccount") == wallet:
                sol_out += amount_sol
            elif nt.get("toUserAccount") == wallet:
                sol_in += amount_sol
        
        sol_change = sol_in - sol_out
        token_in = {"mint": "", "symbol": "SOL", "amount": sol_out} if sol_out > 0.001 else None
        token_out_rec = {"mint": "", "symbol": "SOL", "amount": sol_in} if sol_in > 0.001 else None
        
        # If SOL went out and a token came in → buying token with SOL
        if sol_out > 0.001 and token_out_symbol:
            token_in = {"mint": "", "symbol": "SOL", "amount": sol_out}
            token_out_rec = {"mint": "", "symbol": token_out_symbol, "amount": 0}
        # If SOL came in and a token went out → selling token for SOL
        elif sol_in > 0.001 and token_in_symbol:
            token_in = {"mint": "", "symbol": token_in_symbol, "amount": 0}
            token_out_rec = {"mint": "", "symbol": "SOL", "amount": sol_in}
        
        if token_in or token_out_rec:
            swaps.append({
                "timestamp": ts,
                "token_in": token_in,
                "token_out": token_out_rec,
                "sol_change": round(sol_change, 6),
            })
    
    return swaps


def _build_activity_heatmap_helius(txns: list) -> dict:
    """Build activity heatmap from Helius transaction timestamps."""
    heatmap: dict[str, int] = {}
    day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    
    for tx in txns:
        ts = tx.get("timestamp")
        if not ts:
            continue
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        day = day_names[dt.weekday()]
        hour = dt.hour
        key = f"{day}_{hour}"
        heatmap[key] = heatmap.get(key, 0) + 1
    
    return heatmap


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

        # Try Helius enhanced history first (full parsed history in one call)
        helius_txns = []
        helius_analysis = None
        if HELIUS_API_KEY:
            try:
                helius_start = time.time()
                helius_txns = await asyncio.wait_for(
                    _get_helius_history(client, wallet), timeout=120
                )
                helius_elapsed = time.time() - helius_start
                if helius_txns:
                    helius_analysis = _analyze_helius_txns(helius_txns)
                    logger.info("Helius: fetched %d txns in %.1fs, %d swaps", len(helius_txns), helius_elapsed, helius_analysis["swap_count"])
                else:
                    logger.debug("Helius: 0 txns returned in %.1fs", helius_elapsed)
            except Exception as e:
                logger.warning("Helius failed, falling back to RPC: %s", e)

        # Fallback: sample transactions from RPC
        txn_analysis = {"programs_used": {}, "swap_count": 0, "nft_activity": 0}
        swap_analysis = {
            "total_swaps_detected": 0, "estimated_pnl_sol": 0,
            "biggest_loss": None, "biggest_win": None,
            "win_rate": 0, "total_sol_volume": 0,
        }
        sampled_txns = []
        if helius_analysis:
            # Use Helius data
            txn_analysis = {
                "programs_used": helius_analysis.get("programs", {}),
                "swap_count": helius_analysis.get("swap_count", 0),
                "nft_activity": helius_analysis.get("nft_count", 0),
            }
            swap_analysis = {
                "total_swaps_detected": helius_analysis.get("total_swaps_detected", 0),
                "estimated_pnl_sol": helius_analysis.get("estimated_pnl_sol", 0),
                "biggest_loss": helius_analysis.get("biggest_loss"),
                "biggest_win": helius_analysis.get("biggest_win"),
                "win_rate": helius_analysis.get("win_rate", 0),
                "total_sol_volume": helius_analysis.get("total_sol_volume", 0),
            }
            # Also update signature count if Helius gave us more
            if len(helius_txns) > len(signatures):
                sig_analysis["total"] = len(helius_txns)
                # Recalculate first timestamp from Helius
                timestamps = [t.get("timestamp", 0) for t in helius_txns if t.get("timestamp")]
                if timestamps:
                    earliest = min(timestamps)
                    if sig_analysis["first_ts"] is None or earliest < sig_analysis["first_ts"]:
                        sig_analysis["first_ts"] = earliest
        elif signatures:
            try:
                sampled_txns = await _get_sampled_transactions(client, signatures, wallet, max_calls=30)
                txn_analysis = _analyze_recent_txns(sampled_txns)
            except Exception:
                pass

            # Extract swaps from parsed transactions
            try:
                all_swaps = []
                for tx in sampled_txns:
                    swaps = _extract_swaps_from_tx(tx, wallet, token_list)
                    all_swaps.extend(swaps)
                swap_analysis = _analyze_swaps(all_swaps)
            except Exception:
                pass

        # Timeline analysis (uses all signatures for broad coverage)
        timeline = _analyze_timeline(signatures)

        # Token graveyard
        graveyard = _analyze_graveyard(token_accounts, token_list)

        # Analytics: net worth timeline, protocol stats, loss breakdown, heatmap
        all_swaps = []
        if helius_txns:
            # Extract swap-like records from Helius data for loss charts
            all_swaps = _extract_swaps_from_helius(helius_txns, wallet)
        elif sampled_txns:
            try:
                for tx in sampled_txns:
                    swaps = _extract_swaps_from_tx(tx, wallet, token_list)
                    all_swaps.extend(swaps)
            except Exception:
                pass

        # Build chart data — use Helius-enriched data when available
        if helius_txns:
            net_worth_timeline = _build_net_worth_timeline_helius(helius_txns, wallet, current_sol_balance=sol_balance)
            protocol_stats = _build_protocol_stats_helius(helius_txns)
            # Build activity heatmap from Helius timestamps (more complete than RPC sigs)
            activity_heatmap = _build_activity_heatmap_helius(helius_txns)
        else:
            net_worth_timeline = _build_net_worth_timeline(signatures, sampled_txns, wallet)
            protocol_stats = _build_protocol_stats(sampled_txns)
            activity_heatmap = _build_activity_heatmap(signatures)
        loss_by_token = _build_loss_by_token(all_swaps)
        loss_by_period = _build_loss_by_period(all_swaps)

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
            # PnL & Trading
            "estimated_pnl_sol": swap_analysis.get("estimated_pnl_sol", 0),
            "biggest_loss": swap_analysis.get("biggest_loss"),
            "biggest_win": swap_analysis.get("biggest_win"),
            "total_swaps_detected": swap_analysis.get("total_swaps_detected", 0),
            "win_rate": swap_analysis.get("win_rate", 0),
            "total_sol_volume": swap_analysis.get("total_sol_volume", 0),
            # Timeline
            "active_periods": timeline.get("active_periods", []),
            "peak_activity_period": timeline.get("peak_activity_period"),
            "inactive_gaps": timeline.get("inactive_gaps", []),
            "joined_during": timeline.get("joined_during"),
            # Token Graveyard
            "graveyard_tokens": graveyard.get("graveyard_tokens", 0),
            "graveyard_names": graveyard.get("graveyard_names", []),
            # Charts data
            "net_worth_timeline": net_worth_timeline,
            "protocol_stats": protocol_stats,
            "loss_by_token": loss_by_token,
            "loss_by_period": loss_by_period,
            "activity_heatmap": activity_heatmap,
            "monthly_activity": timeline.get("active_periods", []),
        }
