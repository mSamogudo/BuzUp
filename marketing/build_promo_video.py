#!/usr/bin/env python3
"""Video promocional BusUp (motion design, ~42s, 1080p30).

Gera frames deterministicos com PIL sobre os assets reais do deck (fotos de
produto, capturas do portal, logos oficiais) e monta o MP4 com o ffmpeg do
imageio-ffmpeg. Sem dependencias de video externas.

Uso: backend/.venv312/bin/python marketing/build_promo_video.py
Saida: marketing/BusUp-Promo.mp4
"""

from __future__ import annotations

import base64
import io
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "deck_assets"
FRAMES = ROOT / "premium_export" / "promo_frames"
OUT = ROOT / "BusUp-Promo.mp4"

W, H = 1920, 1080
FPS = 30
FADE = 15  # frames de crossfade entre cenas

NAVY = (10, 22, 40)
NAVY2 = (13, 40, 73)
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
    """Fundo navy com glow radial azul (mesma linguagem do deck)."""
    im = Image.new("RGB", (W, H), NAVY)
    glow = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(glow)
    d.ellipse((W * 0.55, -H * 0.4, W * 1.35, H * 0.7), fill=70)
    d.ellipse((-W * 0.25, H * 0.55, W * 0.35, H * 1.45), fill=45)
    glow = glow.filter(ImageFilter.GaussianBlur(180))
    blue = Image.new("RGB", (W, H), (26, 70, 130))
    return Image.composite(blue, im, glow)


def load(path: Path, max_w: int = 2400) -> Image.Image:
    im = Image.open(path).convert("RGB")
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


def ken_burns(src: Image.Image, t: float, z0: float, z1: float,
              c0: tuple[float, float], c1: tuple[float, float]) -> Image.Image:
    """Zoom/pan continuo: z = fraccao da imagem visivel; c = centro (0..1)."""
    z = z0 + (z1 - z0) * t
    cx = c0[0] + (c1[0] - c0[0]) * t
    cy = c0[1] + (c1[1] - c0[1]) * t
    # janela com aspecto 16:9 dentro da imagem
    win_w = src.width * z
    win_h = win_w * H / W
    if win_h > src.height:
        win_h = src.height * z
        win_w = win_h * W / H
    x = cx * src.width - win_w / 2
    y = cy * src.height - win_h / 2
    x = min(max(x, 0), src.width - win_w)
    y = min(max(y, 0), src.height - win_h)
    return src.crop((round(x), round(y), round(x + win_w), round(y + win_h))).resize((W, H), Image.BILINEAR)


def darken(im: Image.Image, top: float = 0.35, bottom: float = 0.65) -> Image.Image:
    """Gradiente escuro vertical para legibilidade do texto."""
    mask = Image.new("L", (1, H))
    for y in range(H):
        a = top + (bottom - top) * (y / H)
        mask.putpixel((0, y), round(a * 255))
    mask = mask.resize((W, H))
    return Image.composite(Image.new("RGB", (W, H), (4, 10, 20)), im, mask)


def text_block(im: Image.Image, lines: list[tuple[str, ImageFont.FreeTypeFont, tuple]],
               t: float, cx: int = W // 2, base_y: int | None = None,
               stagger: float = 0.18, rise: int = 46, align: str = "center") -> None:
    """Linhas com fade+subida em cascata. t: progresso 0..1 da cena."""
    d = ImageDraw.Draw(im, "RGBA")
    heights = []
    for txt, f, _ in lines:
        box = d.textbbox((0, 0), txt, font=f)
        heights.append(box[3] - box[1] + 18)
    total = sum(heights)
    y = (H - total) // 2 if base_y is None else base_y
    for i, (txt, f, color) in enumerate(lines):
        lt = ease((t - i * stagger) / max(1e-6, 0.5))
        if lt <= 0:
            y += heights[i]
            continue
        box = d.textbbox((0, 0), txt, font=f)
        tw = box[2] - box[0]
        x = (W - tw) // 2 if align == "center" else cx
        d.text((x, y + (1 - lt) * rise - box[1]), txt, font=f,
               fill=color + (round(255 * lt),))
        y += heights[i]


