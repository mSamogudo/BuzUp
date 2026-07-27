#!/usr/bin/env python3
"""Build a premium BusUp 16:9 presentation as PNG slides and a PDF.

The deck is intentionally generated from deterministic image composition rather
than a generative model. Product screens and QR codes stay fixed; only layout,
typography, framing and presentation polish are composed here.
"""

from __future__ import annotations

import base64
import datetime as dt
import io
import math
import os
import textwrap
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
EXPORT = ROOT / "premium_export"
SLIDES_DIR = EXPORT / "slides"
ASSETS = ROOT / "premium_assets"
SHOTS = ROOT / "shots"

W, H = 1920, 1080

NAVY = (5, 21, 40)
NAVY_2 = (8, 37, 66)
BLUE = (45, 140, 240)
BLUE_2 = (126, 200, 255)
INK = (235, 243, 252)
MUTED = (151, 174, 201)
LINE = (50, 103, 156)
WHITE = (255, 255, 255)
PAPER = (246, 249, 253)
BLACK = (7, 10, 16)

FONT_REG = "/System/Library/Fonts/HelveticaNeue.ttc"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_REG_FALLBACK = "/System/Library/Fonts/Supplemental/Arial.ttf"

UP_LIGHT = PROJECT / "frontend/public/assets/up-digital-logo/up_digital_light.png"
UP_DARK = PROJECT / "frontend/public/assets/up-digital-logo/up_digital_dark.png"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REG
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.truetype(FONT_REG_FALLBACK, size)


F = {
    "eyebrow": font(18, True),
    "small": font(20),
    "body": font(28),
    "body_b": font(28, True),
    "body_s": font(24),
    "h3": font(34, True),
    "h2": font(50, True),
    "h1": font(62, True),
    "mega": font(78, True),
    "num": font(68, True),
}


def mkdirs() -> None:
    EXPORT.mkdir(exist_ok=True)
    SLIDES_DIR.mkdir(parents=True, exist_ok=True)


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient_bg() -> Image.Image:
    im = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / (H - 1)
        col = mix(NAVY, (8, 55, 105), t * 0.75)
        d.line((0, y, W, y), fill=col)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((1040, -360, 2260, 760), fill=(45, 140, 240, 64))
    gd.ellipse((-520, 620, 860, 1510), fill=(45, 140, 240, 45))
    gd.ellipse((1240, 660, 2300, 1390), fill=(126, 200, 255, 20))
    glow = glow.filter(ImageFilter.GaussianBlur(72))
    return Image.alpha_composite(im.convert("RGBA"), glow)


def light_bg() -> Image.Image:
    im = Image.new("RGB", (W, H), (247, 250, 254)).convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    d.ellipse((-260, -300, 620, 520), fill=(45, 140, 240, 26))
    d.ellipse((1200, 720, 2250, 1340), fill=(45, 140, 240, 20))
    return Image.alpha_composite(im, glow.filter(ImageFilter.GaussianBlur(90)))


def rounded_mask(size: tuple[int, int], r: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=r, fill=255)
    return mask


