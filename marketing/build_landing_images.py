#!/usr/bin/env python3
"""Imagens da landing compostas a partir do PRODUTO REAL.

Em vez de ilustração genérica, cada imagem é um enquadramento do que o
sistema faz mesmo: ecrãs reais das apps (gravados no emulador), capturas do
portal e o bilhete PDF renderizado. Fundo navy da marca + sombra suave, para
que as secções da landing sejam lidas por imagem e não por texto.

Uso: backend/.venv312/bin/python marketing/build_landing_images.py
Saída: frontend/public/landing/*.webp
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
OUT = PROJECT / "frontend/public/landing"
SCRATCH = Path("/private/tmp/claude-501/-Users-marioabcina-Dev-Projects-BuzUp"
               "/cfd47f12-2cfa-4c29-9fb5-f1db97a65d24/scratchpad")
REC_POS = SCRATCH / "rec_pos"
REC_MAP = SCRATCH / "rec_map"

NAVY = (11, 30, 56)
BLUE = (45, 140, 240)


def canvas(w: int, h: int) -> Image.Image:
    """Fundo navy com glow azul — mesma linguagem do deck e do vídeo."""
    im = Image.new("RGB", (w, h), NAVY)
    glow = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(glow)
    d.ellipse((w * 0.52, -h * 0.5, w * 1.3, h * 0.75), fill=70)
    d.ellipse((-w * 0.25, h * 0.5, w * 0.4, h * 1.5), fill=44)
    glow = glow.filter(ImageFilter.GaussianBlur(int(w * 0.09)))
    return Image.composite(Image.new("RGB", (w, h), (26, 72, 132)), im, glow)


def rounded(im: Image.Image, r: int) -> Image.Image:
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *im.size), radius=r, fill=255)
    out = im.convert("RGBA")
    out.putalpha(mask)
    return out


def shadow(art: Image.Image, blur: int = 34, dy: int = 20, alpha: int = 118) -> Image.Image:
    pad = blur * 2
    cv = Image.new("RGBA", (art.width + pad * 2, art.height + pad * 2 + dy), (0, 0, 0, 0))
    sh = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    black = Image.new("RGBA", art.size, (0, 0, 0, 255))
    black.putalpha(art.getchannel("A").point(lambda v: min(v, alpha)))
    sh.paste(black, (pad, pad + dy), black)
    cv.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    cv.alpha_composite(art, (pad, pad))
    return cv


def phone(screen: Image.Image, height: int) -> Image.Image:
    """Ecrã real dentro de uma moldura de telemóvel minimalista."""
    bezel = 13
    sh = height - 2 * bezel
    sw = round(screen.width * sh / screen.height)
    scr = rounded(screen.resize((sw, sh), Image.LANCZOS), 26)
    ph = Image.new("RGBA", (sw + 2 * bezel, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(ph)
    d.rounded_rectangle((0, 0, ph.width, ph.height), radius=40, fill=(16, 26, 42, 255))
    d.rounded_rectangle((1, 1, ph.width - 2, ph.height - 2), radius=40,
                        outline=(255, 255, 255, 58), width=2)
    ph.paste(scr, (bezel, bezel), scr)
    d.rounded_rectangle((ph.width // 2 - 44, bezel + 8, ph.width // 2 + 44, bezel + 26),
                        radius=9, fill=(16, 26, 42, 255))
    return ph


def browser(shot: Image.Image, width: int, url: str) -> Image.Image:
    bar = 46
    sw = width
    sh_ = round(shot.height * sw / shot.width)
    win = Image.new("RGBA", (sw, sh_ + bar), (0, 0, 0, 0))
    d = ImageDraw.Draw(win)
    d.rounded_rectangle((0, 0, sw, sh_ + bar), radius=18, fill=(17, 33, 56, 255))
    for i, c in enumerate([(255, 96, 92), (255, 189, 68), (0, 202, 78)]):
        d.ellipse((20 + i * 26, bar // 2 - 6, 32 + i * 26, bar // 2 + 6), fill=c)
    d.rounded_rectangle((sw // 2 - 150, 10, sw // 2 + 150, bar - 10), radius=13, fill=(29, 54, 88, 255))
    win.paste(rounded(shot.resize((sw, sh_), Image.LANCZOS), 1), (0, bar))
    return rounded(win.convert("RGB"), 18)


def place(bg: Image.Image, art: Image.Image, cx: int, cy: int, scale: float = 1.0) -> None:
    a = art if scale == 1.0 else art.resize(
        (round(art.width * scale), round(art.height * scale)), Image.LANCZOS)
    bg.paste(a, (cx - a.width // 2, cy - a.height // 2), a)


def save(im: Image.Image, name: str, quality: int = 82) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    im.save(path, "WEBP", quality=quality, method=6)
    print(f"  {name}  {im.size[0]}x{im.size[1]}  {path.stat().st_size // 1024} KB")


def rec(dirn: Path, prefix: str, n: int) -> Image.Image:
    return Image.open(dirn / f"{prefix}_{n:04d}.jpg").convert("RGB")


def ticket_render() -> Image.Image:
    """Renderiza o PDF do bilhete de demonstração para imagem."""
    pdf = SCRATCH / "ticket_demo.pdf"
    png = SCRATCH / "ticket_demo_hi"
    subprocess.run(["/opt/homebrew/bin/pdftoppm", "-png", "-r", "150", "-singlefile",
                    str(pdf), str(png)], check=True, capture_output=True)
    return Image.open(f"{png}.png").convert("RGB")


def animate(frames: list[Image.Image], name: str, fps: int = 12, quality: int = 62) -> None:
    """WebP animado (mais leve que GIF e funciona em <img>).

    Usa gravações reais do produto — o autocarro a andar no mapa é mesmo o
    nosso GPS, não uma animação inventada.
    """
    import imageio_ffmpeg

    tmp = SCRATCH / f"anim_{name}"
    tmp.mkdir(parents=True, exist_ok=True)
    for old in tmp.glob("*.png"):
        old.unlink()
    for i, fr in enumerate(frames):
        fr.save(tmp / f"f_{i:04d}.png")

    out = OUT / name
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([
        ff, "-y", "-framerate", str(fps), "-i", str(tmp / "f_%04d.png"),
        "-vcodec", "libwebp", "-lossless", "0", "-q:v", str(quality),
        "-loop", "0", "-preset", "picture", "-an", "-vsync", "0", str(out),
    ], check=True, capture_output=True)
    print(f"  {name}  {frames[0].size[0]}x{frames[0].size[1]}  {len(frames)} frames  "
          f"{out.stat().st_size // 1024} KB")


def anim_scene(get_frame, indices: list[int], w: int, h: int, phone_h: int, cx: int, cy: int) -> list[Image.Image]:
    base = canvas(w, h)
    out = []
    for n in indices:
        fr = base.copy()
        place(fr, shadow(phone(get_frame(n), phone_h), blur=26, dy=14), cx, cy)
        out.append(fr)
    return out


def main() -> None:
    print("a compor imagens da landing...")

    # 1. Compra online: portal de compra + telemóvel com o mapa de lugares
    bg = canvas(1400, 900)
    # corta a zona útil (cabeçalho + resultados); o resto da captura é fundo
    shot = Image.open(SCRATCH / "booking2.png").convert("RGB").crop((0, 0, 1200, 600))
    place(bg, shadow(browser(shot, 940, "busup.updigital.co.mz/comprar")), 600, 420)
    seats = Image.open(SCRATCH / "mob_new.png").convert("RGB")
    place(bg, shadow(phone(seats, 620), blur=30, dy=18), 1130, 500)
    save(bg, "compra.webp")

    # 2. A bordo: POS real (foto de estúdio) + ecrã da app POS
    bg = canvas(1400, 900)
    pos = Image.open(PROJECT / "marketing/premium_assets/pos_terminal_payment_final_4x5.png").convert("RGB")
    ph = round(pos.height * 760 / pos.width)
    place(bg, shadow(rounded(pos.resize((760, ph), Image.LANCZOS), 26)), 470, 450)
    place(bg, shadow(phone(rec(REC_POS, "p", 700), 560), blur=28, dy=16), 1060, 460)
    save(bg, "bordo.webp")

    # 3. Frota no mapa: app do passageiro com autocarro em movimento
    bg = canvas(1400, 900)
    place(bg, shadow(phone(rec(REC_MAP, "m", 1500), 700)), 700, 450)
    save(bg, "mapa.webp")

    # 4. Bilhete: PDF real
    bg = canvas(1400, 900)
    t = ticket_render()
    th = 760
    tw = round(t.width * th / t.height)
    place(bg, shadow(rounded(t.resize((tw, th), Image.LANCZOS), 18)), 700, 450)
    save(bg, "bilhete.webp")

    # 5. Portal (mantém-se, regenerado aqui para consistência)
    dash = Image.open(PROJECT / "marketing/shots/portal_dashboard.png").convert("RGB").crop((0, 0, 3012, 1500))
    bg = canvas(1400, 820)
    place(bg, shadow(browser(dash, 1120, "busup.updigital.co.mz/app")), 700, 410)
    save(bg, "portal.webp")

    # ---- animações (produto real em movimento) ----
    print("a compor animações...")

    # Mapa: o autocarro a percorrer Maputo (GPS real do terminal)
    frames = anim_scene(lambda n: rec(REC_MAP, "m", n),
                        list(range(1180, 2380, 24)), 760, 900, 700, 380, 450)
    animate(frames, "mapa-anim.webp", fps=10)

    # POS: fluxo do agente/motorista no terminal
    frames = anim_scene(lambda n: rec(REC_POS, "p", n),
                        list(range(430, 700, 6)), 760, 900, 700, 380, 450)
    animate(frames, "bordo-anim.webp", fps=12)

    print("feito.")


if __name__ == "__main__":
    main()
