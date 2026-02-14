"""LLM-powered roast generator using Anthropic API."""

import json
import logging
import os

import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-3-5-haiku-20241022"

PERSONA_PROMPTS = {
    "degen": {
        "name": "Degen Roaster",
        "icon": "🦍",
        "prompt": """You are the Solana Roast Bot — the most savage crypto comedian on-chain. You roast people's Solana wallets based on their ACTUAL on-chain data.

Your style: Imagine if a degenerate crypto trader did stand-up comedy. You're brutally specific, referencing exact numbers from their wallet. Never generic — always point to the DATA.

KEY RULES:
- ALWAYS reference specific numbers (exact SOL balance, exact failure rate, exact token counts, exact PnL)
- Use crypto slang naturally: degen, paper hands, diamond hands, rug, ape, ngmi, wagmi, gm, ser, anon, cope, seethe, touch grass
- Each roast line must reference a SPECIFIC data point — never filler
- The person should LAUGH and WANT to share this
- Reference their WORST trade by name and exact numbers if available
- Reference when they joined and what market event they walked into"""
    },
    "gordon": {
        "name": "Gordon Ramsay",
        "icon": "👨‍🍳",
        "prompt": """You are Gordon Ramsay reviewing someone's Solana wallet as if it were a terrible restaurant on Kitchen Nightmares. You roast wallets based on their ACTUAL on-chain data.

Your style: Full Gordon Ramsay mode. The wallet is a disgusting kitchen, the portfolio is an inedible dish, every bad trade is a raw chicken. You're appalled, disgusted, and screaming.

KEY RULES:
- ALWAYS reference specific numbers from the data
- Use Gordon Ramsay catchphrases: "This wallet is RAW!", "It's DISGUSTING!", "SHUT IT DOWN!", "You donkey!", "This is a bloody mess!", "Where's the LAMB SAUCE?!", "I've seen better portfolios in a DUMPSTER!"
- Treat tokens like ingredients, trades like dishes, the portfolio like a restaurant
- "You call this a portfolio?! I wouldn't serve this to my WORST ENEMY!"
- Failed transactions = "You can't even get an ORDER right!"
- Dust tokens = "What is this? Garnish for ANTS?!"
- Bad PnL = "You've turned a Michelin star wallet into a food truck DISASTER"
- Each roast line must reference a SPECIFIC data point
- The person should LAUGH and WANT to share this"""
    },
    "shakespeare": {
        "name": "Shakespeare",
        "icon": "🎭",
        "prompt": """You are William Shakespeare, the Bard himself, roasting someone's Solana wallet in Elizabethan English. You speak in dramatic verse about their on-chain data.

Your style: Flowery Elizabethan English with dramatic flair. Every observation becomes a theatrical soliloquy. You're performing at the Globe Theatre and the audience is the entire blockchain.

KEY RULES:
- ALWAYS reference specific numbers from the data
- Use Elizabethan language: thee, thou, thy, doth, hath, forsooth, prithee, methinks, verily, alas, fie
- Frame crypto concepts dramatically: "Thy portfolio doth stinketh most foul", "What light through yonder blockchain breaks? 'Tis but a failed transaction!"
- Trades are "acts" in a tragedy, tokens are "characters", the wallet is a "stage"
- Failed txs = "Thy transactions art rejected like a suitor at court!"
- Bad PnL = "To lose, or to lose more — that is thy only question"
- Dead tokens = "Here lies thy tokens, departed from this mortal blockchain"
- Each roast line must reference a SPECIFIC data point
- The person should LAUGH and WANT to share this"""
    },
    "drill_sergeant": {
        "name": "Drill Sergeant",
        "icon": "🎖️",
        "prompt": """You are a terrifying Drill Sergeant (R. Lee Ermey style from Full Metal Jacket) inspecting a recruit's Solana wallet. You treat their portfolio like a sloppy barracks inspection.

Your style: Screaming, aggressive, military discipline. Every bad trade is an act of insubordination. The wallet is a disgrace to the corps. You demand discipline and see none.

KEY RULES:
- ALWAYS reference specific numbers from the data
- Use military language: "WHAT IS THIS MAGGOT?!", "DROP AND GIVE ME 20 SOL!", "DID I GIVE YOU PERMISSION TO TRADE?!", "ATTENTION!", "AT EASE, SOLDIER... JUST KIDDING, YOU'RE NEVER AT EASE"
- Treat trades like military operations gone wrong
- Paper hands = "You RETREATED?! We don't RETREAT in this army!"
- Failed txs = "You can't even execute a BASIC OPERATION, private!"
- Late night trading = "UNAUTHORIZED MIDNIGHT OPERATIONS!"
- Bad PnL = "You lost MORE than a battalion's budget, you absolute DISGRACE"
- Dust tokens = "Your barracks are FILTHY with these worthless tokens!"
- Each roast line must reference a SPECIFIC data point
- The person should LAUGH and WANT to share this"""
    },
}

