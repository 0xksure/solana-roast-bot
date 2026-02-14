"""Telegram bot for the Solana Roast Bot. Webhook mode — integrate with FastAPI."""

import asyncio
import logging
import os
import re
import time
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.constants import ParseMode, ChatType
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from backend.roaster.roast_engine import generate_roast, PERSONA_PROMPTS
from backend.roaster.wallet_analyzer import analyze_wallet
from backend.roaster import db
from backend.roaster import fairscale

logger = logging.getLogger(__name__)

WALLET_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
WEB_URL = os.environ.get("ROAST_WEB_URL", "https://solanaroast.bot")
BOT_TOKEN = os.environ.get("ROAST_TELEGRAM_BOT_TOKEN", "")
ROAST_TIMEOUT = 30

# Rate limiting: user_id -> list of timestamps
_rate_limits: dict[int, list[float]] = defaultdict(list)
RATE_LIMIT_PER_HOUR = 5


def _check_rate_limit(user_id: int) -> bool:
    now = time.time()
    _rate_limits[user_id] = [t for t in _rate_limits[user_id] if now - t < 3600]
    return len(_rate_limits[user_id]) < RATE_LIMIT_PER_HOUR


def _record_rate_limit(user_id: int):
    _rate_limits[user_id].append(time.time())


def _escape_md(text: str) -> str:
    """Escape MarkdownV2 special characters."""
    special = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))


def _format_roast(roast: dict, wallet: str) -> str:
    """Format roast dict into a Telegram MarkdownV2 message."""
    icon = _escape_md(roast.get("persona_icon", "🦍"))
    persona_name = _escape_md(roast.get("persona_name", "Degen Roaster"))
    title = _escape_md(roast.get("title", "Roasted"))
    score = roast.get("degen_score", 0)
    summary = _escape_md(roast.get("summary", ""))
    score_expl = _escape_md(roast.get("score_explanation", ""))

    lines = [
        f"{icon} *{persona_name}*",
        f"",
        f"🔥 *{title}*",
        f"",
    ]

    for rl in roast.get("roast_lines", []):
        lines.append(f"• {_escape_md(rl)}")

    lines.append("")
    lines.append(f"📊 *Degen Score:* {_escape_md(str(score))}/100")
    lines.append(f"_{score_expl}_")
    lines.append("")
    lines.append(f"💬 _{summary}_")

    # Wallet stats summary
    stats = roast.get("wallet_stats", {})
    if stats:
        lines.append("")
        sol = stats.get("sol_balance", 0)
        tokens = stats.get("token_count", 0)
        txs = stats.get("transaction_count", 0)
        lines.append(f"💰 {_escape_md(str(sol))} SOL \\| 🪙 {_escape_md(str(tokens))} tokens \\| 📝 {_escape_md(str(txs))} txs")

    text = "\n".join(lines)
    # Truncate to Telegram limit
    if len(text) > 4000:
        text = text[:3990] + "\n\\.\\.\\."
    return text


