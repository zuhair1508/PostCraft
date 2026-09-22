"""Render branded infographic templates to PNG using Pillow.

Pure Python, no browser or system dependencies required (unlike an HTML+headless-Chromium
approach), which matters for a local personal tool that should run anywhere Python runs.

Visual system: light background, navy header treatment, a single teal accent, white
shadowed cards, and small hand-drawn (vector-primitive) icon badges — deliberately close to
a typical "case study" infographic look rather than a plain dark slide.
"""

import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "generated"

WIDTH = HEIGHT = 1080
PADDING = 80

# --- Palette -----------------------------------------------------------------
NAVY = "#132a43"
NAVY_SOFT = "#3a5068"
BG_COLOR = "#eef2f6"
CARD_BG = "#ffffff"
CARD_BORDER = "#e1e7ed"
ACCENT = "#12977e"
ACCENT_SOFT = "#e3f3f0"
BEFORE_COLOR = "#d1483a"
BEFORE_SOFT = "#fbe9e7"
TEXT_DARK = "#16283c"
TEXT_BODY = "#4a5a6a"
TEXT_MUTED = "#7c8a99"
WHITE = "#ffffff"

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


# --- Low-level helpers ---------------------------------------------------------

def _font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    filename = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for d in FONT_DIR_CANDIDATES:
        p = d / filename
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size=size)


def _fit_font_size(draw, text, bold, max_width, max_size, min_size=32):
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


def _new_canvas(bg=BG_COLOR):
    img = Image.new("RGB", (WIDTH, HEIGHT), bg)
    return img, ImageDraw.Draw(img)


def _drop_shadow(img: Image.Image, x, y, w, h, radius=24, blur=18, opacity=30):
    """Paste a soft blurred shadow behind where a card will go, then return the card origin."""
    pad = blur * 2
    shadow = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [pad, pad + 6, pad + w, pad + h + 6], radius=radius, fill=(20, 30, 45, opacity)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    img.paste(shadow, (x - pad, y - pad), shadow)


def _card(img, draw, x, y, w, h, radius=24, fill=CARD_BG, border=CARD_BORDER, shadow=True):
    if shadow:
        _drop_shadow(img, x, y, w, h, radius=radius)
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill, outline=border, width=1)


