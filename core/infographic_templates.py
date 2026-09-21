"""Render branded infographic templates to PNG using Pillow.

Pure Python, no browser or system dependencies required (unlike an HTML+headless-Chromium
approach), which matters for a local personal tool that should run anywhere Python runs.
"""

import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "generated"

WIDTH = HEIGHT = 1080
PADDING = 90

BG_COLOR = "#0f1f2e"
ACCENT_COLOR = "#6fd6c4"
TEXT_COLOR = "#f4f6f8"
SECONDARY_TEXT_COLOR = "#cfd8dd"
BODY_TEXT_COLOR = "#dfe6e9"
BEFORE_COLOR = "#ff8a7a"
CARD_BG = (255, 255, 255, 13)

FONT_DIR_CANDIDATES = [
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/dejavu"),
    Path("C:/Windows/Fonts"),
]

TEMPLATE_FIELDS = {
    "stat_callout": ["eyebrow", "stat", "label", "footer"],
    "before_after": ["eyebrow", "title", "before", "after"],
    "checklist": ["eyebrow", "title", "items"],
    "quote_card": ["quote", "attribution"],
}


def _font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    filename = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for d in FONT_DIR_CANDIDATES:
        p = d / filename
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size=size)


def _fit_font_size(draw, text, bold, max_width, max_size, min_size=36):
    size = max_size
    while size > min_size:
        font = _font(bold, size)
        if draw.textlength(text, font=font) <= max_width:
            return font
        size -= 6
    return _font(bold, min_size)