def paste_center(im: Image.Image, art: Image.Image, cx: int, cy: int, alpha: float = 1.0, scale: float = 1.0) -> None:
    a = art
    if scale != 1.0:
        a = art.resize((max(1, round(art.width * scale)), max(1, round(art.height * scale))), Image.LANCZOS)
    if alpha < 1.0:
        a = a.copy()
        a.putalpha(a.getchannel("A").point(lambda v: round(v * alpha)))
    im.paste(a, (cx - a.width // 2, cy - a.height // 2), a)


def pill(width: int, height: int, color: tuple, logo: Image.Image) -> Image.Image:
    im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, width, height), radius=height // 4, fill=color + (255,))
    lg = logo.copy()
    lh = round(height * 0.52)
    lg = lg.resize((round(lg.width * lh / lg.height), lh), Image.LANCZOS)
    im.paste(lg, ((width - lg.width) // 2, (height - lg.height) // 2), lg)
    return im


# ----------------------------------------------------------------------------
# Assets
# ----------------------------------------------------------------------------
print("a carregar assets...")
LOGO = load_rgba(ASSETS / "logo_dark.png", 900)
UP_REV = load_rgba(ASSETS / "up_full_rev.png", 340)
POSTER = load(ROOT / "ChatGPT Image Jul 16, 2026, 01_43_54 PM (4).png").crop((0, 172, 1003, 1224))
TICKET = load(ROOT / "premium_assets/ticket_qr_phone_hand_bus_final_4x5.png")
POS = load(ROOT / "premium_assets/pos_terminal_payment_final_4x5.png")
DASH = load(ROOT / "shots/portal_dashboard.png").crop((0, 0, 3012, 1500))
MAPA = load(ROOT / "shots/portal_mapa.png").crop((548, 500, 3012, 1490))
MPESA = load_rgba(ASSETS / "pay_mpesa.png", 300)
EMOLA = load_rgba(ASSETS / "pay_emola.png", 300)
qr_data = (ROOT / "qr.b64.txt").read_text().strip()
qr_b64 = qr_data.split(",", 1)[1] if qr_data.startswith("data:") else qr_data
QR = Image.open(io.BytesIO(base64.b64decode(qr_b64))).convert("RGB").resize((240, 240), Image.LANCZOS)

PILL_MPESA = pill(300, 96, (230, 0, 0), MPESA)
PILL_EMOLA = pill(300, 96, (245, 130, 31), EMOLA)
BG = navy_bg()


# ----------------------------------------------------------------------------
# Cenas: cada uma recebe t (0..1) e devolve um frame 1920x1080
# ----------------------------------------------------------------------------

def s1_logo(t: float) -> Image.Image:
    im = BG.copy()
    a = ease(t / 0.45)
    paste_center(im, LOGO, W // 2, H // 2 - 60, alpha=a, scale=0.92 + 0.08 * ease(t))
    text_block(im, [
        ("Bilhética digital para o transporte público", font(52, "light"), MUTED),
    ], ease((t - 0.35) / 0.5), base_y=H // 2 + 90)
    return im


def s2_problema(t: float) -> Image.Image:
    im = darken(ken_burns(TICKET, ease(t), 0.92, 0.72, (0.5, 0.42), (0.46, 0.34)), 0.45, 0.7)
    text_block(im, [
        ("Dinheiro vivo. Filas. Receita que se perde.", font(74, "bold"), WHITE),
        ("Há uma forma melhor de viajar.", font(52, "light"), BLUE2),
    ], t, base_y=H - 340)
    return im


def s3_solucao(t: float) -> Image.Image:
    im = darken(ken_burns(POSTER, ease(t), 0.98, 0.8, (0.5, 0.42), (0.52, 0.5)), 0.30, 0.62)
    text_block(im, [
        ("Pague com QR, cartão NFC", font(78, "bold"), WHITE),
        ("ou carteira digital.", font(78, "bold"), WHITE),
    ], t, base_y=H - 400)
    pa = ease((t - 0.5) / 0.4)
    if pa > 0:
        paste_center(im, PILL_MPESA, W // 2 - 170, H - 110, alpha=pa, scale=0.9 + 0.1 * pa)
        paste_center(im, PILL_EMOLA, W // 2 + 170, H - 110, alpha=pa, scale=0.9 + 0.1 * pa)
    return im


def s4_pos(t: float) -> Image.Image:
    im = darken(ken_burns(POS, ease(t), 0.9, 0.7, (0.5, 0.5), (0.55, 0.42)), 0.32, 0.6)
    text_block(im, [
        ("O agente vende no terminal.", font(72, "bold"), WHITE),
        ("O motorista inicia a viagem e valida.", font(56, "light"), BLUE2),
    ], t, base_y=H - 330)
    return im


def s5_portal(t: float) -> Image.Image:
    im = darken(ken_burns(DASH, ease(t), 0.9, 0.62, (0.4, 0.35), (0.6, 0.55)), 0.4, 0.64)
    text_block(im, [
        ("O município vê tudo — em tempo real.", font(72, "bold"), WHITE),
        ("Receita, rotas, frota e auditoria ao cêntimo.", font(52, "light"), BLUE2),
    ], t, base_y=H - 320)
    return im


def s6_mapa(t: float) -> Image.Image:
    # pan mantem-se sobre a cidade (a metade direita da captura e mar)
    im = darken(ken_burns(MAPA, ease(t), 0.85, 0.6, (0.28, 0.45), (0.42, 0.58)), 0.38, 0.62)
    text_block(im, [
        ("E os autocarros? No mapa, ao vivo.", font(72, "bold"), WHITE),
        ("Cada passageiro segue a sua viatura no telemóvel.", font(50, "light"), BLUE2),
    ], t, base_y=H - 320)
    return im


def s7_fecho(t: float) -> Image.Image:
    im = BG.copy()
    paste_center(im, LOGO, W // 2, 300, alpha=ease(t / 0.4), scale=0.7)
    qa = ease((t - 0.2) / 0.4)
    if qa > 0:
        card = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
        d = ImageDraw.Draw(card)
        d.rounded_rectangle((0, 0, 300, 300), radius=26, fill=(255, 255, 255, 255))
        card.paste(QR, (30, 30))
        paste_center(im, card, W // 2, 620, alpha=qa)
    text_block(im, [
        ("Baixe já a aplicação", font(58, "bold"), WHITE),
        ("busup.updigital.co.mz", font(46, "medium"), BLUE2),
    ], ease((t - 0.35) / 0.5), base_y=820)
    ua = ease((t - 0.55) / 0.4)
    if ua > 0:
        d = ImageDraw.Draw(im, "RGBA")
        f = font(26, "light")
        label = "Powered by"
        box = d.textbbox((0, 0), label, font=f)
        up = UP_REV.resize((round(UP_REV.width * 0.32), round(UP_REV.height * 0.32)), Image.LANCZOS)
        total_w = (box[2] - box[0]) + 18 + up.width
        x0 = (W - total_w) // 2
        d.text((x0, H - 96 - box[1]), label, font=f, fill=MUTED + (round(255 * ua),))
        upa = up.copy()
        upa.putalpha(upa.getchannel("A").point(lambda v: round(v * ua)))
        im.paste(upa, (x0 + (box[2] - box[0]) + 18, H - 96 - up.height // 2 + 10), upa)
    return im


SCENES = [
    (s1_logo, 4.0),
    (s2_problema, 5.0),
    (s3_solucao, 7.0),
    (s4_pos, 6.0),
    (s5_portal, 6.0),
    (s6_mapa, 6.0),
    (s7_fecho, 8.0),
]


def main() -> None:
    FRAMES.mkdir(parents=True, exist_ok=True)
    for old in FRAMES.glob("f_*.jpg"):
        old.unlink()

    # timeline com crossfades
    counts = [round(dur * FPS) for _, dur in SCENES]
    total = sum(counts)
    print(f"{len(SCENES)} cenas, {total} frames ({total / FPS:.1f}s)")

    idx = 0
    starts = []
    acc = 0
    for c in counts:
        starts.append(acc)
        acc += c

    cache: dict[tuple[int, int], Image.Image] = {}

    def render(scene_i: int, local_f: int) -> Image.Image:
        key = (scene_i, local_f)
        if key not in cache:
            fn, _ = SCENES[scene_i]
            cache.clear() if len(cache) > 4 else None
            cache[key] = fn(local_f / max(1, counts[scene_i] - 1))
        return cache[key]

    for scene_i, (fn, _dur) in enumerate(SCENES):
        n = counts[scene_i]
        for f in range(n):
            frame = render(scene_i, f)
            # crossfade com a cena seguinte nos ultimos FADE frames
            if scene_i < len(SCENES) - 1 and f >= n - FADE:
                k = (f - (n - FADE)) / FADE
                nxt = render(scene_i + 1, 0)
                frame = Image.blend(frame, nxt, ease(k) * 0.999)
            frame.save(FRAMES / f"f_{idx:05d}.jpg", "JPEG", quality=90)
            idx += 1
        print(f"  cena {scene_i + 1}/{len(SCENES)} ok")

    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([
        ff, "-y", "-framerate", str(FPS), "-i", str(FRAMES / "f_%05d.jpg"),
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT),
    ], check=True, capture_output=True)
    print(f"{OUT}  ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
