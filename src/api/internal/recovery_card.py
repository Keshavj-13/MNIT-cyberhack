"""
Recovery Card — Tier 4 Identity Confirmation
Each customer gets a unique 6×6 grid card at enrollment.
Columns A-F, Rows 1-6. Each cell = random digit 0-9.

Tier 4 challenge: system picks 2 random positions; customer must read
the digits off their physical/PNG card to confirm identity.
"""
import secrets, base64, io
from typing import Tuple, List, Dict

COLS = list("ABCDEF")
ROWS = list("123456")

def generate_card() -> Dict[str, int]:
    """Return {A1:7, A2:3, ..., F6:1} — unique per customer."""
    return {f"{c}{r}": secrets.randbelow(10) for c in COLS for r in ROWS}

def make_challenge(n: int = 2) -> List[str]:
    """Pick n random positions to challenge, e.g. ['B3', 'D5']."""
    positions = [f"{c}{r}" for c in COLS for r in ROWS]
    return sorted(secrets.SystemRandom().sample(positions, k=n))

def render_card_png(card: Dict[str, int], username: str) -> bytes:
    """Render the recovery card as a PNG. Returns raw bytes."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        use_pil = True
    except ImportError:
        use_pil = False

    CELL = 60
    HEADER = 90
    PAD = 20
    W = PAD + len(COLS) * CELL + PAD
    H = HEADER + len(ROWS) * CELL + PAD

    if use_pil:
        # Light banking card on white — matches the white customer portal.
        img = Image.new("RGB", (W, H), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        try:
            font_lg = ImageFont.truetype("arial.ttf", 20)
            font_sm = ImageFont.truetype("arial.ttf", 13)
            font_hdr = ImageFont.truetype("arial.ttf", 22)
        except Exception:
            font_lg = ImageFont.load_default()
            font_sm = font_lg
            font_hdr = font_lg

        # Navy header band (brand) with white text
        draw.rectangle([0, 0, W, HEADER - 10], fill=(0, 56, 147))
        draw.text((PAD, 10), "CENTRAL BANK OF INDIA", font=font_hdr, fill=(255, 255, 255))
        draw.text((PAD, 40), "Account Recovery Card", font=font_sm, fill=(205, 222, 255))
        draw.text((PAD, 60), f"Card Holder: {username}", font=font_sm, fill=(205, 222, 255))

        # Column headers A-F (navy)
        for ci, col in enumerate(COLS):
            x = PAD + ci * CELL + CELL // 2
            draw.text((x - 5, HEADER), col, font=font_sm, fill=(0, 56, 147))

        # Row headers and cells (white / light-gray alternating, dark digits)
        for ri, row in enumerate(ROWS):
            y = HEADER + 20 + ri * CELL
            draw.text((4, y + 18), row, font=font_sm, fill=(0, 56, 147))
            for ci, col in enumerate(COLS):
                x = PAD + ci * CELL
                bg = (245, 247, 250) if (ri + ci) % 2 == 0 else (255, 255, 255)
                draw.rectangle([x + 2, y + 2, x + CELL - 2, y + CELL - 2], fill=bg, outline=(210, 216, 225))
                digit = str(card[f"{col}{row}"])
                draw.text((x + CELL // 2 - 7, y + 13), digit, font=font_lg, fill=(15, 23, 42))

        draw.text((PAD, H - 20), "Keep this card safe. Do not share.", font=font_sm, fill=(120, 130, 150))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    else:
        # SVG fallback when Pillow isn't available
        svg = _render_svg(card, username, W, H, CELL, HEADER, PAD)
        return svg.encode()

def _render_svg(card, username, W, H, CELL, HEADER, PAD):
    rows_svg = ""
    for ci, col in enumerate(COLS):
        x = PAD + ci * CELL + CELL // 2 - 5
        rows_svg += f'<text x="{x}" y="{HEADER}" fill="#003893" font-size="13" font-weight="bold">{col}</text>\n'
    for ri, row in enumerate(ROWS):
        y = HEADER + 20 + ri * CELL
        rows_svg += f'<text x="4" y="{y + 22}" fill="#003893" font-size="13" font-weight="bold">{row}</text>\n'
        for ci, col in enumerate(COLS):
            x = PAD + ci * CELL
            bg = "#f5f7fa" if (ri + ci) % 2 == 0 else "#ffffff"
            digit = card[f"{col}{row}"]
            rows_svg += f'<rect x="{x+2}" y="{y+2}" width="{CELL-4}" height="{CELL-4}" fill="{bg}" stroke="#d2d8e1" rx="4"/>\n'
            rows_svg += f'<text x="{x+CELL//2-6}" y="{y+27}" fill="#0f172a" font-size="20" font-weight="bold">{digit}</text>\n'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">
<rect width="{W}" height="{H}" fill="#ffffff"/>
<rect width="{W}" height="{HEADER-10}" fill="#003893"/>
<text x="{PAD}" y="28" fill="white" font-size="20" font-weight="bold">CENTRAL BANK OF INDIA</text>
<text x="{PAD}" y="52" fill="#cddeff" font-size="13">Account Recovery Card</text>
<text x="{PAD}" y="72" fill="#cddeff" font-size="13">Card Holder: {username}</text>
{rows_svg}
<text x="{PAD}" y="{H-6}" fill="#78829a" font-size="11">Keep this card safe. Do not share.</text>
</svg>'''