def _wrap(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _new_canvas():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    return img, ImageDraw.Draw(img)


def _draw_eyebrow_and_bar(draw, eyebrow: str, y: int = PADDING) -> int:
    font = _font(True, 22)
    draw.text((PADDING, y), eyebrow.upper(), font=font, fill=ACCENT_COLOR)
    bar_y = y + 42
    draw.rectangle([PADDING, bar_y, PADDING + 80, bar_y + 6], fill=ACCENT_COLOR)
    return bar_y + 6 + 44


def _draw_card(img, x, y, w, h, radius=24):
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rounded_rectangle([0, 0, w, h], radius=radius, fill=CARD_BG)
    img.paste(overlay, (x, y), overlay)


def _render_stat_callout(fields: dict) -> Image.Image:
    img, draw = _new_canvas()
    eyebrow_bottom = _draw_eyebrow_and_bar(draw, fields["eyebrow"])

    max_stat_width = WIDTH - 2 * PADDING
    stat_font = _fit_font_size(draw, fields["stat"], True, max_stat_width, max_size=190)
    stat_height = draw.textbbox((0, 0), fields["stat"], font=stat_font)[3]

    label_font = _font(False, 38)
    label_lines = _wrap(draw, fields["label"], label_font, WIDTH - 2 * PADDING - 150)

    block_height = stat_height + 30 + 50 * len(label_lines)
    footer_top = HEIGHT - PADDING - 30
    available = footer_top - eyebrow_bottom
    y = eyebrow_bottom + max(0, (available - block_height) // 2)

    draw.text((PADDING, y), fields["stat"], font=stat_font, fill="#ffffff")
    y += stat_height + 30

    for line in label_lines:
        draw.text((PADDING, y), line, font=label_font, fill=SECONDARY_TEXT_COLOR)
        y += 50

    footer_font = _font(True, 26)
    draw.text((PADDING, footer_top), fields["footer"], font=footer_font, fill=ACCENT_COLOR)
    return img


def _render_before_after(fields: dict) -> Image.Image:
    img, draw = _new_canvas()
    y = _draw_eyebrow_and_bar(draw, fields["eyebrow"])

    title_font = _font(True, 46)
    for line in _wrap(draw, fields["title"], title_font, WIDTH - 2 * PADDING):
        draw.text((PADDING, y), line, font=title_font, fill=TEXT_COLOR)
        y += 58
    y += 30

    col_w = (WIDTH - 2 * PADDING - 40) // 2
    col_h = HEIGHT - y - PADDING
    _draw_card(img, PADDING, y, col_w, col_h)
    _draw_card(img, PADDING + col_w + 40, y, col_w, col_h)

    header_font = _font(True, 28)
    body_font = _font(False, 26)
    inner_pad = 36

    draw.text((PADDING + inner_pad, y + inner_pad), "BEFORE", font=header_font, fill=BEFORE_COLOR)
    ty = y + inner_pad + 46
    for line in _wrap(draw, fields["before"], body_font, col_w - 2 * inner_pad):
        draw.text((PADDING + inner_pad, ty), line, font=body_font, fill=BODY_TEXT_COLOR)
        ty += 36

    x2 = PADDING + col_w + 40
    draw.text((x2 + inner_pad, y + inner_pad), "AFTER", font=header_font, fill=ACCENT_COLOR)
    ty = y + inner_pad + 46
    for line in _wrap(draw, fields["after"], body_font, col_w - 2 * inner_pad):
        draw.text((x2 + inner_pad, ty), line, font=body_font, fill=BODY_TEXT_COLOR)
        ty += 36

    return img


def _render_checklist(fields: dict) -> Image.Image:
    img, draw = _new_canvas()
    eyebrow_bottom = _draw_eyebrow_and_bar(draw, fields["eyebrow"])

    title_font = _font(True, 50)
    title_lines = _wrap(draw, fields["title"], title_font, WIDTH - 2 * PADDING)

    item_font = _font(False, 32)
    check_font = _font(True, 32)
    item_line_lists = [_wrap(draw, item, item_font, WIDTH - 2 * PADDING - 60) for item in fields["items"]]

    block_height = 62 * len(title_lines) + 30
    block_height += sum(40 * len(lines) + 24 for lines in item_line_lists)

    available = (HEIGHT - PADDING) - eyebrow_bottom
    y = eyebrow_bottom + max(0, (available - block_height) // 2)

    for line in title_lines:
        draw.text((PADDING, y), line, font=title_font, fill=TEXT_COLOR)
        y += 62
    y += 30

    for lines in item_line_lists:
        draw.text((PADDING, y), "\u2713", font=check_font, fill=ACCENT_COLOR)
        for i, line in enumerate(lines):
            draw.text((PADDING + 55, y + i * 40), line, font=item_font, fill=BODY_TEXT_COLOR)
        y += 40 * len(lines) + 24

    return img


def _render_quote_card(fields: dict) -> Image.Image:
    img, draw = _new_canvas()
    bar_y = PADDING
    draw.rectangle([PADDING, bar_y, PADDING + 80, bar_y + 6], fill=ACCENT_COLOR)

    max_width = WIDTH - 2 * PADDING
    quote_text = f"\u201c{fields['quote']}\u201d"
    quote_font = _fit_font_size(draw, quote_text.split("\n")[0], True, max_width, max_size=58, min_size=38)
    lines = _wrap(draw, quote_text, quote_font, max_width)

    line_height = quote_font.size + 18
    total_height = line_height * len(lines)
    y = (HEIGHT - total_height) // 2
    for line in lines:
        draw.text((PADDING, y), line, font=quote_font, fill=TEXT_COLOR)
        y += line_height

    if fields.get("attribution"):
        attr_font = _font(True, 28)
        draw.text((PADDING, y + 30), fields["attribution"], font=attr_font, fill=ACCENT_COLOR)

    return img


_RENDERERS = {
    "stat_callout": _render_stat_callout,
    "before_after": _render_before_after,
    "checklist": _render_checklist,
    "quote_card": _render_quote_card,
}


def render_infographic(template_name: str, fields: dict) -> Path:
    if template_name not in TEMPLATE_FIELDS:
        raise ValueError(f"Unknown infographic template: {template_name}")

    missing = [f for f in TEMPLATE_FIELDS[template_name] if f not in fields]
    if missing:
        raise ValueError(f"Missing fields for {template_name}: {missing}")

    img = _RENDERERS[template_name](fields)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{template_name}_{uuid.uuid4().hex[:8]}.png"
    img.save(out_path)
    return out_path
