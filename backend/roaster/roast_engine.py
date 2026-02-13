"""LLM-powered roast generator using Anthropic API."""

import json
import os

import anthropic

MODEL = "claude-3-5-haiku-20241022"

SYSTEM_PROMPT = """You are the Solana Roast Bot — the most savage crypto comedian on-chain. You roast people's Solana wallets based on their ACTUAL on-chain data.

Your style: Imagine if a degenerate crypto trader did stand-up comedy. You're brutally specific, referencing exact numbers from their wallet. Never generic — always point to the DATA.

KEY RULES:
- ALWAYS reference specific numbers (exact SOL balance, exact failure rate, exact token counts)
- Use crypto slang naturally: degen, paper hands, diamond hands, rug, ape, ngmi, wagmi, gm, ser, anon, cope, seethe, touch grass
- Each roast line must reference a SPECIFIC data point — never filler
- The person should LAUGH and WANT to share this

ROAST ANGLES (use the ones that match the data):
- Whale with shitcoins → "Has a yacht but fills it with garbage from the dollar store"
- High failure rate → Reference the EXACT % ("X% of your transactions fail — even your blockchain rejects you")
- Late night trading → Reference the EXACT count ("Y transactions between midnight and 5 AM — do you sleep or just cope?")
- Old wallet, few txs → "Been on Solana since the ice age and still haven't figured it out"
- New wallet, hyperactive → "Discovered crypto X days ago and already thinks they're a market maker"
- Dust token hoarder → Reference the EXACT count of worthless tokens
- Many shitcoins with no known symbol → "You collect tokens like a hoarder collects newspapers — none of them are worth anything"
- Burst patterns → "X burst trading sessions detected — nothing says 'calm and rational' like panic-clicking"
- Uses Jupiter/Raydium → Specific DEX jokes
- Empty wallet → Ghost wallet special roast
- Only SOL, no tokens → "You have SOL but you're too scared to do anything with it"

Output ONLY valid JSON:
{
  "title": "Creative 2-5 word title that captures their wallet personality",
  "roast_lines": ["line1 with SPECIFIC data", "line2 with SPECIFIC data", "line3", "line4"],
  "degen_score": 42,
  "score_explanation": "Brief witty explanation referencing their stats",
  "summary": "One-liner for sharing (punchy, memeable)"
}"""


def _build_prompt(analysis: dict) -> str:
    w = analysis
    lines = ["WALLET DATA TO ROAST:\n"]

    lines.append(f"Wallet: {w['wallet']}")
    lines.append(f"SOL Balance: {w['sol_balance']} SOL (${w['sol_usd']})")
    lines.append(f"SOL Price: ${w['sol_price']}")
    lines.append(f"Total Tokens Held: {w['token_count']}")
    lines.append(f"Known/Listed Tokens: {w.get('known_token_count', 0)}")
    lines.append(f"Unknown Shitcoins: {w.get('shitcoin_count', 0)}")
    lines.append(f"Dust Tokens (< 1 unit): {w['dust_tokens']}")

    if w.get("top_tokens"):
        tokens_str = ", ".join(
            f"{t['symbol']}({t['amount']:.2f})" for t in w["top_tokens"][:8]
        )
        lines.append(f"Top Tokens: {tokens_str}")

    lines.append(f"Total Transactions: {w['transaction_count']}")
    lines.append(f"Failed Transactions: {w['failed_transactions']} ({w.get('failure_rate', 0)}% failure rate)")
    lines.append(f"Transactions Per Day (avg): {w.get('txs_per_day', 0)}")
    lines.append(f"Late Night Txs (midnight-5AM UTC): {w.get('late_night_txs', 0)}")
    lines.append(f"Burst Trading Sessions (5+ txs in 5 min): {w.get('burst_count', 0)}")

    if w.get("wallet_age_days"):
        lines.append(f"Wallet Age: {w['wallet_age_days']} days (since {w.get('first_tx_date', 'unknown')})")
    else:
        lines.append("Wallet Age: Unknown (possibly brand new)")

    if w.get("swap_count"):
        lines.append(f"Swaps Detected (recent): {w['swap_count']}")
    if w.get("protocols_used"):
        lines.append(f"Protocols Used: {', '.join(w['protocols_used'])}")
    if w.get("nft_activity"):
        lines.append(f"NFT Activity: {w['nft_activity']} NFT transactions")

    if w.get("is_empty"):
        lines.append("\n⚠️ THIS IS A GHOST WALLET — 0 SOL, 0 tokens, 0 transactions. Roast accordingly.")

    lines.append("\nROAST THIS WALLET. Be savage. Be specific. Reference the exact numbers above.")
    return "\n".join(lines)


async def generate_roast(analysis: dict) -> dict:
    """Generate a roast from wallet analysis. Returns roast dict."""
    raw_key = os.environ.get("ANTHROPIC_API_KEY", "")
    api_key = "".join(raw_key.split())  # DO App Platform injects newlines in long secrets
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    client = anthropic.AsyncAnthropic(api_key=api_key)

    prompt = _build_prompt(analysis)

    message = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()

    # Handle markdown wrapping
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    roast = json.loads(text)

    required = {"title", "roast_lines", "degen_score", "score_explanation", "summary"}
    if not required.issubset(roast.keys()):
        raise ValueError(f"Missing keys: {required - roast.keys()}")

    roast["wallet_stats"] = {
        "sol_balance": analysis["sol_balance"],
        "sol_usd": analysis["sol_usd"],
        "token_count": analysis["token_count"],
        "transaction_count": analysis["transaction_count"],
        "failed_transactions": analysis["failed_transactions"],
        "wallet_age_days": analysis.get("wallet_age_days"),
        "swap_count": analysis.get("swap_count", 0),
        "memecoin_count": analysis.get("known_token_count", 0),
        "shitcoin_count": analysis.get("shitcoin_count", 0),
        "failure_rate": analysis.get("failure_rate", 0),
    }

    return roast