def _icon_badge(img, cx, cy, r, bg, fg, kind: str):
    """A filled circle with a small vector icon drawn inside it."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg)

    s = r * 0.55  # icon half-extent
    lw = max(3, r // 7)

    if kind == "clock":
        od.ellipse([cx - s, cy - s, cx + s, cy + s], outline=fg, width=lw)
        od.line([cx, cy, cx, cy - s * 0.6], fill=fg, width=lw)
        od.line([cx, cy, cx + s * 0.45, cy + s * 0.2], fill=fg, width=lw)
    elif kind == "check":
        od.line(
            [cx - s, cy + s * 0.05, cx - s * 0.2, cy + s * 0.75, cx + s, cy - s * 0.7],
            fill=fg, width=lw, joint="curve",
        )
    elif kind == "bolt":
        od.polygon(
            [
                (cx + s * 0.15, cy - s), (cx - s * 0.55, cy + s * 0.15), (cx - s * 0.05, cy + s * 0.15),
                (cx - s * 0.15, cy + s), (cx + s * 0.55, cy - s * 0.15), (cx + s * 0.05, cy - s * 0.15),
            ],
            fill=fg,
        )
    elif kind == "shield":
        od.polygon(
            [
                (cx, cy - s), (cx + s * 0.85, cy - s * 0.55), (cx + s * 0.85, cy + s * 0.15),
                (cx, cy + s), (cx - s * 0.85, cy + s * 0.15), (cx - s * 0.85, cy - s * 0.55),
            ],
            outline=fg, width=lw,
        )
        od.line(
            [cx - s * 0.35, cy, cx - s * 0.05, cy + s * 0.35, cx + s * 0.4, cy - s * 0.3],
            fill=fg, width=max(2, lw - 1), joint="curve",
        )
    elif kind == "chart":
        base = cy + s * 0.7
        for i, hh in enumerate((0.5, 1.0, 0.7)):
            bx = cx - s * 0.7 + i * s * 0.7
            od.rectangle([bx, base - s * hh, bx + s * 0.45, base], fill=fg)
    elif kind == "warning":
        od.polygon([(cx, cy - s), (cx + s, cy + s * 0.8), (cx - s, cy + s * 0.8)], outline=fg, width=lw)
        od.line([cx, cy - s * 0.15, cx, cy + s * 0.25], fill=fg, width=lw)
        od.ellipse([cx - lw * 0.6, cy + s * 0.45, cx + lw * 0.6, cy + s * 0.55 + lw], fill=fg)
    elif kind == "spark":
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            od.line([cx, cy, cx + dx * s, cy + dy * s], fill=fg, width=lw)
        for dx, dy in ((-0.7, -0.7), (0.7, -0.7), (-0.7, 0.7), (0.7, 0.7)):
            od.line([cx, cy, cx + dx * s * 0.7, cy + dy * s * 0.7], fill=fg, width=max(2, lw - 1))
    else:  # dot fallback
        od.ellipse([cx - s * 0.35, cy - s * 0.35, cx + s * 0.35, cy + s * 0.35], fill=fg)

    img.paste(overlay, (0, 0), overlay)


def _eyebrow_pill(img, draw, x, y, text: str) -> int:
    """A small rounded pill with the eyebrow label; returns the y just below it."""
    font = _font(True, 24)
    tw = draw.textlength(text.upper(), font=font)
    pad_x, pad_y = 22, 12
    w, h = tw + pad_x * 2, font.size + pad_y * 2
    _card(img, draw, x, y, int(w), int(h), radius=h // 2, fill=ACCENT_SOFT, border=ACCENT_SOFT, shadow=False)
    draw.text((x + pad_x, y + pad_y - 2), text.upper(), font=font, fill=ACCENT)
    return y + int(h)


# --- Templates -----------------------------------------------------------------

def _render_stat_callout(fields: dict) -> Image.Image:
    img, draw = _new_canvas()

    inner = 72
    card_w = WIDTH - 2 * PADDING
    max_stat_width = card_w - 2 * inner

    r = 46
    header_h = 2 * r
    gap_header_stat = 44

    stat_font = _fit_font_size(draw, fields["stat"], True, max_stat_width, max_size=210)
    stat_bbox = draw.textbbox((0, 0), fields["stat"], font=stat_font)
    stat_height = stat_bbox[3] - stat_bbox[1]
    gap_stat_label = 30

    label_font = _font(False, 36)
    label_lines = _wrap(draw, fields["label"], label_font, max_stat_width - 20)
    label_h = 48 * len(label_lines)

    footer_font = _font(True, 30)
    footer_lines = _wrap(draw, fields["footer"], footer_font, max_stat_width)
    footer_h = (footer_font.size + 14) * len(footer_lines)
    gap_label_footer = 56

    content_h = header_h + gap_header_stat + stat_height + gap_stat_label + label_h + gap_label_footer + footer_h
    card_h = content_h + 2 * inner
    card_x = PADDING
    card_y = max(PADDING, (HEIGHT - card_h) // 2)
    _card(img, draw, card_x, card_y, card_w, card_h, radius=32)

    x = card_x + inner
    y = card_y + inner

    _icon_badge(img, x + r, y + r, r, ACCENT_SOFT, ACCENT, "chart")
    _eyebrow_pill(img, draw, x + 2 * r + 24, y + r - 24, fields["eyebrow"])
    y += header_h + gap_header_stat

    draw.text((x, y), fields["stat"], font=stat_font, fill=ACCENT)
    y += stat_height + gap_stat_label

    for line in label_lines:
        draw.text((x, y), line, font=label_font, fill=TEXT_BODY)
        y += 48
    y += gap_label_footer - 24

    draw.line([x, y, card_x + card_w - inner, y], fill=CARD_BORDER, width=2)
    y += 24
    for line in footer_lines:
        draw.text((x, y), line, font=footer_font, fill=TEXT_DARK)
        y += footer_font.size + 14

    return img


def _render_before_after(fields: dict) -> Image.Image:
    img, draw = _new_canvas()

    x = PADDING
    y = PADDING
    _eyebrow_pill(img, draw, x, y, fields["eyebrow"])
    y += 70

    title_font = _font(True, 50)
    title_lines = _wrap(draw, fields["title"], title_font, WIDTH - 2 * PADDING)
    for line in title_lines:
        draw.text((x, y), line, font=title_font, fill=TEXT_DARK)
        y += 60
    header_bottom = y + 20

    gap = 32
    col_w = (WIDTH - 2 * PADDING - gap) // 2
    inner_pad = 40
    r = 34
    header_font = _font(True, 30)
    body_font = _font(False, 28)

    columns = [
        (x, BEFORE_COLOR, BEFORE_SOFT, "warning", "BEFORE", fields["before"]),
        (x + col_w + gap, ACCENT, ACCENT_SOFT, "check", "AFTER", fields["after"]),
    ]
    body_lines = [_wrap(draw, body, body_font, col_w - 2 * inner_pad) for *_, body in columns]
    body_h = max(40 * len(lines) for lines in body_lines)
    col_h = inner_pad + 2 * r + 40 + body_h + inner_pad

    available = (HEIGHT - PADDING) - header_bottom
    col_y = header_bottom + max(0, (available - col_h) // 2)

    for (col_x, color, soft, icon, label, _body), lines in zip(columns, body_lines):
        _card(img, draw, col_x, col_y, col_w, col_h, radius=26)
        draw.rectangle([col_x, col_y, col_x + col_w, col_y + 8], fill=color)

        icon_cy = col_y + inner_pad + r
        _icon_badge(img, col_x + inner_pad + r, icon_cy, r, soft, color, icon)
        draw.text(
            (col_x + inner_pad + 2 * r + 20, icon_cy - header_font.size // 2 - 2),
            label, font=header_font, fill=color,
        )

        ty = icon_cy + r + 40
        for line in lines:
            draw.text((col_x + inner_pad, ty), line, font=body_font, fill=TEXT_BODY)
            ty += 40

    return img


def _render_checklist(fields: dict) -> Image.Image:
    img, draw = _new_canvas()

    x = PADDING
    y = PADDING
    _eyebrow_pill(img, draw, x, y, fields["eyebrow"])
    y += 70

    title_font = _font(True, 52)
    title_lines = _wrap(draw, fields["title"], title_font, WIDTH - 2 * PADDING)
    for line in title_lines:
        draw.text((x, y), line, font=title_font, fill=TEXT_DARK)
        y += 62
    header_bottom = y + 20

    card_x = x
    card_w = WIDTH - 2 * PADDING
    inner_pad = 48
    item_font = _font(False, 32)
    item_line_lists = [
        _wrap(draw, item, item_font, card_w - 2 * inner_pad - 70) for item in fields["items"]
    ]

    row_gap = 34
    row_heights = [34 * len(lines) + 40 for lines in item_line_lists]
    items_h = sum(row_heights) + row_gap * max(0, len(row_heights) - 1)
    card_h = 2 * inner_pad + items_h

    available = (HEIGHT - PADDING) - header_bottom
    card_y = header_bottom + max(0, (available - card_h) // 2)
    _card(img, draw, card_x, card_y, card_w, card_h, radius=26)

    iy = card_y + inner_pad
    r = 22
    for lines, rh in zip(item_line_lists, row_heights):
        cy = iy + rh // 2 - 4
        _icon_badge(img, card_x + inner_pad + r, cy, r, ACCENT_SOFT, ACCENT, "check")
        ty = iy
        for line in lines:
            draw.text((card_x + inner_pad + 2 * r + 26, ty), line, font=item_font, fill=TEXT_DARK)
            ty += 40
        iy += rh + row_gap

    return img


def _render_quote_card(fields: dict) -> Image.Image:
    img, draw = _new_canvas(bg=NAVY)

    max_width = WIDTH - 2 * PADDING
    quote_text = fields["quote"]
    quote_font = _fit_font_size(draw, quote_text, True, max_width, max_size=64, min_size=36)
    lines = _wrap(draw, quote_text, quote_font, max_width)

    mark_font = _font(True, 150)
    mark_h = 110
    line_height = quote_font.size + 20
    quote_h = line_height * len(lines)
    rule_gap = 44
    attribution = fields.get("attribution", "").strip()
    attr_font = _font(False, 28)
    attr_h = (attr_font.size + 24) if attribution else 24

    content_h = mark_h + quote_h + rule_gap + attr_h
    y = max(PADDING, (HEIGHT - content_h) // 2)

    draw.text((PADDING - 14, y - 34), "\u201c", font=mark_font, fill=ACCENT)
    y += mark_h

    for line in lines:
        draw.text((PADDING, y), line, font=quote_font, fill="#ffffff")
        y += line_height

    draw.line([PADDING, y + rule_gap - 20, PADDING + 70, y + rule_gap - 20], fill=ACCENT, width=5)
    y += rule_gap

    if attribution:
        draw.text((PADDING, y), attribution, font=attr_font, fill="#b9c6d4")

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