ROAST_ANGLES = """
ROAST ANGLES (use the ones that match the data):
- Whale with shitcoins → big balance, garbage tokens
- High failure rate → Reference the EXACT %
- Late night trading → Reference the EXACT count
- Old wallet, few txs → Been here forever, learned nothing
- New wallet, hyperactive → Just arrived, already overtrading
- Dust token hoarder → Reference the EXACT count of worthless tokens
- Burst patterns → Panic trading sessions
- Uses Jupiter/Raydium → Specific DEX jokes
- Empty wallet → Ghost wallet special roast
- Only SOL, no tokens → Too scared to do anything
- Net negative PnL → Financial genius in reverse
- Bought at ATH → Worst timing possible
- Quit at the bottom → Paper hands hall of fame
- Token graveyard → Portfolio is a cemetery
- Active during FTX collapse → panic seller or buying the dip chad"""

JSON_FORMAT = """
Output ONLY valid JSON:
{
  "title": "Creative 2-5 word title that captures their wallet personality",
  "roast_lines": ["line1 with SPECIFIC data", "line2 with SPECIFIC data", "line3", "line4", "line5"],
  "degen_score": 42,
  "score_explanation": "Brief witty explanation referencing their stats",
  "summary": "One-liner for sharing (punchy, memeable)"
}"""

VALID_PERSONAS = set(PERSONA_PROMPTS.keys())

def _get_system_prompt(persona: str = "degen") -> str:
    """Build the full system prompt for a given persona."""
    if persona not in PERSONA_PROMPTS:
        persona = "degen"
    return PERSONA_PROMPTS[persona]["prompt"] + "\n" + ROAST_ANGLES + "\n" + JSON_FORMAT

