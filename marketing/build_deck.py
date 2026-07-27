#!/usr/bin/env python3
"""Constroi a apresentacao BusUp 16:9 a partir de deck.html.

Pipeline: tokens base64 -> deck.built.html -> Brave headless -> PDF vectorial
-> pdftoppm -> PNGs por slide -> PPTX (writer de build_premium_deck) -> folha
de contacto para revisao visual.
"""

from __future__ import annotations

import base64
import io
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image

from build_premium_deck import make_pptx

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
SHOTS = ROOT / "shots"
DECK_ASSETS = ROOT / "deck_assets"
EXPORT = ROOT / "premium_export"
PAGES = EXPORT / "pdf_pages"

BRAVE = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
UPDIR = PROJECT / "frontend/public/assets/up-digital-logo"


def b64(im: Image.Image, fmt: str = "PNG", **kw) -> str:
    buf = io.BytesIO()
    im.save(buf, fmt, optimize=True, **kw)
    return f"data:image/{fmt.lower()};base64," + base64.b64encode(buf.getvalue()).decode()


def logo(path: Path, max_w: int = 900) -> str:
    im = Image.open(path).convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    im = im.crop(bbox)
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    return b64(im)


def shot(name: str, crop: tuple[int, int, int, int] | None = None, max_w: int = 2000) -> str:
    im = Image.open(SHOTS / name).convert("RGB")
    if crop:
        im = im.crop(crop)
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    return b64(im)


def photo(path: Path, max_w: int = 1400, quality: int = 88, crop: tuple[int, int, int, int] | None = None) -> str:
    im = Image.open(path).convert("RGB")
    if crop:
        im = im.crop(crop)
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def qr() -> str:
    data = (ROOT / "qr.b64.txt").read_text().strip()
    return data if data.startswith("data:") else "data:image/png;base64," + data


TOKENS = {
    "__LOGO_DARK__": logo(DECK_ASSETS / "logo_dark.png"),
    "__LOGO_LIGHT__": logo(DECK_ASSETS / "logo_light.png"),
    # marca oficial UpDigital (monograma UP + sorriso); _rev = knockout branco p/ fundo escuro
    "__UP_LIGHT__": logo(DECK_ASSETS / "up_mark_rev.png", 300),
    "__UP_DARK__": logo(DECK_ASSETS / "up_mark.png", 300),
    "__UP_FULL_REV__": logo(DECK_ASSETS / "up_full_rev.png", 500),
    # 3012: corta a scrollbar escura na borda direita das capturas do portal
    "__SHOT_DASH__": shot("portal_dashboard.png", (0, 0, 3012, 1500)),
    "__SHOT_ROTAS__": shot("portal_rotas.png", (0, 0, 3012, 1500)),
    "__SHOT_MAPA__": shot("portal_mapa.png", (548, 500, 3012, 1490)),
    "__SHOT_VAL__": shot("portal_validacoes.png", (0, 0, 3012, 1225)),
    # capa: poster com todos os componentes (autocarro + gestao + POS + mobile),
    # sem as faixas de logo/texto embutidas
    "__POSTER_ALL__": photo(ROOT / "ChatGPT Image Jul 16, 2026, 01_43_54 PM (4).png",
                            1100, 90, crop=(0, 172, 1003, 1224)),
    # fotos reais de produto (estudio azul + rua); telemovel recolorido p/ azul da marca
    "__PHOTO_PHONE__": photo(DECK_ASSETS / "photo_phone_blue.png", 1100),
    "__PHOTO_POS__": photo(ROOT / "premium_assets/pos_terminal_payment_final_4x5.png", 1100),
    "__PHOTO_TICKET__": photo(ROOT / "premium_assets/ticket_qr_phone_hand_bus_final_4x5.png", 1200),
    # carteiras de pagamento (assets do proprio produto)
    "__PAY_MPESA__": logo(DECK_ASSETS / "pay_mpesa.png", 240),
    "__PAY_EMOLA__": logo(DECK_ASSETS / "pay_emola.png", 240),
    # portfolio UpDigital (logos oficiais das propostas GOUP/MBANDI)
    "__PL_BUSUP__": logo(DECK_ASSETS / "prod_busup.png", 400),
    "__PL_PAYUP__": logo(DECK_ASSETS / "prod_payup.png", 400),
    "__PL_CASHUP__": logo(DECK_ASSETS / "prod_cashup.png", 400),
    "__PL_TAXUP__": logo(DECK_ASSETS / "prod_taxup.png", 400),
    "__PL_GATEUP__": logo(DECK_ASSETS / "prod_gateup.png", 400),
    "__PL_GOUP__": logo(DECK_ASSETS / "prod_goup.png", 400),
    "__QR__": qr(),
}


def build_html() -> Path:
    html = (ROOT / "deck.html").read_text()
    for tok, val in TOKENS.items():
        if tok not in html:
            raise SystemExit(f"token ausente no HTML: {tok}")
        html = html.replace(tok, val)
    out = ROOT / "deck.built.html"
    out.write_text(html)
    print(f"{out}  ({len(html) / 1e6:.1f} MB)")
    return out


def render_pdf(built: Path) -> Path:
    pdf = ROOT / "BusUp-Apresentacao.pdf"
    subprocess.run(
        [BRAVE, "--headless", "--disable-gpu", "--no-sandbox",
         "--virtual-time-budget=8000", "--print-to-pdf-no-header",
         f"--print-to-pdf={pdf}", f"file://{built}"],
        check=True, capture_output=True,
    )
    print(f"{pdf}  ({pdf.stat().st_size / 1e6:.1f} MB)")
    return pdf


def rasterize(pdf: Path) -> list[Path]:
    PAGES.mkdir(parents=True, exist_ok=True)
    for old in PAGES.glob("page-*.png"):
        old.unlink()
    subprocess.run(
        ["pdftoppm", "-png", "-r", "144", str(pdf), str(PAGES / "page")],
        check=True, capture_output=True,
    )
    pngs = sorted(PAGES.glob("page-*.png"))
    # normaliza para 2880x1620 exactos e re-optimiza
    for p in pngs:
        im = Image.open(p).convert("RGB")
        if im.size != (2880, 1620):
            im = im.resize((2880, 1620), Image.LANCZOS)
        im.save(p, optimize=True)
    print(f"{len(pngs)} páginas rasterizadas em {PAGES}")
    return pngs


def contact_sheet(pngs: list[Path]) -> None:
    thumb_w, thumb_h = 640, 360
    cols = 2
    rows = math.ceil(len(pngs) / cols)
    sheet = Image.new("RGB", (cols * (thumb_w + 24) + 24, rows * (thumb_h + 24) + 24), "#1A1A1E")
    for i, p in enumerate(pngs):
        t = Image.open(p).convert("RGB")
        t.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
        x = 24 + (i % cols) * (thumb_w + 24)
        y = 24 + (i // cols) * (thumb_h + 24)
        sheet.paste(t, (x, y))
    out = EXPORT / "deck-contact-sheet.jpg"
    sheet.save(out, quality=90)
    print(out)


def main() -> None:
    built = build_html()
    pdf = render_pdf(built)
    pngs = rasterize(pdf)
    if len(pngs) != 11:
        sys.exit(f"esperava 11 páginas, obtive {len(pngs)}")
    make_pptx(pngs, ROOT / "BusUp-Apresentacao-Premium.pptx")
    print(ROOT / "BusUp-Apresentacao-Premium.pptx")
    contact_sheet(pngs)


if __name__ == "__main__":
    main()
