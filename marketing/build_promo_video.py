#!/usr/bin/env python3
"""Video promocional BusUp (motion design enterprise, ~46s, 1080p30).

Linguagem: produto SEMPRE 100% visivel — cartoes flutuantes e janelas de
browser sobre o fundo navy da marca, texto ao lado, movimento lento e subtil
(sem zoom agressivo). Frames deterministicos com PIL; encode com o ffmpeg do
imageio-ffmpeg.

Uso: backend/.venv312/bin/python marketing/build_promo_video.py
Saida: marketing/BusUp-Promo.mp4
"""

from __future__ import annotations

import base64
import io
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "deck_assets"
FRAMES = ROOT / "premium_export" / "promo_frames"
OUT = ROOT / "BusUp-Promo.mp4"

W, H = 1920, 1080
FPS = 30
FADE = 16  # frames de crossfade entre cenas

NAVY = (10, 22, 40)
BLUE = (45, 140, 240)
BLUE2 = (125, 185, 255)
WHITE = (255, 255, 255)
MUTED = (176, 198, 224)

FONT = "/System/Library/Fonts/HelveticaNeue.ttc"


def font(size: int, weight: str = "bold") -> ImageFont.FreeTypeFont:
    idx = {"regular": 0, "bold": 1, "light": 7, "medium": 10}[weight]
    return ImageFont.truetype(FONT, size, index=idx)


def ease(t: float) -> float:
    """Cubic in-out."""
    t = min(max(t, 0.0), 1.0)
    return 4 * t * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 3) / 2


def navy_bg() -> Image.Image:
    """Fundo navy com glows radiais azuis (mesma linguagem do deck)."""
    im = Image.new("RGB", (W, H), NAVY)
    glow = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(glow)
    d.ellipse((W * 0.58, -H * 0.45, W * 1.4, H * 0.72), fill=64)
    d.ellipse((-W * 0.28, H * 0.55, W * 0.38, H * 1.5), fill=42)
    glow = glow.filter(ImageFilter.GaussianBlur(190))
    blue = Image.new("RGB", (W, H), (24, 66, 124))
    im = Image.composite(blue, im, glow)
    # linha de horizonte subtil
    d2 = ImageDraw.Draw(im, "RGBA")
    d2.line((0, H - 3, W, H - 3), fill=BLUE + (26,), width=2)
    return im


def load(path: Path, max_w: int = 2600, crop: tuple[int, int, int, int] | None = None) -> Image.Image:
    """Abre, CORTA primeiro (coordenadas do original) e so depois reduz —
    cortar depois de reduzir preencheria o excesso a preto."""
    im = Image.open(path).convert("RGB")
    if crop:
        im = im.crop(crop)
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    return im


def load_rgba(path: Path, max_w: int) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    if bbox:
        im = im.crop(bbox)
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    return im


def rounded(im: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *im.size), radius=radius, fill=255)
    out = im.convert("RGBA")
    out.putalpha(mask)
    return out


def photo_card(im: Image.Image, height: int, radius: int = 34) -> Image.Image:
    """Foto inteira (sem crop) como cartao arredondado com borda subtil."""
    w = round(im.width * height / im.height)
    card = rounded(im.resize((w, height), Image.LANCZOS), radius)
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, w - 1, height - 1), radius=radius,
                        outline=(255, 255, 255, 46), width=2)
    return card


