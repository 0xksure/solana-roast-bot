"""LLM-powered roast generator using Anthropic API."""

import json
import os

import anthropic

MODEL = "claude-3-5-haiku-20241022"

SYSTEM_PROMPT = """You are the Solana Roast Bot — a savage but hilarious crypto comedian who roasts people's Solana wallets based on their on-chain activity.

Your job: Generate a BRUTAL but funny roast. Think crypto-bro humor meets stand-up comedy. Be specific — reference their actual data. Not mean-spirited, just devastatingly accurate.

Rules:
- Reference specific numbers from their wallet data
- Use crypto slang naturally (degen, paper hands, diamond hands, rug, ape, ngmi, wagmi, gm, ser)  
- 3-5 roast lines, each a standalone zinger
- A creative title that captures their wallet personality
- A degen score 1-100 (higher = more degen)
- Keep it fun — the person should WANT to share this

Output ONLY valid JSON with this exact structure:
{
  "title": "The Paper-Handed Tourist",
  "roast_lines": ["line1", "line2", "line3"],
  "degen_score": 42,
  "score_explanation": "Brief explanation of the score",
  "summary": "One-liner summary for sharing"
}"""


def _build_prompt(analysis: dict) -> str:
    lines = ["Here's the wallet data to roast:\n"]

    w = analysis
    lines.append(f"**Wallet:** {w['wallet']}")
    lines.append(f"**SOL Balance:** {w['sol_balance']} SOL (${w['sol_usd']})")
    lines.append(f"**Token Holdings:** {w['token_count']} tokens ({w['dust_tokens']} dust tokens, {w['memecoin_count']} known memecoins)")

    if w.get("top_tokens"):
        tokens_str = ", ".join(
            f"{t['symbol']}({t['amount']:.2f})" for t in w["top_tokens"][:5]
        )
        lines.append(f"**Top Tokens:** {tokens_str}")

    if w.get("helius_tokens"):
        ht = ", ".join(f"{t['symbol']}({t['amount']})" for t in w["helius_tokens"][:5])
        lines.append(f"**Token Balances (detailed):** {ht}")

    lines.append(f"**Total Transactions:** {w['transaction_count']}")
    lines.append(f"**Failed Transactions:** {w['failed_transactions']}")

    if w.get("wallet_age_days"):
        lines.append(f"**Wallet Age:** {w['wallet_age_days']} days (since {w.get('first_tx_date', 'unknown')})")

    if w.get("swap_count"):
        lines.append(f"**Swaps:** {w['swap_count']}")
    if w.get("protocols_used"):
        lines.append(f"**Protocols Used:** {', '.join(w['protocols_used'])}")
    if w.get("nft_activity"):
        lines.append(f"**NFT Activity:** {w['nft_activity']} NFT transactions")
    if w.get("tx_types"):
        lines.append(f"**Transaction Types:** {json.dumps(w['tx_types'])}")

    lines.append("\nNow roast this wallet. Be savage. Be specific. Be funny.")
    return "\n".join(lines)


async def generate_roast(analysis: dict) -> dict:
    """Generate a roast from wallet analysis. Returns roast dict."""
    client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    prompt = _build_prompt(analysis)

    message = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()

    # Parse JSON from response
    # Handle potential markdown wrapping
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    roast = json.loads(text)

    # Validate structure
    required = {"title", "roast_lines", "degen_score", "score_explanation", "summary"}
    if not required.issubset(roast.keys()):
        raise ValueError(f"Missing keys: {required - roast.keys()}")

    # Attach wallet stats for the response
    roast["wallet_stats"] = {
        "sol_balance": analysis["sol_balance"],
        "sol_usd": analysis["sol_usd"],
        "token_count": analysis["token_count"],
        "transaction_count": analysis["transaction_count"],
        "failed_transactions": analysis["failed_transactions"],
        "wallet_age_days": analysis.get("wallet_age_days"),
        "swap_count": analysis.get("swap_count", 0),
        "memecoin_count": analysis.get("memecoin_count", 0),
    }

    return roast
