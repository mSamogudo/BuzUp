#!/usr/bin/env python3
"""Embute as imagens em base64 no brochure.html e escreve brochure.built.html.

As capturas reais vivem em marketing/shots/ (ja tratadas: rodape admin_teste
removido, laranja do build antigo convertido para o azul da marca).
"""
import base64, io, os, re
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "shots")


def load(path, max_w=None, crop=None, quality=None):
    im = Image.open(path).convert("RGB")
    if crop:
        im = im.crop(crop)
    if max_w and im.width > max_w:
        h = round(im.height * max_w / im.width)
        im = im.resize((max_w, h), Image.LANCZOS)
    buf = io.BytesIO()
    if quality:
        im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
        mime = "jpeg"
    else:
        im.save(buf, "PNG", optimize=True)
        mime = "png"
    return f"data:image/{mime};base64," + base64.b64encode(buf.getvalue()).decode()


def poster(name, max_w=1500):
    return load(os.path.join(HERE, name), max_w=max_w, quality=86)


def shot(name, max_w):
    return load(os.path.join(SHOTS, name), max_w=max_w)


def phone(name, max_w=620, ratio=16 / 9):
    """Normaliza um ecra de telemovel para 9:16 — corta o vazio em baixo, ou
    preenche com a cor de fundo do proprio ecra. Mantem os tres alinhados."""
    im = Image.open(os.path.join(SHOTS, name)).convert("RGB")
    want = round(im.width * ratio)
    if im.height > want:
        im = im.crop((0, 0, im.width, want))
    elif im.height < want:
        bg = im.crop((0, im.height - 2, im.width, im.height)).resize((1, 1), Image.BOX).getpixel((0, 0))
        pad = Image.new("RGB", (im.width, want), bg)
        pad.paste(im, (0, 0))
        im = pad
    h = round(im.height * max_w / im.width)
    im = im.resize((max_w, h), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


TOKENS = {
    "__IMG_ECOSYSTEM__": poster("ChatGPT Image Jul 16, 2026, 11_39_54 AM.png"),
    "__IMG_CONNECT__":   poster("ChatGPT Image Jul 16, 2026, 01_43_59 PM (8).png"),
    "__IMG_FLOW__":      poster("ChatGPT Image Jul 16, 2026, 01_43_51 PM (2).png"),
    "__IMG_START__":     poster("ChatGPT Image Jul 16, 2026, 01_43_48 PM (1).png", max_w=1200),
    # capturas reais do produto
    "__IMG_CARTEIRA__":  phone("mobile_carteira.png", 760, ratio=17 / 9),
    "__IMG_POS__":       phone("pos_venda_ok.png", 760, ratio=17 / 9),
    "__IMG_BILHETE__":   phone("mobile_bilhete.png"),
    "__IMG_PERFIL__":    phone("mobile_perfil.png"),
    "__IMG_FLUXO__":     phone("pos_fluxo.png"),
    # dashboard: corta o branco vazio abaixo dos cartoes, mantendo o menu lateral
    "__IMG_MGMT__":      load(os.path.join(SHOTS, "portal_dashboard.png"),
                              crop=(0, 0, 3024, 1500), max_w=2000),
    "__IMG_AUDIT__":     shot("portal_validacoes.png", 2000),
    # mapa: so a tela do mapa, sem a barra lateral do portal
    "__IMG_CONTROL__":   load(os.path.join(SHOTS, "portal_mapa.png"),
                              crop=(556, 492, 2140, 1726), max_w=1400),
    "__IMG_QR__":        "data:image/png;base64," + open(os.path.join(HERE, "qr.b64.txt")).read().strip(),
}

html = open(os.path.join(HERE, "brochure.html")).read()
for tok, val in TOKENS.items():
    if tok not in html:
        raise SystemExit(f"token ausente no HTML: {tok}")
    html = html.replace(tok, val)

left = re.findall(r"__IMG_[A-Z_]+__", html)
if left:
    raise SystemExit(f"tokens por substituir: {set(left)}")

out = os.path.join(HERE, "brochure.built.html")
open(out, "w").write(html)
print(f"{out}  ({len(html)/1e6:.1f} MB)")