def composite_round_rect(
    canvas: Image.Image,
    box: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int] | None = None,
    width: int = 1,
) -> None:
    x, y, w, h = box
    layer = Image.new("RGBA", (w + width * 2, h + width * 2), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle(
        (width, width, w + width - 1, h + width - 1),
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )
    canvas.alpha_composite(layer, (x - width, y - width))


def trim_alpha(im: Image.Image) -> Image.Image:
    im = im.convert("RGBA")
    alpha = im.getchannel("A")
    bbox = alpha.getbbox()
    return im.crop(bbox) if bbox else im


def open_img(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def fit_cover(im: Image.Image, size: tuple[int, int], pos: tuple[float, float] = (0.5, 0.5)) -> Image.Image:
    return ImageOps.fit(im.convert("RGBA"), size, method=Image.Resampling.LANCZOS, centering=pos)


def fit_contain(im: Image.Image, size: tuple[int, int], bg: tuple[int, int, int, int] = (0, 0, 0, 0)) -> Image.Image:
    canvas = Image.new("RGBA", size, bg)
    tmp = im.convert("RGBA").copy()
    tmp.thumbnail(size, Image.Resampling.LANCZOS)
    canvas.alpha_composite(tmp, ((size[0] - tmp.width) // 2, (size[1] - tmp.height) // 2))
    return canvas


def paste_card(
    canvas: Image.Image,
    im: Image.Image,
    xy: tuple[int, int],
    size: tuple[int, int],
    radius: int = 32,
    cover: bool = True,
    shadow: bool = True,
    border: tuple[int, int, int, int] | None = (255, 255, 255, 38),
) -> None:
    x, y = xy
    if shadow:
        sh = Image.new("RGBA", size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=(0, 0, 0, 120))
        sh = sh.filter(ImageFilter.GaussianBlur(28))
        canvas.alpha_composite(sh, (x, y + 18))
    fitted = fit_cover(im, size) if cover else fit_contain(im, size)
    mask = rounded_mask(size, radius)
    canvas.paste(fitted, xy, mask)
    if border:
        composite_round_rect(canvas, (x, y, size[0], size[1]), radius, (0, 0, 0, 0), border, 2)


def draw_text(
    d: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int] | tuple[int, int, int, int],
    max_width: int | None = None,
    line_spacing: int = 8,
) -> int:
    x, y = xy
    if not max_width:
        d.text((x, y), text, font=fnt, fill=fill)
        return y + d.textbbox((x, y), text, font=fnt)[3] - y
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if d.textlength(trial, font=fnt) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    for line in lines:
        d.text((x, y), line, font=fnt, fill=fill)
        y += fnt.size + line_spacing
    return y


def draw_rich_title(
    d: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    parts: list[tuple[str, tuple[int, int, int]]],
    fnt: ImageFont.FreeTypeFont,
    max_width: int,
    line_gap: int = 10,
) -> int:
    x0, y = xy
    x = x0
    for txt, col in parts:
        for word in txt.split(" "):
            token = word + " "
            tw = d.textlength(token, font=fnt)
            if x + tw > x0 + max_width and x > x0:
                x = x0
                y += int(fnt.size * 1.16) + line_gap
            d.text((x, y), token, font=fnt, fill=col)
            x += tw
    return y + int(fnt.size * 1.16) + line_gap


def busup_logo(d: ImageDraw.ImageDraw, xy: tuple[int, int], size: int = 34, dark: bool = False) -> None:
    x, y = xy
    col = (18, 26, 40) if dark else WHITE
    d.text((x, y), "BUS", font=font(size, True), fill=col)
    x2 = x + round(d.textlength("BUS", font=font(size, True)))
    d.text((x2, y), "UP", font=font(size, True), fill=BLUE)
    # Subtle smile under UP.
    d.arc((x2 + size // 2, y + size * 0.78, x2 + size * 2, y + size * 1.55), 18, 162, fill=col, width=max(2, size // 12))


def up_logo(max_w: int, light: bool = True) -> Image.Image:
    path = UP_LIGHT if light else UP_DARK
    im = trim_alpha(open_img(path))
    im.thumbnail((max_w, 90), Image.Resampling.LANCZOS)
    return im


def footer(canvas: Image.Image, slide_no: str, label: str, light: bool = False) -> None:
    d = ImageDraw.Draw(canvas)
    y = H - 72
    color = (38, 53, 75) if light else (160, 182, 207)
    line = (214, 224, 237, 255) if light else (69, 112, 160, 95)
    d.line((96, y - 22, W - 96, y - 22), fill=line, width=1)
    busup_logo(d, (96, y - 2), 24, dark=light)
    d.text((235, y + 4), label, font=F["small"], fill=color)
    logo = up_logo(136, light=not light)
    logo_x = W - 96 - logo.width
    canvas.alpha_composite(logo, (logo_x, y - 3))
    powered = "Powered by"
    powered_w = d.textlength(powered, font=F["small"])
    d.text((logo_x - powered_w - 22, y + 4), powered, font=F["small"], fill=color)


def eyebrow(d: ImageDraw.ImageDraw, text: str, no: str, light: bool = False) -> None:
    col = BLUE if light else BLUE_2
    d.text((96, 74), text.upper(), font=F["eyebrow"], fill=col)
    d.text((W - 140, 74), no, font=F["eyebrow"], fill=(91, 112, 137) if light else (105, 130, 158))


def pill(d: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fill: tuple[int, int, int, int], color=WHITE) -> None:
    x, y = xy
    pad_x = 18
    h = 38
    tw = d.textlength(text, font=font(17, True))
    if len(fill) == 4 and fill[3] < 255:
        layer = Image.new("RGBA", (int(tw + pad_x * 2) + 2, h + 2), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle((1, 1, int(tw + pad_x * 2), h), radius=19, fill=fill)
        d._image.alpha_composite(layer, (x - 1, y - 1))
    else:
        d.rounded_rectangle((x, y, x + tw + pad_x * 2, y + h), radius=19, fill=fill)
    d.text((x + pad_x, y + 8), text, font=font(17, True), fill=color)


def glass_panel(canvas: Image.Image, box: tuple[int, int, int, int], radius: int = 34, light: bool = False) -> None:
    x, y, w, h = box
    if light:
        fill = (255, 255, 255, 225)
        outline = (212, 225, 240, 255)
        shadow = (25, 57, 91, 32)
    else:
        fill = (255, 255, 255, 20)
        outline = (126, 200, 255, 38)
        shadow = (0, 0, 0, 80)
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=shadow)
    sh = sh.filter(ImageFilter.GaussianBlur(22))
    canvas.alpha_composite(sh, (x, y + 12))
    composite_round_rect(canvas, (x, y, w, h), radius, fill, outline, 1)


def card_metric(canvas: Image.Image, box: tuple[int, int, int, int], label: str, value: str, detail: str, light: bool = False) -> None:
    glass_panel(canvas, box, 26, light=light)
    d = ImageDraw.Draw(canvas)
    x, y, w, _ = box
    d.text((x + 26, y + 24), label.upper(), font=font(17, True), fill=BLUE if light else BLUE_2)
    d.text((x + 26, y + 62), value, font=F["h3"], fill=(20, 28, 42) if light else WHITE)
    d.text((x + 26, y + 108), detail, font=font(20), fill=(83, 101, 125) if light else MUTED)


def icon_circle(canvas: Image.Image, cx: int, cy: int, label: str) -> None:
    d = ImageDraw.Draw(canvas)
    d.ellipse((cx - 34, cy - 34, cx + 34, cy + 34), fill=(45, 140, 240, 255))
    d.text((cx - d.textlength(label, font=font(24, True)) / 2, cy - 15), label, font=font(24, True), fill=WHITE)


def paste_object(canvas: Image.Image, obj: Image.Image, xy: tuple[int, int], shadow: bool = True) -> None:
    x, y = xy
    obj = obj.convert("RGBA")
    if shadow:
        alpha = obj.getchannel("A")
        sh = Image.new("RGBA", obj.size, (0, 0, 0, 0))
        sh.putalpha(alpha.point(lambda p: int(p * 0.42)))
        sh = sh.filter(ImageFilter.GaussianBlur(26))
        canvas.alpha_composite(sh, (x, y + 22))
    canvas.alpha_composite(obj, xy)


def phone_mockup(src: Image.Image, size: tuple[int, int]) -> Image.Image:
    w, h = size
    obj = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(obj)
    body = (7, 10, 15, 255)
    edge = (62, 74, 88, 255)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=max(34, w // 7), fill=body, outline=edge, width=max(2, w // 80))
    bezel = max(10, w // 24)
    top = max(14, h // 55)
    bottom = max(14, h // 52)
    screen_box = (bezel, top, w - bezel, h - bottom)
    sw, sh = screen_box[2] - screen_box[0], screen_box[3] - screen_box[1]
    screen = fit_cover(src, (sw, sh), (0.5, 0.5))
    mask = rounded_mask((sw, sh), max(24, w // 10))
    obj.paste(screen, (screen_box[0], screen_box[1]), mask)
    island_w, island_h = int(w * 0.25), max(5, int(h * 0.012))
    d.rounded_rectangle(((w - island_w) // 2, top + 6, (w + island_w) // 2, top + 6 + island_h), radius=island_h // 2, fill=(12, 14, 18, 210))
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=max(34, w // 7), outline=(255, 255, 255, 30), width=1)
    return obj


def pos_mockup(src: Image.Image, size: tuple[int, int]) -> Image.Image:
    w, h = size
    obj = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(obj)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=max(28, w // 9), fill=(14, 15, 18, 255), outline=(82, 88, 96, 255), width=max(2, w // 90))
    d.rounded_rectangle((int(w * 0.34), int(h * 0.035), int(w * 0.66), int(h * 0.07)), radius=9, fill=(38, 40, 44, 255))
    nfc_cx, nfc_y = w // 2, int(h * 0.12)
    for r in (18, 28, 38):
        d.arc((nfc_cx - r, nfc_y - r, nfc_cx + r, nfc_y + r), 210, 330, fill=(65, 70, 76, 255), width=2)
    bezel = int(w * 0.11)
    sy = int(h * 0.18)
    sw = w - bezel * 2
    sh = int(h * 0.48)
    d.rounded_rectangle((bezel - 8, sy - 8, bezel + sw + 8, sy + sh + 8), radius=22, fill=(5, 6, 8, 255))
    screen = fit_cover(src, (sw, sh), (0.5, 0.5))
    obj.paste(screen, (bezel, sy), rounded_mask((sw, sh), 14))
    key_y = sy + sh + int(h * 0.035)
    key_w = int(w * 0.17)
    key_h = int(h * 0.042)
    gap_x = int(w * 0.045)
    gap_y = int(h * 0.014)
    colors = [(220, 65, 42), (224, 181, 39), (41, 184, 82)]
    for c in range(3):
        x = int(w * 0.18) + c * (key_w + gap_x)
        d.rounded_rectangle((x, key_y, x + key_w, key_y + key_h), radius=8, fill=colors[c], outline=(0, 0, 0, 80))
    labels = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "OK", "0", "."]
    y = key_y + key_h + gap_y
    for row in range(4):
        for col in range(3):
            x = int(w * 0.18) + col * (key_w + gap_x)
            d.rounded_rectangle((x, y, x + key_w, y + key_h), radius=8, fill=(31, 33, 36, 255), outline=(83, 88, 95, 255), width=1)
            label = labels[row * 3 + col]
            d.text((x + key_w / 2 - d.textlength(label, font=font(15, True)) / 2, y + key_h / 2 - 9), label, font=font(15, True), fill=(230, 235, 240))
        y += key_h + gap_y
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=max(28, w // 9), outline=(255, 255, 255, 22), width=1)
    return obj


def laptop_mockup(src: Image.Image, size: tuple[int, int]) -> Image.Image:
    w, h = size
    obj = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(obj)
    screen_w = int(w * 0.84)
    screen_h = int(screen_w * 0.57)
    sx = (w - screen_w) // 2
    sy = int(h * 0.05)
    d.rounded_rectangle((sx - 16, sy - 16, sx + screen_w + 16, sy + screen_h + 18), radius=22, fill=(8, 11, 16, 255), outline=(80, 90, 105, 255), width=2)
    screen = fit_cover(src, (screen_w, screen_h), (0.5, 0.5))
    obj.paste(screen, (sx, sy), rounded_mask((screen_w, screen_h), 8))
    base_y = sy + screen_h + 26
    base_w = int(w * 0.95)
    base_h = int(h * 0.16)
    bx = (w - base_w) // 2
    d.rounded_rectangle((bx, base_y, bx + base_w, base_y + base_h), radius=14, fill=(92, 101, 114, 255))
    d.rectangle((bx + 28, base_y, bx + base_w - 28, base_y + int(base_h * 0.48)), fill=(123, 132, 145, 255))
    d.rounded_rectangle((w // 2 - 90, base_y + 16, w // 2 + 90, base_y + 32), radius=8, fill=(75, 83, 94, 255))
    d.rounded_rectangle((bx, base_y + base_h - 14, bx + base_w, base_y + base_h), radius=12, fill=(54, 61, 72, 255))
    return obj


def browser_window(src: Image.Image, size: tuple[int, int]) -> Image.Image:
    w, h = size
    obj = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(obj)
    chrome_h = 52
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=26, fill=(255, 255, 255, 255), outline=(206, 220, 236, 255), width=1)
    d.rounded_rectangle((0, 0, w - 1, chrome_h), radius=26, fill=(246, 249, 253, 255))
    d.rectangle((0, chrome_h - 14, w - 1, chrome_h), fill=(246, 249, 253, 255))
    for i, col in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse((24 + i * 26, 20, 38 + i * 26, 34), fill=col)
    d.rounded_rectangle((118, 16, w - 26, 38), radius=11, fill=(236, 241, 247, 255))
    viewport = Image.new("RGBA", (w - 2, h - chrome_h - 1), (255, 255, 255, 255))
    shot = src.convert("RGBA").copy()
    shot.thumbnail((w - 2, h - chrome_h - 1), Image.Resampling.LANCZOS)
    viewport.alpha_composite(shot, ((viewport.width - shot.width) // 2, (viewport.height - shot.height) // 2))
    obj.alpha_composite(viewport, (1, chrome_h))
    return obj


def qr_image() -> Image.Image | None:
    path = ROOT / "qr.b64.txt"
    if not path.exists():
        return None
    data = path.read_text().strip()
    if "," in data:
        data = data.split(",", 1)[1]
    data += "=" * (-len(data) % 4)
    raw = base64.b64decode(data)
    return Image.open(io.BytesIO(raw)).convert("RGBA")


def slide_01() -> Image.Image:
    im = gradient_bg()
    d = ImageDraw.Draw(im)
    busup_logo(d, (96, 76), 42)
    pill(d, (W - 470, 76), "Apresentação institucional 2026", (255, 255, 255, 22), BLUE_2)
    y = draw_rich_title(
        d,
        (96, 190),
        [("Transporte público inteligente ", WHITE), ("com controlo total de receita.", BLUE_2)],
        F["mega"],
        910,
        14,
    )
    draw_text(
        d,
        (100, y + 18),
        "BusUp transforma pagamentos, validação e gestão operacional numa plataforma cashless para municípios e operadores.",
        F["body"],
        MUTED,
        760,
        9,
    )
    portal = browser_window(open_img(SHOTS / "portal_dashboard.png"), (820, 520))
    paste_object(im, portal, (930, 250))
    metrics = [("Cashless", "QR + NFC", "Menos numerário"), ("Auditoria", "Real time", "Cada validação registada"), ("Operação", "3 canais", "Mobile / POS / Portal")]
    x = 96
    for label, value, detail in metrics:
        glass_panel(im, (x, 800, 220, 125), radius=24)
        d.text((x + 22, 824), label.upper(), font=font(16, True), fill=BLUE_2)
        d.text((x + 22, 866), value, font=font(24, True), fill=WHITE)
        d.text((x + 22, 904), detail, font=font(18), fill=MUTED)
        x += 250
    footer(im, "01", "Executive product deck")
    return im


def slide_02() -> Image.Image:
    im = light_bg()
    d = ImageDraw.Draw(im)
    eyebrow(d, "Resumo executivo", "02", light=True)
    title_y = draw_rich_title(
        d,
        (96, 150),
        [("Modernização sem fricção para passageiros, agentes e gestores.", (20, 28, 42))],
        F["h1"],
        840,
    )
    draw_text(
        d,
        (100, title_y + 18),
        "A proposta não é apenas digitalizar bilhetes: é criar uma camada operacional auditável para receitas, rotas, frota, passageiros e validações.",
        F["body"],
        (82, 101, 126),
        760,
    )
    portal = browser_window(open_img(SHOTS / "portal_dashboard.png"), (800, 500))
    paste_object(im, portal, (1025, 140))
    items = [
        ("01", "Arrecadação rastreável", "Receita registada e consultável em tempo real, por rota, terminal e agente."),
        ("02", "Pagamento inclusivo", "Smartphone, QR Code e cartão NFC para cobrir todos os perfis de passageiro."),
        ("03", "Decisão com dados", "Mapas, relatórios e histórico para planeamento de mobilidade urbana."),
        ("04", "Operação local", "Suporte e integração com pagamentos nacionais em Moçambique."),
    ]
    x, y = 96, 645
    for i, (num, title, body) in enumerate(items):
        bx = x + (i % 2) * 470
        by = y + (i // 2) * 170
        glass_panel(im, (bx, by, 430, 132), radius=24, light=True)
        d.text((bx + 24, by + 26), num, font=font(22, True), fill=BLUE)
        d.text((bx + 78, by + 22), title, font=font(25, True), fill=(20, 28, 42))
        draw_text(d, (bx + 78, by + 58), body, font(20), (82, 101, 126), 310, 4)
    footer(im, "02", "Resumo executivo", light=True)
    return im


def slide_03() -> Image.Image:
    im = gradient_bg()
    d = ImageDraw.Draw(im)
    eyebrow(d, "O problema", "03")
    title_y = draw_rich_title(
        d,
        (96, 150),
        [("O numerário cria perda, lentidão e falta de transparência.", WHITE)],
        F["h1"],
        760,
    )
    draw_text(
        d,
        (100, title_y + 18),
        "Quando cada pagamento acontece fora de um sistema auditável, a cidade perde receita, dados e capacidade de gestão.",
        F["body"],
        MUTED,
        700,
    )
    composite_round_rect(im, (1195, 118, 510, 760), 38, (255, 255, 255, 16), (126, 200, 255, 45), 1)
    phone = phone_mockup(open_img(SHOTS / "mobile_bilhete.png"), (330, 720))
    paste_object(im, phone, (1285, 142))
    problems = [
        ("Receita invisível", "Sem registo digital, não há reconciliação confiável."),
        ("Planeamento cego", "Sem dados por rota e horário, a frota é gerida por intuição."),
        ("Embarque lento", "Troco e validação manual criam filas nos pontos de paragem."),
        ("Risco operacional", "Dinheiro físico aumenta exposição a fraude e insegurança."),
    ]
    for i, (title, body) in enumerate(problems):
        bx = 96 + (i % 2) * 450
        by = 575 + (i // 2) * 165
        glass_panel(im, (bx, by, 410, 124), radius=24)
        icon_circle(im, bx + 52, by + 62, str(i + 1))
        d.text((bx + 104, by + 28), title, font=font(25, True), fill=WHITE)
        draw_text(d, (bx + 104, by + 62), body, font(19), MUTED, 270, 4)
    footer(im, "03", "Problema operacional")
    return im


def slide_04() -> Image.Image:
    im = light_bg()
    d = ImageDraw.Draw(im)
    eyebrow(d, "Arquitetura da solução", "04", light=True)
    title_y = draw_rich_title(d, (96, 145), [("Uma plataforma. Três superfícies. Um fluxo de dados.", (20, 28, 42))], F["h1"], 1060)
    draw_text(d, (100, title_y + 14), "BusUp liga passageiro, agente e gestão municipal numa cadeia única: emissão, pagamento, validação e auditoria.", F["body"], (82, 101, 126), 820)
    modules = [
        ("App Passageiro", "Carteira, QR, bilhetes e histórico.", "MOBILE"),
        ("Terminal POS", "Venda, validação QR/NFC e operação do agente.", "POS"),
        ("Portal de Gestão", "Receita, rotas, frota, passageiros e auditoria.", "PORTAL"),
    ]
    start_x = 116
    for i, (title, body, tag) in enumerate(modules):
        bx = start_x + i * 580
        by = 520
        glass_panel(im, (bx, by, 500, 255), radius=32, light=True)
        d.text((bx + 34, by + 34), tag, font=font(18, True), fill=BLUE)
        d.text((bx + 34, by + 82), title, font=F["h3"], fill=(20, 28, 42))
        draw_text(d, (bx + 34, by + 136), body, font(23), (82, 101, 126), 390, 6)
        if i < 2:
            ax = bx + 515
            d.line((ax, by + 128, ax + 44, by + 128), fill=(45, 140, 240), width=4)
            d.polygon([(ax + 44, by + 128), (ax + 26, by + 118), (ax + 26, by + 138)], fill=(45, 140, 240))
    # Data rail.
    d.rounded_rectangle((260, 835, 1660, 900), radius=32, fill=(13, 59, 102, 255))
    d.text((334, 854), "Pagamento e validação", font=font(23, True), fill=WHITE)
    d.text((720, 854), "Dados operacionais", font=font(23, True), fill=WHITE)
    d.text((1095, 854), "Auditoria e relatórios", font=font(23, True), fill=WHITE)
    footer(im, "04", "Arquitetura de produto", light=True)
    return im


def slide_05() -> Image.Image:
    im = gradient_bg()
    d = ImageDraw.Draw(im)
    eyebrow(d, "Experiência do passageiro", "05")
    title_y = draw_rich_title(d, (96, 145), [("Carteira digital, bilhete QR e cartão NFC para inclusão real.", WHITE)], F["h1"], 820)
    draw_text(d, (100, title_y + 16), "A experiência precisa ser simples no primeiro uso e confiável todos os dias. O passageiro vê saldo, compra bilhete e apresenta QR ao agente.", F["body"], MUTED, 700)
    composite_round_rect(im, (1195, 112, 500, 760), 38, (255, 255, 255, 16), (126, 200, 255, 45), 1)
    phone = phone_mockup(open_img(SHOTS / "mobile_carteira.png"), (330, 720))
    paste_object(im, phone, (1280, 136))
    features = [
        ("Recarga integrada", "M-Pesa / e-Mola, sem filas de atendimento."),
        ("QR de embarque", "Validação rápida, legível e auditável."),
        ("Histórico completo", "Movimentos, bilhetes e perfil num só lugar."),
        ("Alternativa NFC", "Cartão recarregável para quem não usa smartphone."),
    ]
    for i, (title, body) in enumerate(features):
        by = 560 + i * 92
        glass_panel(im, (96, by, 820, 72), radius=20)
        d.ellipse((122, by + 20, 154, by + 52), fill=BLUE)
        d.text((174, by + 14), title, font=font(24, True), fill=WHITE)
        d.text((410, by + 17), body, font=font(21), fill=MUTED)
    footer(im, "05", "App Passageiro")
    return im


def slide_06() -> Image.Image:
    im = gradient_bg()
    d = ImageDraw.Draw(im)
    eyebrow(d, "Operação no terreno", "06")
    title_y = draw_rich_title(d, (96, 145), [("O POS transforma cada venda e validação num evento auditável.", WHITE)], F["h1"], 820)
    draw_text(d, (100, title_y + 16), "O agente opera num terminal físico: vende, valida QR ou NFC, confirma estado e sincroniza tudo com o portal.", F["body"], MUTED, 700)
    composite_round_rect(im, (1195, 112, 500, 760), 38, (255, 255, 255, 16), (126, 200, 255, 45), 1)
    pos = pos_mockup(open_img(SHOTS / "pos_venda_ok.png"), (350, 745))
    paste_object(im, pos, (1270, 118))
    steps = [("1", "Escolhe viagem"), ("2", "Recebe pagamento"), ("3", "Emite/valida bilhete"), ("4", "Sincroniza no portal")]
    for i, (num, text) in enumerate(steps):
        bx = 110 + (i % 2) * 420
        by = 570 + (i // 2) * 145
        glass_panel(im, (bx, by, 360, 104), radius=24)
        icon_circle(im, bx + 58, by + 52, num)
        draw_text(d, (bx + 112, by + 34), text, font(25, True), WHITE, 220, 4)
    footer(im, "06", "Terminal POS")
    return im


def slide_07() -> Image.Image:
    im = light_bg()
    d = ImageDraw.Draw(im)
    eyebrow(d, "Gestão e receita", "07", light=True)
    draw_rich_title(d, (96, 145), [("Painel executivo para receita, recargas e rotas.", (20, 28, 42))], F["h1"], 620)
    portal = browser_window(open_img(SHOTS / "portal_dashboard.png"), (980, 590))
    paste_object(im, portal, (760, 145))
    metrics = [
        ("Receita hoje", "970,00 MZN", "66 validações"),
        ("Top-ups hoje", "4500,00 MZN", "21 recargas"),
        ("Saldo em circulação", "21 180,00 MZN", "60 passageiros"),
    ]
    y = 425
    for label, value, detail in metrics:
        card_metric(im, (96, y, 520, 126), label, value, detail, light=True)
        y += 150
    footer(im, "07", "Portal de Gestão", light=True)
    return im


def slide_08() -> Image.Image:
    im = light_bg()
    d = ImageDraw.Draw(im)
    eyebrow(d, "Controlo municipal", "08", light=True)
    title_y = draw_rich_title(d, (96, 145), [("Da operação diária ao planeamento urbano.", (20, 28, 42))], F["h1"], 760)
    draw_text(d, (100, title_y + 14), "O município ganha uma visão operacional de rede: onde há procura, onde há validações, quais rotas performam e onde existem bloqueios.", F["body"], (82, 101, 126), 720)
    mapa = open_img(SHOTS / "portal_mapa.png")
    val = open_img(SHOTS / "portal_validacoes.png")
    paste_card(im, mapa, (960, 145), (770, 360), radius=28, cover=True, shadow=True, border=(210, 225, 242, 255))
    paste_card(im, val, (960, 545), (770, 360), radius=28, cover=True, shadow=True, border=(210, 225, 242, 255))
    benefits = [
        ("Transparência total", "Receita auditável por rota, terminal e agente."),
        ("Planeamento", "Fluxo por rota, horário e veículo para ajustar oferta."),
        ("Segurança", "Menos numerário e histórico completo de operação."),
        ("Suporte local", "Operação e integração feitas em Moçambique."),
    ]
    y = 515
    for title, body in benefits:
        d.ellipse((116, y + 7, 142, y + 33), fill=BLUE)
        d.text((166, y), title, font=font(25, True), fill=(20, 28, 42))
        d.text((166, y + 34), body, font=font(21), fill=(82, 101, 126))
        y += 92
    footer(im, "08", "Controlo e auditoria", light=True)
    return im


def slide_09() -> Image.Image:
    im = gradient_bg()
    d = ImageDraw.Draw(im)
    eyebrow(d, "Enterprise readiness", "09")
    title_y = draw_rich_title(d, (96, 145), [("Pronto para piloto, expansão e operação continuada.", WHITE)], F["h1"], 850)
    draw_text(d, (100, title_y + 16), "A apresentação precisava desta camada: como a solução entra em produção, como é suportada e como reduz risco operacional.", F["body"], MUTED, 760)
    roadmap = [("0-30 dias", "Piloto controlado", "Rotas selecionadas, POS configurados e equipa treinada."), ("31-60 dias", "Expansão", "Cartões NFC, campanhas de recarga e relatórios executivos."), ("61-90 dias", "Operação plena", "KPIs, auditoria financeira e melhoria contínua por dados.")]
    x = 110
    for period, title, body in roadmap:
        glass_panel(im, (x, 535, 520, 250), radius=32)
        d.text((x + 34, 570), period, font=font(22, True), fill=BLUE_2)
        d.text((x + 34, 622), title, font=F["h3"], fill=WHITE)
        draw_text(d, (x + 34, 680), body, font(23), MUTED, 420, 6)
        x += 575
    chips = ["Pagamentos locais", "OTA", "Auditoria", "Relatórios", "Suporte local", "QR + NFC"]
    x, y = 110, 835
    for chip in chips:
        pill(d, (x, y), chip, (255, 255, 255, 22), BLUE_2)
        x += int(d.textlength(chip, font=font(17, True))) + 58
    footer(im, "09", "Plano de implementação")
    return im


def slide_10() -> Image.Image:
    im = gradient_bg()
    d = ImageDraw.Draw(im)
    busup_logo(d, (96, 78), 42)
    logo = up_logo(210, light=True)
    logo_x = W - 96 - logo.width
    im.alpha_composite(logo, (logo_x, 72))
    powered = "Powered by"
    d.text((logo_x - d.textlength(powered, font=font(22)) - 24, 88), powered, font=font(22), fill=MUTED)
    draw_rich_title(
        d,
        (96, 200),
        [("Leve o BusUp para a sua cidade.", WHITE)],
        F["mega"],
        980,
    )
    draw_text(
        d,
        (100, 380),
        "Agende uma demonstração executiva. Em poucos dias, a equipa pode validar rotas, terminais, carteira, QR/NFC e relatórios em ambiente operacional.",
        F["body"],
        MUTED,
        850,
    )
    qr = qr_image()
    if qr:
        glass_panel(im, (1320, 232, 370, 460), radius=34)
        q = fit_contain(qr, (260, 260), (255, 255, 255, 255))
        paste_card(im, q, (1375, 282), (260, 260), radius=18, cover=False, shadow=False, border=None)
        d.text((1388, 575), "Aponte a câmara", font=font(28, True), fill=WHITE)
        d.text((1378, 620), "Demo e contacto comercial", font=font(20), fill=MUTED)
    cta_box = (96, 725, 1030, 166)
    x, y, w, h = cta_box
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((0, 0, w - 1, h - 1), radius=34, fill=(0, 0, 0, 130))
    sh = sh.filter(ImageFilter.GaussianBlur(24))
    im.alpha_composite(sh, (x, y + 14))
    d.rounded_rectangle((x, y, x + w, y + h), radius=34, fill=(5, 34, 62, 255), outline=(80, 160, 230, 140), width=1)
    d.text((130, 762), "Demo executiva", font=font(24, True), fill=BLUE_2)
    d.text((130, 806), "Contacto comercial UpDigital", font=font(33, True), fill=WHITE)
    d.text((130, 854), "updigital.co.mz   |   busup.updigital.co.mz", font=font(24), fill=MUTED)
    footer(im, "10", "Contacto e próximos passos")
    return im


def make_contact_sheet(slides: list[Image.Image]) -> None:
    thumb_w, thumb_h = 430, 242
    cols = 2
    rows = math.ceil(len(slides) / cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + 40)), "white")
    d = ImageDraw.Draw(sheet)
    for i, slide in enumerate(slides):
        thumb = slide.convert("RGB").copy()
        thumb.thumbnail((thumb_w - 20, thumb_h - 14), Image.Resampling.LANCZOS)
        x = (i % cols) * thumb_w + (thumb_w - thumb.width) // 2
        y = (i // cols) * (thumb_h + 40) + 8
        sheet.paste(thumb, (x, y))
        d.text(((i % cols) * thumb_w + 16, y + thumb.height + 8), f"Slide {i + 1:02d}", fill=(20, 28, 42), font=font(16, True))
    sheet.save(EXPORT / "BusUp-Apresentacao-Premium-contact-sheet.jpg", quality=92)


def _group_shape_xml() -> str:
    return """
        <p:nvGrpSpPr>
          <p:cNvPr id="1" name=""/>
          <p:cNvGrpSpPr/>
          <p:nvPr/>
        </p:nvGrpSpPr>
        <p:grpSpPr>
          <a:xfrm>
            <a:off x="0" y="0"/>
            <a:ext cx="0" cy="0"/>
            <a:chOff x="0" y="0"/>
            <a:chExt cx="0" cy="0"/>
          </a:xfrm>
        </p:grpSpPr>
    """


def make_pptx(pngs: list[Path], out: Path) -> None:
    """Create a dependency-free PPTX with each PNG as a full-slide image."""

    slide_cx = 12192000
    slide_cy = 6858000
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    content_overrides = "\n".join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, len(pngs) + 1)
    )
    slide_ids = "\n".join(
        f'<p:sldId id="{255 + i}" r:id="rId{i + 1}"/>' for i in range(1, len(pngs) + 1)
    )
    presentation_rels = "\n".join(
        f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
        for i in range(1, len(pngs) + 1)
    )

    content_types = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
  {content_overrides}
</Types>"""

    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

    core = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>BusUp Apresentacao Premium</dc:title>
  <dc:creator>UpDigital</dc:creator>
  <cp:lastModifiedBy>UpDigital</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>"""

    app = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>BusUp Marketing Deck Generator</Application>
  <PresentationFormat>Wide</PresentationFormat>
  <Slides>{len(pngs)}</Slides>
  <Company>UpDigital</Company>
</Properties>"""

    presentation = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst>
    <p:sldMasterId id="2147483648" r:id="rId1"/>
  </p:sldMasterIdLst>
  <p:sldIdLst>
    {slide_ids}
  </p:sldIdLst>
  <p:sldSz cx="{slide_cx}" cy="{slide_cy}" type="wide"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>"""

    presentation_rels_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
  {presentation_rels}
</Relationships>"""

    slide_layout = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
  <p:cSld name="Blank">
    <p:spTree>{_group_shape_xml()}</p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>"""

    slide_layout_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>"""

    slide_master = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree>{_group_shape_xml()}</p:spTree></p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst>
    <p:sldLayoutId id="2147483649" r:id="rId1"/>
  </p:sldLayoutIdLst>
  <p:txStyles>
    <p:titleStyle/><p:bodyStyle/><p:otherStyle/>
  </p:txStyles>
</p:sldMaster>"""

    slide_master_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>"""

    theme = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="BusUp">
  <a:themeElements>
    <a:clrScheme name="BusUp">
      <a:dk1><a:srgbClr val="051528"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>
      <a:dk2><a:srgbClr val="0D3B66"/></a:dk2><a:lt2><a:srgbClr val="F6F9FD"/></a:lt2>
      <a:accent1><a:srgbClr val="2D8CF0"/></a:accent1><a:accent2><a:srgbClr val="7EC8FF"/></a:accent2>
      <a:accent3><a:srgbClr val="0D3B66"/></a:accent3><a:accent4><a:srgbClr val="AFC3D8"/></a:accent4>
      <a:accent5><a:srgbClr val="132B45"/></a:accent5><a:accent6><a:srgbClr val="FFFFFF"/></a:accent6>
      <a:hlink><a:srgbClr val="2D8CF0"/></a:hlink><a:folHlink><a:srgbClr val="0D3B66"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="BusUp"><a:majorFont><a:latin typeface="Aptos Display"/></a:majorFont><a:minorFont><a:latin typeface="Aptos"/></a:minorFont></a:fontScheme>
    <a:fmtScheme name="BusUp"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
  </a:themeElements>
</a:theme>"""

    def slide_xml(i: int, name: str) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      {_group_shape_xml()}
      <p:pic>
        <p:nvPicPr>
          <p:cNvPr id="2" name="{name}"/>
          <p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr>
          <p:nvPr/>
        </p:nvPicPr>
        <p:blipFill><a:blip r:embed="rId1"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>
        <p:spPr>
          <a:xfrm><a:off x="0" y="0"/><a:ext cx="{slide_cx}" cy="{slide_cy}"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
      </p:pic>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""

    def slide_rels(i: int) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image{i}.png"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>"""

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
        z.writestr("ppt/presentation.xml", presentation)
        z.writestr("ppt/_rels/presentation.xml.rels", presentation_rels_xml)
        z.writestr("ppt/slideLayouts/slideLayout1.xml", slide_layout)
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", slide_layout_rels)
        z.writestr("ppt/slideMasters/slideMaster1.xml", slide_master)
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", slide_master_rels)
        z.writestr("ppt/theme/theme1.xml", theme)
        for i, png in enumerate(pngs, start=1):
            z.writestr(f"ppt/slides/slide{i}.xml", slide_xml(i, png.name))
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", slide_rels(i))
            z.write(png, f"ppt/media/image{i}.png")


def main() -> None:
    mkdirs()
    slides = [
        slide_01(),
        slide_02(),
        slide_03(),
        slide_04(),
        slide_05(),
        slide_06(),
        slide_07(),
        slide_08(),
        slide_09(),
        slide_10(),
    ]
    pngs = []
    for i, slide in enumerate(slides, start=1):
        path = SLIDES_DIR / f"slide-{i:02d}.png"
        slide.convert("RGB").save(path, quality=95)
        pngs.append(path)
    pdf_path = ROOT / "BusUp-Apresentacao.pdf"
    pptx_path = ROOT / "BusUp-Apresentacao-Premium.pptx"
    rgb = [s.convert("RGB") for s in slides]
    rgb[0].save(pdf_path, save_all=True, append_images=rgb[1:], resolution=144.0)
    make_pptx(pngs, pptx_path)
    make_contact_sheet(slides)
    print(f"Wrote {pdf_path}")
    print(f"Wrote {pptx_path}")
    print(f"Wrote {SLIDES_DIR}")
    print(f"Wrote {EXPORT / 'BusUp-Apresentacao-Premium-contact-sheet.jpg'}")


if __name__ == "__main__":
    main()
