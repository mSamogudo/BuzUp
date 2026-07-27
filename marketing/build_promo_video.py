#!/usr/bin/env python3
"""Video promocional BusUp v3 — broadcast-ready.

- 25 fps (PAL/TV), frames PNG sem perdas, encode CRF 16
- gravacoes REAIS das apps (POS do motorista + mapa com autocarro em
  movimento) capturadas no emulador, em moldura de telemovel
- cena do problema em tipografia cinetica; composicoes alternadas;
  marca de agua; fecho com contacto
- narracao pt-PT (voz Joana do macOS) mixada; sem musica (adicionar
  faixa licenciada quando existir)

Saidas: marketing/BusUp-Promo.mp4 (~48s) e marketing/BusUp-Promo-TV30.mp4 (30s)

Requisitos: frames das gravacoes ja extraidos (ffmpeg fps=25) em
REC_POS_DIR / REC_MAP_DIR — ver constantes abaixo.
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
SCRATCH = Path("/private/tmp/claude-501/-Users-marioabcina-Dev-Projects-BuzUp/cfd47f12-2cfa-4c29-9fb5-f1db97a65d24/scratchpad")
REC_POS_DIR = SCRATCH / "rec_pos"
REC_MAP_DIR = SCRATCH / "rec_map"

W, H = 1920, 1080
FPS = 25
FADE = 13

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
    t = min(max(t, 0.0), 1.0)
    return 4 * t * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 3) / 2


def navy_bg() -> Image.Image:
    im = Image.new("RGB", (W, H), NAVY)
    glow = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(glow)
    d.ellipse((W * 0.58, -H * 0.45, W * 1.4, H * 0.72), fill=64)
    d.ellipse((-W * 0.28, H * 0.55, W * 0.38, H * 1.5), fill=42)
    glow = glow.filter(ImageFilter.GaussianBlur(190))
    blue = Image.new("RGB", (W, H), (24, 66, 124))
    return Image.composite(blue, im, glow)


def load(path: Path, max_w: int = 2600, crop: tuple[int, int, int, int] | None = None) -> Image.Image:
    """Corta PRIMEIRO (coords do original), so depois reduz."""
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
    w = round(im.width * height / im.height)
    card = rounded(im.resize((w, height), Image.LANCZOS), radius)
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, w - 1, height - 1), radius=radius,
                        outline=(255, 255, 255, 46), width=2)
    return card


def browser_window(shot: Image.Image, width: int, url: str) -> Image.Image:
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
    return rounded(win.convert("RGB"), 22)


def phone_frame(screen: Image.Image, height: int) -> Image.Image:
    """Gravacao de ecra (1080x2400) numa moldura de telemovel minimalista."""
    bezel = 16
    sw = round(screen.width * (height - 2 * bezel) / screen.height)
    sh = height - 2 * bezel
    scr = rounded(screen.resize((sw, sh), Image.LANCZOS), 34)
    ph = Image.new("RGBA", (sw + 2 * bezel, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(ph)
    d.rounded_rectangle((0, 0, ph.width, ph.height), radius=50, fill=(14, 22, 36, 255))
    d.rounded_rectangle((1, 1, ph.width - 2, ph.height - 2), radius=50,
                        outline=(255, 255, 255, 56), width=2)
    ph.paste(scr, (bezel, bezel), scr)
    # ilha da camara
    d.rounded_rectangle((ph.width // 2 - 52, bezel + 10, ph.width // 2 + 52, bezel + 30),
                        radius=10, fill=(14, 22, 36, 255))
    return ph


def with_shadow(art: Image.Image, blur: int = 42, dy: int = 26, alpha: int = 120) -> Image.Image:
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
          appear: float = 0.4, rise: int = 40, s0: float = 0.99, s1: float = 1.01) -> None:
    a = ease(t / appear)
    s = s0 + (s1 - s0) * ease(t)
    paste_center(im, art, cx, cy + round((1 - a) * rise), alpha=a, scale=s)


def kicker_text(d: ImageDraw.ImageDraw, x: int, y: int, txt: str, alpha: float) -> None:
    d.text((x, y), " ".join(txt.upper()), font=font(27, "medium"),
           fill=BLUE2 + (round(255 * alpha),))


def left_block(im: Image.Image, t: float, x: int, y: int, kicker: str,
               head_lines: list[str], sub_lines: list[str],
               head_size: int = 76, sub_size: int = 42) -> int:
    d = ImageDraw.Draw(im, "RGBA")
    ka = ease(t / 0.3)
    if ka > 0:
        kicker_text(d, x, y + round((1 - ka) * 24), kicker, ka)
    yy = y + 64
    fh = font(head_size, "bold")
    for i, line in enumerate(head_lines):
        la = ease((t - 0.1 - i * 0.08) / 0.4)
        if la > 0:
            d.text((x, yy + round((1 - la) * 40)), line, font=fh, fill=WHITE + (round(255 * la),))
        yy += round(head_size * 1.18)
    yy += 22
    fs = font(sub_size, "light")
    for i, line in enumerate(sub_lines):
        la = ease((t - 0.3 - i * 0.08) / 0.4)
        if la > 0:
            d.text((x, yy + round((1 - la) * 34)), line, font=fs, fill=MUTED + (round(255 * la),))
        yy += round(sub_size * 1.42)
    return yy


def watermark(im: Image.Image) -> None:
    lg = LOGO_SMALL.copy()
    lg.putalpha(lg.getchannel("A").point(lambda v: round(v * 0.4)))
    im.paste(lg, (W - lg.width - 46, H - lg.height - 38), lg)


def pill(width: int, height: int, color: tuple, logo: Image.Image) -> Image.Image:
    im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, width, height), radius=height // 4, fill=color + (255,))
    lg = logo.copy()
    lh = round(height * 0.5)
    lg = lg.resize((round(lg.width * lh / lg.height), lh), Image.LANCZOS)
    im.paste(lg, ((width - lg.width) // 2, (height - lg.height) // 2), lg)
    return im


def rec_frame(dirn: Path, prefix: str, n: int, n_max: int) -> Image.Image:
    n = min(max(n, 1), n_max)
    return Image.open(dirn / f"{prefix}_{n:04d}.jpg").convert("RGB")


# ----------------------------------------------------------------------------
# Assets
# ----------------------------------------------------------------------------
print("a carregar assets...")
LOGO = load_rgba(ASSETS / "logo_dark.png", 860)
LOGO_SMALL = load_rgba(ASSETS / "logo_dark.png", 190)
UP_REV = load_rgba(ASSETS / "up_full_rev.png", 340)
POSTER = load(ROOT / "ChatGPT Image Jul 16, 2026, 01_43_54 PM (4).png", crop=(0, 172, 1003, 1224))
DASH = load(ROOT / "shots/portal_dashboard.png", crop=(0, 0, 3012, 1500))
MPESA = load_rgba(ASSETS / "pay_mpesa.png", 300)
EMOLA = load_rgba(ASSETS / "pay_emola.png", 300)
qr_data = (ROOT / "qr.b64.txt").read_text().strip()
qr_b64 = qr_data.split(",", 1)[1] if qr_data.startswith("data:") else qr_data
QR = Image.open(io.BytesIO(base64.b64decode(qr_b64))).convert("RGB").resize((236, 236), Image.LANCZOS)

BG = navy_bg()
CARD_POSTER = with_shadow(photo_card(POSTER, 860, radius=28))
WIN_DASH = with_shadow(browser_window(DASH, 1460, "busup.updigital.co.mz/app"), blur=48, dy=30)
PILL_MPESA = pill(272, 88, (230, 0, 0), MPESA)
PILL_EMOLA = pill(272, 88, (245, 130, 31), EMOLA)

N_POS = len(list(REC_POS_DIR.glob("p_*.jpg")))
N_MAP = len(list(REC_MAP_DIR.glob("m_*.jpg")))
print(f"gravacoes: pos={N_POS} frames, map={N_MAP} frames")

# guiao das gravacoes (frames 25fps da captura):
# POS: 430-470 login preenchido | 520-1240 home motorista | 1245-1279 -> Minhas viagens
POS_SCRIPT: list[int] = (
    list(range(430, 472))                 # login
    + list(range(520, 700, 2))            # home (ligeiro speed-up)
    + list(range(1246, 1280))             # transicao + minhas viagens
)
PHONE_H = 900


def pos_screen(t: float) -> Image.Image:
    i = round(t * (len(POS_SCRIPT) - 1))
    n = POS_SCRIPT[i]
    return rec_frame(REC_POS_DIR, "p", n, N_POS)


def map_screen(t: float) -> Image.Image:
    # 8x: 72s de captura em ~9s de cena — o autocarro desliza pela cidade
    n = 450 + round(t * 1800)
    return rec_frame(REC_MAP_DIR, "m", n, N_MAP)


# ----------------------------------------------------------------------------
# Cenas
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
        lw = round((tb[2] - tb[0]) * ease((t - 0.5) / 0.5))
        if lw > 0:
            d.rounded_rectangle(((W - lw) // 2, H // 2 + 178, (W + lw) // 2, H // 2 + 184),
                                radius=3, fill=BLUE + (round(220 * la),))
    return im


def s2_problema(t: float) -> Image.Image:
    """Tipografia cinetica: as tres dores, uma a uma, depois a virada."""
    im = BG.copy()
    d = ImageDraw.Draw(im, "RGBA")
    words = [("Dinheiro vivo.", 0.02), ("Filas.", 0.2), ("Receita que se perde.", 0.38)]
    f = font(96, "bold")
    total_h = 3 * round(96 * 1.34)
    y = (H - total_h) // 2 - 60
    for txt, t0 in words:
        la = ease((t - t0) / 0.28)
        if la > 0:
            tb = d.textbbox((0, 0), txt, font=f)
            s = 0.94 + 0.06 * la
            fs = font(round(96 * s), "bold")
            tb2 = d.textbbox((0, 0), txt, font=fs)
            d.text(((W - tb2[2]) // 2, y), txt, font=fs, fill=WHITE + (round(255 * la),))
        y += round(96 * 1.34)
    va = ease((t - 0.62) / 0.3)
    if va > 0:
        f2 = font(52, "light")
        txt = "Há uma forma melhor de viajar."
        tb = d.textbbox((0, 0), txt, font=f2)
        d.text(((W - tb[2]) // 2, y + 34 + round((1 - va) * 30)), txt,
               font=f2, fill=BLUE2 + (round(255 * va),))
        lw = round(560 * ease((t - 0.72) / 0.28))
        if lw > 0:
            d.rounded_rectangle(((W - lw) // 2, y + 130, (W + lw) // 2, y + 136),
                                radius=3, fill=BLUE + (200,))
    watermark(im)
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
    watermark(im)
    return im


def s4_pos_live(t: float) -> Image.Image:
    """Gravacao REAL da app POS (motorista): telefone a esquerda, texto a direita."""
    im = BG.copy()
    ph = with_shadow(phone_frame(pos_screen(t), PHONE_H), blur=40, dy=24)
    drift(im, ph, 470, H // 2, t, rise=46)
    left_block(im, t, 900, 300, "A bordo — app real",
               ["O agente vende.", "O motorista valida", "e inicia a viagem."],
               ["Terminais SUNMI e Urovo,", "com NFC e impressão."],
               head_size=72)
    watermark(im)
    return im


def s5_portal(t: float) -> Image.Image:
    im = BG.copy()
    d = ImageDraw.Draw(im, "RGBA")
    ka = ease(t / 0.3)
    kicker_text(d, 652, 92, "Portal do município", ka)
    ha = ease((t - 0.08) / 0.4)
    if ha > 0:
        f = font(64, "bold")
        txt = "Cada metical, visível em tempo real."
        tb = d.textbbox((0, 0), txt, font=f)
        d.text(((W - tb[2]) // 2, 138 + round((1 - ha) * 34)), txt,
               font=f, fill=WHITE + (round(255 * ha),))
    drift(im, WIN_DASH, W // 2, 640, t, rise=54)
    watermark(im)
    return im


def s6_mapa_live(t: float) -> Image.Image:
    """Gravacao REAL do mapa com o autocarro em movimento (8x)."""
    im = BG.copy()
    ph = with_shadow(phone_frame(map_screen(t), PHONE_H), blur=40, dy=24)
    drift(im, ph, 1450, H // 2, t, rise=46)
    y_end = left_block(im, t, 140, 300, "Para o passageiro — em directo",
                       ["Os autocarros?", "No mapa, ao vivo."],
                       ["Rota, viatura e velocidade,", "no telemóvel de cada passageiro."],
                       head_size=72)
    ba = ease((t - 0.45) / 0.35)
    if ba > 0:
        d = ImageDraw.Draw(im, "RGBA")
        chip = "GPS real do terminal a bordo"
        f = font(30, "medium")
        tb = d.textbbox((0, 0), chip, font=f)
        x0, y0 = 140, y_end + 40
        d.rounded_rectangle((x0, y0, x0 + tb[2] + 56, y0 + tb[3] + 34), radius=14,
                            outline=BLUE + (round(200 * ba),), width=2)
        d.ellipse((x0 + 20, y0 + (tb[3] + 34) // 2 - 7, x0 + 34, y0 + (tb[3] + 34) // 2 + 7),
                  fill=(46, 200, 120, round(255 * ba)))
        d.text((x0 + 48, y0 + 15), chip, font=f, fill=WHITE + (round(255 * ba),))
    watermark(im)
    return im


def s7_fecho(t: float) -> Image.Image:
    im = BG.copy()
    paste_center(im, LOGO, W // 2, 240, alpha=ease(t / 0.4), scale=0.62)
    qa = ease((t - 0.15) / 0.4)
    if qa > 0:
        card = Image.new("RGBA", (296, 296), (0, 0, 0, 0))
        dd = ImageDraw.Draw(card)
        dd.rounded_rectangle((0, 0, 296, 296), radius=26, fill=(255, 255, 255, 255))
        card.paste(QR, (30, 30))
        paste_center(im, with_shadow(card, blur=30, dy=16), W // 2, 545, alpha=qa)
    d = ImageDraw.Draw(im, "RGBA")
    ta = ease((t - 0.3) / 0.45)
    if ta > 0:
        for txt, f, y, col in [
            ("Baixe já a aplicação", font(54, "bold"), 756, WHITE),
            ("busup.updigital.co.mz", font(42, "medium"), 832, BLUE2),
            ("+258 86 693 0017  ·  comercial@updigital.co.mz", font(32, "light"), 902, MUTED),
        ]:
            tb = d.textbbox((0, 0), txt, font=f)
            d.text(((W - tb[2]) // 2, y + round((1 - ta) * 26)), txt, font=f,
                   fill=col + (round(255 * ta),))
    ua = ease((t - 0.5) / 0.4)
    if ua > 0:
        f = font(25, "light")
        label = "Powered by"
        tb = d.textbbox((0, 0), label, font=f)
        up = UP_REV.resize((round(UP_REV.width * 0.30), round(UP_REV.height * 0.30)), Image.LANCZOS)
        total_w = (tb[2] - tb[0]) + 18 + up.width
        x0 = (W - total_w) // 2
        d.text((x0, H - 82 - tb[1]), label, font=f, fill=MUTED + (round(255 * ua),))
        upa = up.copy()
        upa.putalpha(upa.getchannel("A").point(lambda v: round(v * ua)))
        im.paste(upa, (x0 + (tb[2] - tb[0]) + 18, H - 86 - up.height // 2 + 12), upa)
    return im


# (funcao, duracao_full_s, duracao_tv_s, linha de narracao | None)
SCENES = [
    (s1_logo, 4.5, 3.0, None),
    (s2_problema, 6.0, 4.5, "Dinheiro vivo. Filas. Receita que se perde."),
    (s3_solucao, 7.0, 5.0, "Com o BusUp, paga-se com QR, cartão NFC ou carteira digital."),
    (s4_pos_live, 8.5, 5.5, "O agente vende. O motorista valida e inicia a viagem."),
    (s5_portal, 6.5, 4.5, "E o município vê cada metical, em tempo real."),
    (s6_mapa_live, 9.0, 4.5, "Os autocarros? No mapa, ao vivo."),
    (s7_fecho, 8.0, 3.0, "BusUp. Baixe já em busup ponto updigital ponto co ponto mz."),
]


def render(durations: list[float], out: Path, vo: bool) -> None:
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()

    FRAMES.mkdir(parents=True, exist_ok=True)
    for old in FRAMES.glob("f_*.png"):
        old.unlink()

    counts = [round(dur * FPS) for dur in durations]
    total = sum(counts)
    print(f"{out.name}: {len(SCENES)} cenas, {total} frames ({total / FPS:.1f}s)")

    idx = 0
    for scene_i, (fn, *_rest) in enumerate(SCENES):
        n = counts[scene_i]
        first_of_next = None
        for f in range(n):
            frame = fn(f / max(1, n - 1))
            if scene_i < len(SCENES) - 1 and f >= n - FADE:
                if first_of_next is None:
                    first_of_next = SCENES[scene_i + 1][0](0.0)
                k = ease((f - (n - FADE)) / FADE)
                frame = Image.blend(frame, first_of_next, min(k, 0.999))
            frame.save(FRAMES / f"f_{idx:05d}.png")
            idx += 1
        print(f"  cena {scene_i + 1}/{len(SCENES)} ok")

    video_args = [
        ff, "-y", "-framerate", str(FPS), "-i", str(FRAMES / "f_%05d.png"),
    ]
    if vo:
        wav = build_voiceover(durations)
        video_args += ["-i", str(wav)]
    video_args += [
        "-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    ]
    if vo:
        video_args += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    video_args += [str(out)]
    subprocess.run(video_args, check=True, capture_output=True)
    print(f"{out}  ({out.stat().st_size / 1e6:.1f} MB)")


def build_voiceover(durations: list[float]) -> Path:
    """Narracao pt-PT (voz Joana) alinhada ao inicio de cada cena (+0.4s)."""
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()

    total = sum(durations)
    mix_inputs = []
    filters = []
    starts = []
    acc = 0.0
    for dur in durations:
        starts.append(acc)
        acc += dur

    n = 0
    for i, (_fn, _df, _dt, line) in enumerate(SCENES):
        if not line:
            continue
        aiff = SCRATCH / f"vo_{i}.aiff"
        subprocess.run(["say", "-v", "Joana", "-o", str(aiff), line], check=True)
        delay_ms = round((starts[i] + 0.4) * 1000)
        mix_inputs += ["-i", str(aiff)]
        filters.append(f"[{n}:a]adelay={delay_ms}|{delay_ms},volume=1.0[a{n}]")
        n += 1

    amix = "".join(f"[a{k}]" for k in range(n)) + f"amix=inputs={n}:normalize=0[vo]"
    graph = ";".join(filters + [amix,
        f"[vo]apad=whole_dur={total},loudnorm=I=-18:TP=-1.5:LRA=11[out]"])
    wav = SCRATCH / "vo_mix.wav"
    subprocess.run([ff, "-y", *mix_inputs, "-filter_complex", graph,
                    "-map", "[out]", "-ar", "48000", str(wav)],
                   check=True, capture_output=True)
    return wav


if __name__ == "__main__":
    render([d for _f, d, _t, _l in SCENES], ROOT / "BusUp-Promo.mp4", vo=True)
    render([t for _f, _d, t, _l in SCENES], ROOT / "BusUp-Promo-TV30.mp4", vo=True)