def _roast_keyboard(wallet: str, persona: str = "degen") -> InlineKeyboardMarkup:
    """Build inline keyboard for roast response."""
    buttons = [
        [
            InlineKeyboardButton("🔄 Roast Again", callback_data=f"roast:{wallet}:{persona}"),
            InlineKeyboardButton("🎭 Different Persona", callback_data=f"personas:{wallet}"),
        ],
        [
            InlineKeyboardButton("🌐 View on Web", url=f"{WEB_URL}/?wallet={wallet}"),
            InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={WEB_URL}/{wallet}&text=Check%20out%20this%20wallet%20roast%20🔥"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def _persona_keyboard(wallet: str) -> InlineKeyboardMarkup:
    """Build persona selection keyboard."""
    buttons = []
    for pid, pdata in PERSONA_PROMPTS.items():
        buttons.append([InlineKeyboardButton(
            f"{pdata['icon']} {pdata['name']}",
            callback_data=f"roast:{wallet}:{pid}"
        )])
    return InlineKeyboardMarkup(buttons)


def _save_telegram_roast(chat_id: int, user_id: int, username: str, wallet: str, persona: str):
    """Save telegram roast to DB for analytics."""
    try:
        if db.DATABASE_URL:
            import psycopg2
            conn = psycopg2.connect(db.DATABASE_URL, connect_timeout=5)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO telegram_roasts (chat_id, user_id, username, wallet_address, persona, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (chat_id, user_id, username or "", wallet, persona, time.time())
            )
            conn.commit()
            conn.close()
    except Exception as e:
        logger.warning("Failed to save telegram roast: %s", e)


async def _do_roast(wallet: str, persona: str) -> dict:
    """Generate a roast for the given wallet and persona."""
    analysis = db.get_cached_analysis(wallet)
    if not analysis:
        analysis = await asyncio.wait_for(analyze_wallet(wallet), timeout=ROAST_TIMEOUT)
        db.save_analysis(wallet, analysis)

    fairscale_data = await fairscale.get_fairscore(wallet)
    if fairscale_data:
        db.save_fairscale_score(wallet, fairscale_data)

    roast = await asyncio.wait_for(generate_roast(analysis, fairscale_data=fairscale_data, persona=persona), timeout=ROAST_TIMEOUT)

    score = roast.get("degen_score", 0)
    roast["percentile"] = db.get_percentile(score)
    db.save_roast(wallet, roast)
    return roast


# ── Command Handlers ──

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔥 *Welcome to the Solana Roast Bot\\!* 🔥\n"
        "\n"
        "I roast Solana wallets based on their on\\-chain data\\. "
        "No mercy\\. No filter\\. Just pure, data\\-driven savagery\\.\n"
        "\n"
        "📜 *Commands:*\n"
        "• `/roast <wallet>` — Roast a wallet\n"
        "• `/roast <wallet> <persona>` — Roast with a specific persona\n"
        "• `/personas` — See available roast personas\n"
        "• `/leaderboard` — Top 10 most degen wallets\n"
        "• `/battle <wallet1> <wallet2>` — Wallet vs wallet showdown\n"
        "\n"
        "🎭 *Personas:* degen, gordon, shakespeare, drill\\_sergeant\n"
        "\n"
        "_Drop a wallet address and get roasted\\, ser\\. 💀_"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_personas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["🎭 *Available Personas:*\n"]
    for pid, pdata in PERSONA_PROMPTS.items():
        lines.append(f"• {_escape_md(pdata['icon'])} *{_escape_md(pdata['name'])}* — `{_escape_md(pid)}`")
    lines.append(f"\n_Usage: `/roast <wallet> <persona>`_")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_roast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text(
            "🤡 You forgot the wallet address, ser\\.\n\n"
            "_Usage: `/roast <wallet_address>` or `/roast <wallet_address> <persona>`_",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    wallet = context.args[0].strip()
    persona = context.args[1].strip() if len(context.args) > 1 else "degen"

    if not WALLET_RE.match(wallet):
        await update.message.reply_text("❌ That doesn't look like a valid Solana wallet address\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    if persona not in PERSONA_PROMPTS:
        persona = "degen"

    if not _check_rate_limit(user.id):
        await update.message.reply_text(
            "🌱 Slow down, ser\\! Max 5 roasts per hour\\. Touch some grass and try again later\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # Send "typing" indicator
    await update.message.chat.send_action("typing")

    try:
        roast = await _do_roast(wallet, persona)
    except asyncio.TimeoutError:
        await update.message.reply_text("⏰ Roast timed out — this wallet is too complex even for us\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    except Exception as e:
        logger.error("Telegram roast failed for %s: %s", wallet[:8], e, exc_info=True)
        await update.message.reply_text("💀 Even the blockchain doesn't want to talk about this wallet\\. Try again later\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    _record_rate_limit(user.id)
    _save_telegram_roast(update.effective_chat.id, user.id, user.username, wallet, persona)

    text = _format_roast(roast, wallet)
    keyboard = _roast_keyboard(wallet, persona)

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboard)


async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leaders = db.get_leaderboard(10)
    if not leaders:
        await update.message.reply_text("📊 No roasts yet\\! Be the first to get roasted\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    lines = ["🏆 *Top 10 Degens:*\n"]
    medals = ["🥇", "🥈", "🥉"] + ["🔥"] * 7
    for i, entry in enumerate(leaders):
        w = entry["wallet"]
        short = f"{w[:6]}\\.\\.\\{w[-4:]}"
        score = _escape_md(str(entry.get("degen_score", 0)))
        title = _escape_md(entry.get("title", ""))
        lines.append(f"{medals[i]} {short} — *{score}*/100 _{title}_")

    lines.append(f"\n[View full leaderboard]({_escape_md(WEB_URL)})")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)


async def cmd_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚔️ Need two wallets to battle\\!\n\n_Usage: `/battle <wallet1> <wallet2>`_",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    wallet1 = context.args[0].strip()
    wallet2 = context.args[1].strip()

    if not WALLET_RE.match(wallet1) or not WALLET_RE.match(wallet2):
        await update.message.reply_text("❌ Invalid wallet address\\(es\\)\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    if wallet1 == wallet2:
        await update.message.reply_text("🤡 Can't battle yourself, ser\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    user = update.effective_user
    if not _check_rate_limit(user.id):
        await update.message.reply_text("🌱 Rate limited\\! Try again later\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    await update.message.chat.send_action("typing")

    try:
        roast1, roast2 = await asyncio.gather(
            _do_roast(wallet1, "degen"),
            _do_roast(wallet2, "degen"),
        )
    except Exception as e:
        logger.error("Battle failed: %s", e, exc_info=True)
        await update.message.reply_text("💀 Battle failed\\. These wallets broke our arena\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    _record_rate_limit(user.id)

    s1 = roast1.get("degen_score", 0)
    s2 = roast2.get("degen_score", 0)
    w1_short = f"{wallet1[:6]}...{wallet1[-4:]}"
    w2_short = f"{wallet2[:6]}...{wallet2[-4:]}"

    winner = w1_short if s1 >= s2 else w2_short
    lines = [
        f"⚔️ *WALLET BATTLE* ⚔️\n",
        f"🟥 {_escape_md(w1_short)} — *{s1}*/100",
        f"_{_escape_md(roast1.get('title', ''))}_\n",
        f"🟦 {_escape_md(w2_short)} — *{s2}*/100",
        f"_{_escape_md(roast2.get('title', ''))}_\n",
        f"🏆 *Winner:* {_escape_md(winner)} wins with peak degen energy\\!",
    ]

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("personas:"):
        wallet = data.split(":", 1)[1]
        await query.message.reply_text(
            "🎭 *Pick a persona:*",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_persona_keyboard(wallet),
        )

    elif data.startswith("roast:"):
        parts = data.split(":")
        wallet = parts[1]
        persona = parts[2] if len(parts) > 2 else "degen"

        user = update.effective_user
        if not _check_rate_limit(user.id):
            await query.message.reply_text("🌱 Rate limited\\! Try again later\\.", parse_mode=ParseMode.MARKDOWN_V2)
            return

        await query.message.chat.send_action("typing")

        try:
            roast = await _do_roast(wallet, persona)
        except Exception as e:
            logger.error("Callback roast failed: %s", e, exc_info=True)
            await query.message.reply_text("💀 Roast failed\\. Try again\\.", parse_mode=ParseMode.MARKDOWN_V2)
            return

        _record_rate_limit(user.id)
        _save_telegram_roast(query.message.chat.id, user.id, user.username, wallet, persona)

        text = _format_roast(roast, wallet)
        keyboard = _roast_keyboard(wallet, persona)
        await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboard)


# ── Application Setup ──

_app: Application | None = None


def get_application() -> Application:
    """Get or create the Telegram bot Application (singleton)."""
    global _app
    if _app is not None:
        return _app

    if not BOT_TOKEN:
        raise ValueError("ROAST_TELEGRAM_BOT_TOKEN not set")

    _app = Application.builder().token(BOT_TOKEN).build()
    _app.add_handler(CommandHandler("start", cmd_start))
    _app.add_handler(CommandHandler("help", cmd_start))
    _app.add_handler(CommandHandler("roast", cmd_roast))
    _app.add_handler(CommandHandler("personas", cmd_personas))
    _app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    _app.add_handler(CommandHandler("battle", cmd_battle))
    _app.add_handler(CallbackQueryHandler(callback_handler))

    return _app


async def setup_webhook(webhook_url: str):
    """Set the Telegram webhook URL. Call once on deploy."""
    app = get_application()
    await app.bot.set_webhook(url=webhook_url)
    logger.info("Telegram webhook set to %s", webhook_url)


async def set_bot_commands():
    """Register bot commands with Telegram (shows in menu)."""
    app = get_application()
    commands = [
        BotCommand("roast", "Roast a Solana wallet 🔥"),
        BotCommand("personas", "List roast personas 🎭"),
        BotCommand("leaderboard", "Top 10 degens 🏆"),
        BotCommand("battle", "Wallet vs wallet ⚔️"),
        BotCommand("start", "Welcome message"),
    ]
    await app.bot.set_my_commands(commands)
    logger.info("Bot commands registered")