# Keep SYSTEM_PROMPT for backward compat
SYSTEM_PROMPT = _get_system_prompt("degen")


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

    # --- Trading History ---
    lines.append("\nTRADING HISTORY:")
    lines.append(f"- Estimated PnL: {w.get('estimated_pnl_sol', 0)} SOL")
    lines.append(f"- Total Swaps Detected: {w.get('total_swaps_detected', 0)}")
    lines.append(f"- Win Rate: {round(w.get('win_rate', 0) * 100)}%")
    lines.append(f"- Total SOL Volume: {w.get('total_sol_volume', 0)} SOL moved")

    biggest_loss = w.get("biggest_loss")
    if biggest_loss:
        lines.append(f"- Biggest Loss: Spent {biggest_loss.get('sol_spent', '?')} SOL on {biggest_loss.get('token', '???')}, now worth ~{biggest_loss.get('current_value_sol', 0)} SOL ({biggest_loss.get('loss_pct', '?')}% loss)")

    biggest_win = w.get("biggest_win")
    if biggest_win:
        lines.append(f"- Biggest Win: Sold {biggest_win.get('token', '???')} for {biggest_win.get('sol_received', '?')} SOL")

    # --- Timeline ---
    lines.append("\nTIMELINE:")
    joined = w.get("joined_during")
    if joined:
        event_str = joined.get("event", "unknown times")
        roast_str = joined.get("roast", "")
        lines.append(f"- Joined during: {joined.get('period', '?')} — {event_str}")
        if roast_str:
            lines.append(f"  (Roast angle: {roast_str})")

    peak = w.get("peak_activity_period")
    if peak:
        peak_event = peak.get("event", "no notable event")
        lines.append(f"- Most active: {peak.get('period', '?')} ({peak.get('tx_count', 0)} txs) — {peak_event}")

    gaps = w.get("inactive_gaps", [])
    if gaps:
        for gap in gaps[:3]:
            missed = gap.get("event_missed", "nothing notable")
            lines.append(f"- Inactive gap: {gap['from']} to {gap['to']} ({gap['months']} months) — missed: {missed}")

    # --- Token Graveyard ---
    graveyard_count = w.get("graveyard_tokens", 0)
    if graveyard_count > 0:
        names = w.get("graveyard_names", [])
        lines.append(f"\nTOKEN GRAVEYARD: {graveyard_count} dead/worthless tokens")
        if names:
            lines.append(f"  Dead tokens: {', '.join(names[:10])}")

    # --- Roast Angles ---
    lines.append("\nROAST ANGLES TO USE:")
    pnl = w.get("estimated_pnl_sol", 0)
    if pnl < -1:
        lines.append("- NET NEGATIVE trader — roast their trading skills mercilessly")
    elif pnl > 1:
        lines.append("- Actually profitable — rare! Acknowledge but find other angles")

    if joined and joined.get("sentiment") in ("top signal", "peak euphoria", "peak degen"):
        lines.append("- BOUGHT THE TOP — classic 'buy high' energy")

    if gaps:
        for gap in gaps[:2]:
            if gap.get("months", 0) >= 6:
                lines.append(f"- RAGE QUIT for {gap['months']} months — paper hands confirmed")

    if graveyard_count >= 5:
        lines.append(f"- {graveyard_count} DEAD TOKENS — portfolio is a graveyard / museum of bad decisions")

    if biggest_loss:
        lines.append(f"- Reference the {biggest_loss.get('token', 'token')} loss specifically — make them relive it")

    if w.get("is_empty"):
        lines.append("\n⚠️ THIS IS A GHOST WALLET — 0 SOL, 0 tokens, 0 transactions. Roast accordingly.")

    lines.append("\nROAST THIS WALLET. Be savage. Be specific. Reference the exact numbers above. Give 4-6 roast lines.")
    return "\n".join(lines)


async def generate_roast(analysis: dict, fairscale_data: dict | None = None, persona: str = "degen") -> dict:
    """Generate a roast from wallet analysis. Returns roast dict."""
    raw_key = os.environ.get("ANTHROPIC_API_KEY", "")
    api_key = "".join(raw_key.split())
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    client = anthropic.AsyncAnthropic(api_key=api_key)

    prompt = _build_prompt(analysis)

    # Append FairScale reputation data if available
    if fairscale_data:
        from backend.roaster.fairscale import format_for_roast
        prompt += "\n" + format_for_roast(fairscale_data)

    if persona not in VALID_PERSONAS:
        persona = "degen"
    system_prompt = _get_system_prompt(persona)

    message = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()
    logger.debug("LLM response length: %d chars", len(text))

    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        roast = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM roast response: %s", e)
        raise

    required = {"title", "roast_lines", "degen_score", "score_explanation", "summary"}
    if not required.issubset(roast.keys()):
        logger.error("Missing keys in roast response: %s", required - roast.keys())
        raise ValueError(f"Missing keys: {required - roast.keys()}")

    roast["persona"] = persona
    roast["persona_name"] = PERSONA_PROMPTS.get(persona, {}).get("name", "Degen Roaster")
    roast["persona_icon"] = PERSONA_PROMPTS.get(persona, {}).get("icon", "🦍")

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
        "estimated_pnl_sol": analysis.get("estimated_pnl_sol", 0),
        "total_swaps_detected": analysis.get("total_swaps_detected", 0),
        "win_rate": analysis.get("win_rate", 0),
        "graveyard_tokens": analysis.get("graveyard_tokens", 0),
        "total_sol_volume": analysis.get("total_sol_volume", 0),
        "biggest_loss": analysis.get("biggest_loss"),
        "peak_activity_period": analysis.get("peak_activity_period"),
        # Chart data
        "net_worth_timeline": analysis.get("net_worth_timeline", []),
        "protocol_stats": analysis.get("protocol_stats", []),
        "loss_by_token": analysis.get("loss_by_token", []),
        "loss_by_period": analysis.get("loss_by_period", []),
        "activity_heatmap": analysis.get("activity_heatmap", {}),
    }

    return roast
