"""Wallet analyzer — fetches on-chain data for a Solana wallet."""

import asyncio
import base64
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

SOLANA_RPC = "https://api.mainnet-beta.solana.com"
JUPITER_PRICE = "https://api.jup.ag/price/v2"
HELIUS_KEY_PATH = Path.home() / ".config" / "helius" / "api_key"

KNOWN_MEMECOINS = {
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": "BONK",
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm": "WIF",
    "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr": "POPCAT",
    "A8C3xuqscfmyLrte3VmTqrAq8kgMASius9AFNANwpump": "FARTCOIN",
}

SOL_MINT = "So11111111111111111111111111111111111111112"


def _helius_key() -> str | None:
    try:
        return HELIUS_KEY_PATH.read_text().strip()
    except FileNotFoundError:
        return os.environ.get("HELIUS_API_KEY")


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
    try:
        r = await client.get(f"{JUPITER_PRICE}?ids={SOL_MINT}", timeout=10)
        data = r.json()
        return float(data["data"][SOL_MINT]["price"])
    except Exception:
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


async def _helius_transactions(client: httpx.AsyncClient, wallet: str, key: str) -> list:
    try:
        r = await client.get(
            f"https://api.helius.xyz/v0/addresses/{wallet}/transactions?api-key={key}&limit=100",
            timeout=20,
        )
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


async def _helius_balances(client: httpx.AsyncClient, wallet: str, key: str) -> dict:
    try:
        r = await client.get(
            f"https://api.helius.xyz/v0/addresses/{wallet}/balances?api-key={key}",
            timeout=15,
        )
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


def _analyze_signatures(sigs: list) -> dict:
    if not sigs:
        return {"total": 0, "failed": 0, "first_ts": None, "last_ts": None}
    failed = sum(1 for s in sigs if s.get("err") is not None)
    timestamps = [s["blockTime"] for s in sigs if s.get("blockTime")]
    return {
        "total": len(sigs),
        "failed": failed,
        "first_ts": min(timestamps) if timestamps else None,
        "last_ts": max(timestamps) if timestamps else None,
    }


def _analyze_tokens(accounts: list) -> list:
    tokens = []
    for acc in accounts:
        info = acc.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
        token_amount = info.get("tokenAmount", {})
        amount = float(token_amount.get("uiAmount") or 0)
        if amount <= 0:
            continue
        mint = info.get("mint", "")
        tokens.append({
            "mint": mint,
            "amount": amount,
            "decimals": token_amount.get("decimals", 0),
            "symbol": KNOWN_MEMECOINS.get(mint, "UNKNOWN"),
            "is_memecoin": mint in KNOWN_MEMECOINS,
        })
    return sorted(tokens, key=lambda t: t["amount"], reverse=True)


def _analyze_helius_txns(txns: list) -> dict:
    swaps = 0
    protocols = set()
    nft_count = 0
    types = {}
    for tx in txns:
        t = tx.get("type", "UNKNOWN")
        types[t] = types.get(t, 0) + 1
        if t in ("SWAP", "TOKEN_SWAP"):
            swaps += 1
            source = tx.get("source", "")
            if source:
                protocols.add(source)
        if t in ("NFT_MINT", "NFT_SALE", "NFT_BID", "COMPRESSED_NFT_MINT"):
            nft_count += 1
    return {
        "swap_count": swaps,
        "protocols": list(protocols),
        "nft_activity": nft_count,
        "tx_types": types,
    }


async def analyze_wallet(wallet: str) -> dict:
    """Main entry point — returns full wallet analysis dict."""
    helius_key = _helius_key()

    async with httpx.AsyncClient() as client:
        # Parallel fetches
        tasks = {
            "balance": _get_sol_balance(client, wallet),
            "sol_price": _get_sol_price(client),
            "signatures": _get_signatures(client, wallet),
            "tokens": _get_token_accounts(client, wallet),
        }
        if helius_key:
            tasks["helius_txns"] = _helius_transactions(client, wallet, helius_key)
            tasks["helius_balances"] = _helius_balances(client, wallet, helius_key)

        keys = list(tasks.keys())
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        data = {}
        for k, v in zip(keys, results):
            data[k] = v if not isinstance(v, Exception) else ([] if k in ("signatures", "tokens", "helius_txns") else ({} if k == "helius_balances" else 0))

        sol_balance = data["balance"]
        sol_price = data["sol_price"]
        sig_analysis = _analyze_signatures(data["signatures"])
        token_list = _analyze_tokens(data["tokens"])

        helius_analysis = {}
        if helius_key and isinstance(data.get("helius_txns"), list):
            helius_analysis = _analyze_helius_txns(data["helius_txns"])

        # Wallet age
        wallet_age_days = None
        if sig_analysis["first_ts"]:
            wallet_age_days = (time.time() - sig_analysis["first_ts"]) / 86400

        # Count dust tokens (< $1 value estimated)
        dust_count = sum(1 for t in token_list if t["amount"] < 1)
        memecoin_count = sum(1 for t in token_list if t["is_memecoin"])

        # Helius balances for better token info
        helius_tokens = []
        if isinstance(data.get("helius_balances"), dict):
            for tok in data["helius_balances"].get("tokens", []):
                helius_tokens.append({
                    "mint": tok.get("mint", ""),
                    "amount": tok.get("amount", 0),
                    "symbol": tok.get("symbol", "UNKNOWN"),
                })

        return {
            "wallet": wallet,
            "sol_balance": round(sol_balance, 4),
            "sol_usd": round(sol_balance * sol_price, 2),
            "sol_price": round(sol_price, 2),
            "token_count": len(token_list),
            "top_tokens": token_list[:10],
            "helius_tokens": helius_tokens[:10] if helius_tokens else [],
            "dust_tokens": dust_count,
            "memecoin_count": memecoin_count,
            "transaction_count": sig_analysis["total"],
            "failed_transactions": sig_analysis["failed"],
            "wallet_age_days": round(wallet_age_days) if wallet_age_days else None,
            "first_tx_date": datetime.fromtimestamp(sig_analysis["first_ts"], tz=timezone.utc).isoformat() if sig_analysis["first_ts"] else None,
            "swap_count": helius_analysis.get("swap_count", 0),
            "protocols_used": helius_analysis.get("protocols", []),
            "nft_activity": helius_analysis.get("nft_activity", 0),
            "tx_types": helius_analysis.get("tx_types", {}),
            "has_helius": helius_key is not None,
        }
