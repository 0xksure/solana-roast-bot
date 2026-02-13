"""Generate shareable roast card images using Pillow."""

import io
import math
import os
import random
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CARD_W, CARD_H = 1200, 630
FONTS_DIR = Path(__file__).parent.parent / "static" / "fonts"


def _font(bold: bool = False, size: int = 24) -> ImageFont.FreeTypeFont:
    name = "Inter-Bold.ttf" if bold else "Inter-Regular.ttf"
    path = FONTS_DIR / name
    if path.exists():
        return ImageFont.truetype(str(path), size)
    for fallback in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(fallback):
            return ImageFont.truetype(fallback, size)
    return ImageFont.load_default()


def _truncate_wallet(wallet: str) -> str:
    if len(wallet) > 10:
        return f"{wallet[:4]}...{wallet[-4:]}"
    return wallet


def _draw_gradient(img: Image.Image):
    """Draw a dark purple-to-black gradient with subtle noise."""
    draw = ImageDraw.Draw(img)
    for y in range(CARD_H):
        ratio = y / CARD_H
        r = int(25 * (1 - ratio) + 8 * ratio)
        g = int(8 * (1 - ratio) + 5 * ratio)
        b = int(55 * (1 - ratio) + 20 * ratio)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b))


def _draw_decorative_dots(draw: ImageDraw.Draw):
    """Draw QR-code-style decorative dots in corners."""
    random.seed(42)  # deterministic
    for cx, cy in [(CARD_W - 80, 80), (CARD_W - 80, CARD_H - 80)]:
        for i in range(7):
            for j in range(7):
                if random.random() > 0.45:
                    x = cx + (i - 3) * 12
                    y = cy + (j - 3) * 12
                    draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(60, 30, 90, 180))


def _draw_score_bar(draw: ImageDraw.Draw, x: int, y: int, w: int, h: int, score: int):
    """Draw a degen score progress bar."""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=(40, 20, 60))
    fill_w = int(w * min(score, 100) / 100)
    if fill_w > 0:
        if score < 33:
            color = (50, 205, 50)
        elif score < 66:
            color = (255, 200, 0)
        else:
            color = (255, 60, 60)
        draw.rounded_rectangle([x, y, x + fill_w, y + h], radius=h // 2, fill=color)


def generate_card(roast: dict, wallet: str) -> bytes:
    """Generate a PNG card and return bytes."""
    img = Image.new("RGB", (CARD_W, CARD_H))
    _draw_gradient(img)
    draw = ImageDraw.Draw(img)

    # Decorative dots
    _draw_decorative_dots(draw)

    # Orange gradient accent line at top (thicker)
    for i in range(6):
        alpha = 255 - i * 30
        r_val = min(255, 255 - i * 10)
        draw.line([(0, i), (CARD_W, i)], fill=(r_val, 120 - i * 10, 50 - i * 5))

    # Purple glow effect (subtle)
    for i in range(20):
        opacity = 15 - i
        if opacity > 0:
            draw.ellipse([CARD_W // 2 - 300 - i * 5, -100 - i * 3,
                         CARD_W // 2 + 300 + i * 5, 100 + i * 3],
                        fill=(80 + i, 30, 120 + i))

    # Fire emojis
    fire_font = _font(bold=True, size=40)
    for (fx, fy) in [(CARD_W - 160, 20), (CARD_W - 120, 50), (50, CARD_H - 60)]:
        try:
            draw.text((fx, fy), "🔥", font=fire_font, fill=(255, 120, 50))
        except Exception:
            draw.text((fx, fy), "*", font=fire_font, fill=(255, 120, 50))

    # Header
    header_font = _font(bold=True, size=28)
    draw.text((40, 20), "SOLANA ROAST BOT", fill=(255, 120, 50), font=header_font)

    # Wallet address
    wallet_font = _font(False, 18)
    draw.text((40, 58), _truncate_wallet(wallet), fill=(150, 140, 170), font=wallet_font)

    # Title
    title_font = _font(bold=True, size=40)
    title = roast.get("title", "Anon Degen")
    draw.text((40, 90), f'"{title}"', fill=(255, 255, 255), font=title_font)

    # Roast lines
    line_font = _font(False, 20)
    y_pos = 150
    for i, line in enumerate(roast.get("roast_lines", [])[:3]):
        wrapped = textwrap.fill(line, width=75)
        for j, wl in enumerate(wrapped.split("\n")):
            prefix = "• " if j == 0 else "  "
            draw.text((50, y_pos), f"{prefix}{wl}", fill=(220, 210, 240), font=line_font)
            y_pos += 28
        y_pos += 8

    # Degen score section (bigger and more prominent)
    score = roast.get("degen_score", 0)
    score_y = max(y_pos + 15, 400)

    # Score background panel
    draw.rounded_rectangle([30, score_y - 10, 620, score_y + 75], radius=12, fill=(20, 10, 40))

    score_font = _font(bold=True, size=32)
    draw.text((45, score_y), f"DEGEN SCORE: {score}/100", fill=(255, 255, 255), font=score_font)
    _draw_score_bar(draw, 45, score_y + 42, 550, 24, score)

    # Stats row at bottom
    stats = roast.get("wallet_stats", {})
    stats_y = CARD_H - 55
    stats_font = _font(bold=True, size=16)
    stats_label_font = _font(False, 14)

    stat_items = [
        (f"{stats.get('sol_balance', 0)} SOL", "Balance"),
        (f"{stats.get('token_count', 0)}", "Tokens"),
        (f"{stats.get('wallet_age_days', '?')}d", "Age"),
        (f"{stats.get('transaction_count', 0)}", "TXs"),
        (f"{stats.get('failure_rate', 0)}%", "Fail Rate"),
    ]

    # Stats background
    draw.rounded_rectangle([30, stats_y - 10, CARD_W - 30, CARD_H - 8], radius=8, fill=(15, 8, 30))

    stat_x = 50
    for val, label in stat_items:
        draw.text((stat_x, stats_y), str(val), fill=(255, 200, 100), font=stats_font)
        draw.text((stat_x, stats_y + 20), label, fill=(120, 110, 140), font=stats_label_font)
        stat_x += 200

    # Watermark
    wm_font = _font(False, 14)
    draw.text((CARD_W - 180, stats_y + 5), "solana-roast.bot", fill=(80, 70, 100), font=wm_font)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
