"""Generate shareable roast card images using Pillow."""

import io
import os
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
    # Fallback to system font
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
    """Draw a dark purple-to-black gradient."""
    draw = ImageDraw.Draw(img)
    for y in range(CARD_H):
        ratio = y / CARD_H
        r = int(30 * (1 - ratio) + 5 * ratio)
        g = int(10 * (1 - ratio) + 5 * ratio)
        b = int(60 * (1 - ratio) + 15 * ratio)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b))


def _draw_score_bar(draw: ImageDraw.Draw, x: int, y: int, w: int, h: int, score: int):
    """Draw a degen score progress bar."""
    # Background
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=(40, 20, 60))
    # Fill
    fill_w = int(w * min(score, 100) / 100)
    if fill_w > 0:
        # Color: green->yellow->red based on score
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

    # Header
    header_font = _font(bold=True, size=28)
    draw.text((40, 25), "🔥 SOLANA ROAST BOT", fill=(255, 120, 50), font=header_font)

    # Wallet address
    wallet_font = _font(False, 18)
    draw.text((40, 65), _truncate_wallet(wallet), fill=(150, 140, 170), font=wallet_font)

    # Title
    title_font = _font(bold=True, size=44)
    title = roast.get("title", "Anon Degen")
    draw.text((40, 100), f'"{title}"', fill=(255, 255, 255), font=title_font)

    # Roast lines
    line_font = _font(False, 22)
    y_pos = 170
    for i, line in enumerate(roast.get("roast_lines", [])[:3]):
        wrapped = textwrap.fill(line, width=70)
        for wl in wrapped.split("\n"):
            draw.text((50, y_pos), f"• {wl}" if wl == wrapped.split("\n")[0] else f"  {wl}",
                      fill=(220, 210, 240), font=line_font)
            y_pos += 30
        y_pos += 10

    # Degen score
    score = roast.get("degen_score", 0)
    score_y = max(y_pos + 20, 440)
    score_font = _font(bold=True, size=28)
    draw.text((40, score_y), f"DEGEN SCORE: {score}/100", fill=(255, 255, 255), font=score_font)
    _draw_score_bar(draw, 40, score_y + 40, 500, 20, score)

    # Score explanation
    expl_font = _font(False, 16)
    expl = roast.get("score_explanation", "")
    if expl:
        draw.text((40, score_y + 70), textwrap.shorten(expl, width=80), fill=(150, 140, 170), font=expl_font)

    # Watermark
    wm_font = _font(False, 16)
    draw.text((CARD_W - 200, CARD_H - 35), "solana-roast.bot", fill=(100, 90, 120), font=wm_font)

    # Accent line at top
    draw.rectangle([0, 0, CARD_W, 4], fill=(255, 120, 50))

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