def browser_window(shot: Image.Image, width: int, url: str) -> Image.Image:
    """Captura inteira numa janela de browser minimalista (como no deck)."""
    bar_h = 62
    sw = width
    sh = round(shot.height * sw / shot.width)
    win = Image.new("RGBA", (sw, sh + bar_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(win)
    d.rounded_rectangle((0, 0, sw, sh + bar_h), radius=22, fill=(16, 32, 56, 255))
    for i, c in enumerate([(255, 96, 92), (255, 189, 68), (0, 202, 78)]):
        d.ellipse((26 + i * 34, bar_h // 2 - 8, 42 + i * 34, bar_h // 2 + 8), fill=c)
    f = font(24, "regular")
    tb = d.textbbox((0, 0), url, font=f)
    pw = tb[2] - tb[0] + 44
    d.rounded_rectangle(((sw - pw) // 2, 13, (sw + pw) // 2, bar_h - 13),
                        radius=18, fill=(28, 52, 86, 255))
    d.text(((sw - (tb[2] - tb[0])) // 2, (bar_h - (tb[3] - tb[1])) // 2 - tb[1]),
           url, font=f, fill=(168, 196, 228))
    shot_r = rounded(shot.resize((sw, sh), Image.LANCZOS), 1)
    win.paste(shot_r, (0, bar_h), shot_r)
    # re-arredonda o conjunto
    return rounded(win.convert("RGB"), 22)


def with_shadow(art: Image.Image, blur: int = 42, dy: int = 26, alpha: int = 120) -> Image.Image:
    """Devolve arte + sombra suave num canvas maior (pronto a colar)."""
    pad = blur * 2
    canvas = Image.new("RGBA", (art.width + pad * 2, art.height + pad * 2 + dy), (0, 0, 0, 0))
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    a = art.getchannel("A").point(lambda v: min(v, alpha))
    black = Image.new("RGBA", art.size, (0, 0, 0, 255))
    black.putalpha(a)
    sh.paste(black, (pad, pad + dy), black)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(sh)
    canvas.alpha_composite(art, (pad, pad))
    return canvas


def paste_center(im: Image.Image, art: Image.Image, cx: int, cy: int,
                 alpha: float = 1.0, scale: float = 1.0) -> None:
    a = art
    if scale != 1.0:
        a = art.resize((max(1, round(art.width * scale)), max(1, round(art.height * scale))), Image.LANCZOS)
    if alpha < 1.0:
        a = a.copy()
        a.putalpha(a.getchannel("A").point(lambda v: round(v * alpha)))
    im.paste(a, (cx - a.width // 2, cy - a.height // 2), a)


def drift(im: Image.Image, art: Image.Image, cx: int, cy: int, t: float,
          appear: float = 0.45, rise: int = 40, s0: float = 0.985, s1: float = 1.015) -> None:
    """Entrada com fade+subida e depois deriva de escala quase imperceptivel."""
    a = ease(t / appear)
    s = s0 + (s1 - s0) * ease(t)
    paste_center(im, art, cx, cy + round((1 - a) * rise), alpha=a, scale=s)


def kicker_text(d: ImageDraw.ImageDraw, x: int, y: int, txt: str, alpha: float) -> None:
    f = font(27, "medium")
    d.text((x, y), " ".join(txt.upper()), font=f, fill=BLUE2 + (round(255 * alpha),))


def left_block(im: Image.Image, t: float, x: int, y: int, kicker: str,
               head_lines: list[str], sub_lines: list[str],
               head_size: int = 76, sub_size: int = 42) -> int:
    """Bloco de texto alinhado a esquerda: kicker -> headline -> sub, em cascata."""
    d = ImageDraw.Draw(im, "RGBA")
    ka = ease(t / 0.35)
    if ka > 0:
        kicker_text(d, x, y + round((1 - ka) * 24), kicker, ka)
    yy = y + 64
    fh = font(head_size, "bold")
    for i, line in enumerate(head_lines):
        la = ease((t - 0.12 - i * 0.1) / 0.45)
        if la > 0:
            d.text((x, yy + round((1 - la) * 40)), line, font=fh, fill=WHITE + (round(255 * la),))
        yy += round(head_size * 1.18)
    yy += 22
    fs = font(sub_size, "light")
    for i, line in enumerate(sub_lines):
        la = ease((t - 0.34 - i * 0.1) / 0.45)
        if la > 0:
            d.text((x, yy + round((1 - la) * 34)), line, font=fs, fill=MUTED + (round(255 * la),))
        yy += round(sub_size * 1.42)
    return yy


def pill(width: int, height: int, color: tuple, logo: Image.Image) -> Image.Image:
    im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, width, height), radius=height // 4, fill=color + (255,))
    lg = logo.copy()
    lh = round(height * 0.5)
    lg = lg.resize((round(lg.width * lh / lg.height), lh), Image.LANCZOS)
    im.paste(lg, ((width - lg.width) // 2, (height - lg.height) // 2), lg)
    return im


# ----------------------------------------------------------------------------
# Assets
# ----------------------------------------------------------------------------
print("a carregar assets...")
LOGO = load_rgba(ASSETS / "logo_dark.png", 860)
UP_REV = load_rgba(ASSETS / "up_full_rev.png", 340)
POSTER = load(ROOT / "ChatGPT Image Jul 16, 2026, 01_43_54 PM (4).png", crop=(0, 172, 1003, 1224))
TICKET = load(ROOT / "premium_assets/ticket_qr_phone_hand_bus_final_4x5.png")
POS = load(ROOT / "premium_assets/pos_terminal_payment_final_4x5.png")
PHONE = load(ASSETS / "photo_phone_blue.png")
DASH = load(ROOT / "shots/portal_dashboard.png", crop=(0, 0, 3012, 1500))
MAPA = load(ROOT / "shots/portal_mapa.png", crop=(548, 500, 2400, 1490))
MPESA = load_rgba(ASSETS / "pay_mpesa.png", 300)
EMOLA = load_rgba(ASSETS / "pay_emola.png", 300)
qr_data = (ROOT / "qr.b64.txt").read_text().strip()
qr_b64 = qr_data.split(",", 1)[1] if qr_data.startswith("data:") else qr_data
QR = Image.open(io.BytesIO(base64.b64decode(qr_b64))).convert("RGB").resize((236, 236), Image.LANCZOS)

BG = navy_bg()

# artes pre-compostas (cartao + sombra) — geradas uma vez
CARD_TICKET = with_shadow(photo_card(TICKET, 780))
CARD_POS = with_shadow(photo_card(POS, 780))
CARD_PHONE = with_shadow(photo_card(PHONE, 780))
CARD_POSTER = with_shadow(photo_card(POSTER, 860, radius=28))
WIN_DASH = with_shadow(browser_window(DASH, 1460, "busup.updigital.co.mz/app"), blur=48, dy=30)
WIN_MAPA = with_shadow(browser_window(MAPA, 1060, "busup.updigital.co.mz/app/map"), blur=48, dy=30)
PILL_MPESA = pill(272, 88, (230, 0, 0), MPESA)
PILL_EMOLA = pill(272, 88, (245, 130, 31), EMOLA)


# ----------------------------------------------------------------------------
# Cenas (t: 0..1 -> frame 1920x1080)
# ----------------------------------------------------------------------------

def s1_logo(t: float) -> Image.Image:
    im = BG.copy()
    a = ease(t / 0.45)
    paste_center(im, LOGO, W // 2, H // 2 - 70, alpha=a, scale=0.96 + 0.04 * ease(t))
    d = ImageDraw.Draw(im, "RGBA")
    la = ease((t - 0.35) / 0.5)
    if la > 0:
        f = font(46, "light")
        txt = "Bilhética digital para o transporte público"
        tb = d.textbbox((0, 0), txt, font=f)
        d.text(((W - tb[2]) // 2, H // 2 + 96 + round((1 - la) * 30)), txt,
               font=f, fill=MUTED + (round(255 * la),))
        # risco azul a crescer
        lw = round((tb[2] - tb[0]) * ease((t - 0.5) / 0.5))
        if lw > 0:
            d.rounded_rectangle(((W - lw) // 2, H // 2 + 178, (W + lw) // 2, H // 2 + 184),
                                radius=3, fill=BLUE + (round(220 * la),))
    return im


def s2_problema(t: float) -> Image.Image:
    im = BG.copy()
    drift(im, CARD_TICKET, 1400, H // 2, t)
    left_block(im, t, 140, 300, "O problema de hoje",
               ["Dinheiro vivo. Filas.", "Receita que se perde."],
               ["Cada viagem paga em notas é uma viagem", "sem registo, sem controlo, sem futuro."],
               head_size=78)
    return im


def s3_solucao(t: float) -> Image.Image:
    im = BG.copy()
    drift(im, CARD_POSTER, 1395, H // 2, t)
    y_end = left_block(im, t, 140, 240, "A solução BusUp",
                       ["Pague com QR,", "cartão NFC ou", "carteira digital."],
                       ["Recargas instantâneas com"],
                       head_size=80)
    pa = ease((t - 0.38) / 0.35)
    if pa > 0:
        paste_center(im, PILL_MPESA, 140 + 136, y_end + 66, alpha=pa, scale=0.94 + 0.06 * pa)
        paste_center(im, PILL_EMOLA, 140 + 136 + 300, y_end + 66, alpha=pa, scale=0.94 + 0.06 * pa)
    return im


def s4_pos(t: float) -> Image.Image:
    im = BG.copy()
    drift(im, CARD_POS, 1400, H // 2, t)
    left_block(im, t, 140, 300, "A bordo",
               ["O agente vende.", "O motorista valida", "e inicia a viagem."],
               ["Terminais SUNMI e Urovo, com NFC,", "impressão e modo offline."],
               head_size=74)
    return im


def s5_portal(t: float) -> Image.Image:
    im = BG.copy()
    d = ImageDraw.Draw(im, "RGBA")
    ka = ease(t / 0.35)
    kicker_text(d, (W - 620) // 2 + 40, 92, "Portal do município", ka)
    ha = ease((t - 0.1) / 0.45)
    if ha > 0:
        f = font(64, "bold")
        txt = "Cada metical, visível em tempo real."
        tb = d.textbbox((0, 0), txt, font=f)
        d.text(((W - tb[2]) // 2, 138 + round((1 - ha) * 34)), txt,
               font=f, fill=WHITE + (round(255 * ha),))
    drift(im, WIN_DASH, W // 2, 640, t, rise=54)
    return im


def s6_mapa(t: float) -> Image.Image:
    im = BG.copy()
    drift(im, WIN_MAPA, 1310, 560, t, rise=54)
    left_block(im, t, 130, 330, "Para o passageiro",
               ["Os autocarros?", "No mapa, ao vivo."],
               ["Rota, viatura e velocidade,", "no telemóvel de cada passageiro."],
               head_size=70)
    return im


def s7_fecho(t: float) -> Image.Image:
    im = BG.copy()
    paste_center(im, LOGO, W // 2, 262, alpha=ease(t / 0.4), scale=0.66)
    qa = ease((t - 0.18) / 0.4)
    if qa > 0:
        card = Image.new("RGBA", (296, 296), (0, 0, 0, 0))
        dd = ImageDraw.Draw(card)
        dd.rounded_rectangle((0, 0, 296, 296), radius=26, fill=(255, 255, 255, 255))
        card.paste(QR, (30, 30))
        paste_center(im, with_shadow(card, blur=30, dy=16), W // 2, 590, alpha=qa)
    d = ImageDraw.Draw(im, "RGBA")
    ta = ease((t - 0.35) / 0.5)
    if ta > 0:
        f1 = font(56, "bold")
        txt1 = "Baixe já a aplicação"
        tb1 = d.textbbox((0, 0), txt1, font=f1)
        d.text(((W - tb1[2]) // 2, 806 + round((1 - ta) * 30)), txt1, font=f1,
               fill=WHITE + (round(255 * ta),))
        f2 = font(42, "medium")
        txt2 = "busup.updigital.co.mz"
        tb2 = d.textbbox((0, 0), txt2, font=f2)
        d.text(((W - tb2[2]) // 2, 886 + round((1 - ta) * 30)), txt2, font=f2,
               fill=BLUE2 + (round(255 * ta),))
    ua = ease((t - 0.55) / 0.4)
    if ua > 0:
        f = font(25, "light")
        label = "Powered by"
        tb = d.textbbox((0, 0), label, font=f)
        up = UP_REV.resize((round(UP_REV.width * 0.30), round(UP_REV.height * 0.30)), Image.LANCZOS)
        total_w = (tb[2] - tb[0]) + 18 + up.width
        x0 = (W - total_w) // 2
        d.text((x0, H - 88 - tb[1]), label, font=f, fill=MUTED + (round(255 * ua),))
        upa = up.copy()
        upa.putalpha(upa.getchannel("A").point(lambda v: round(v * ua)))
        im.paste(upa, (x0 + (tb[2] - tb[0]) + 18, H - 92 - up.height // 2 + 12), upa)
    return im


SCENES = [
    (s1_logo, 4.5),
    (s2_problema, 6.0),
    (s3_solucao, 7.5),
    (s4_pos, 6.5),
    (s5_portal, 7.0),
    (s6_mapa, 6.5),
    (s7_fecho, 8.0),
]


def main() -> None:
    FRAMES.mkdir(parents=True, exist_ok=True)
    for old in FRAMES.glob("f_*.jpg"):
        old.unlink()

    counts = [round(dur * FPS) for _, dur in SCENES]
    total = sum(counts)
    print(f"{len(SCENES)} cenas, {total} frames ({total / FPS:.1f}s)")

    idx = 0
    next_first: Image.Image | None = None
    for scene_i, (fn, _dur) in enumerate(SCENES):
        n = counts[scene_i]
        first_of_next = None
        for f in range(n):
            frame = fn(f / max(1, n - 1))
            if scene_i < len(SCENES) - 1 and f >= n - FADE:
                if first_of_next is None:
                    nfn, _ = SCENES[scene_i + 1]
                    first_of_next = nfn(0.0)
                k = ease((f - (n - FADE)) / FADE)
                frame = Image.blend(frame, first_of_next, min(k, 0.999))
            frame.save(FRAMES / f"f_{idx:05d}.jpg", "JPEG", quality=92)
            idx += 1
        print(f"  cena {scene_i + 1}/{len(SCENES)} ok")

    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([
        ff, "-y", "-framerate", str(FPS), "-i", str(FRAMES / "f_%05d.jpg"),
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT),
    ], check=True, capture_output=True)
    print(f"{OUT}  ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
