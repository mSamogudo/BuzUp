from __future__ import annotations

import io
from decimal import Decimal
from pathlib import Path

import qrcode
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from apps.guest_checkouts.models import DigitalTravelPass
from apps.guest_checkouts.ticket_codes import ticket_reference, ticket_short_code


DESIGN_WIDTH = 1024
DESIGN_HEIGHT = 1535
TICKET_SCALE = 1.08

PAGE_WIDTH = DESIGN_WIDTH * TICKET_SCALE
PAGE_HEIGHT = DESIGN_HEIGHT * TICKET_SCALE

NAVY = colors.HexColor("#071E49")
ORANGE = colors.HexColor("#E47B11")
RED = colors.HexColor("#D32F2F")


def generate_ticket_pdf(travel_pass: DigitalTravelPass, token: str | None = None) -> bytes:
    return generate_tickets_pdf([(travel_pass, token or travel_pass.token)])


def generate_tickets_pdf(travel_passes: list[DigitalTravelPass | tuple[DigitalTravelPass, str | None]]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))

    normalized_passes = _normalize_passes(travel_passes)
    total = len(normalized_passes)
    for index, (travel_pass, token) in enumerate(normalized_passes, start=1):
        _draw_ticket_page(c, travel_pass, token, sequence=index, total=total)
        if index < total:
            c.showPage()

    c.save()
    return buf.getvalue()


def _normalize_passes(
    travel_passes: list[DigitalTravelPass | tuple[DigitalTravelPass, str | None]],
) -> list[tuple[DigitalTravelPass, str]]:
    normalized = []
    for item in travel_passes:
        if isinstance(item, tuple):
            travel_pass, token = item
        else:
            travel_pass, token = item, None
        normalized.append((travel_pass, token or travel_pass.token))
    return normalized


def _draw_ticket_page(c: canvas.Canvas, travel_pass: DigitalTravelPass, token: str, *, sequence: int, total: int) -> None:
    c.saveState()
    c.scale(TICKET_SCALE, TICKET_SCALE)
    ref = ticket_reference(travel_pass, sequence=sequence, total=total)
    _draw_template(c, nominal=_is_nominal(travel_pass))
    _draw_dynamic_fields(c, travel_pass, ref)
    _draw_qr(c, token, ref)
    c.restoreState()


def _is_nominal(tp: DigitalTravelPass) -> bool:
    return bool(tp.passenger_name or tp.document_number or tp.seat_number)


def _draw_template(c: canvas.Canvas, *, nominal: bool) -> None:
    # Variantes de fundo branco geradas a partir do JPG original (que tinha o
    # cartao sobre um pano azul-escuro). A variante "nominal" tem a zona a
    # direita do QR limpa para receber os dados do passageiro.
    candidates = ["ticket_template_white.jpg", "ticket_template_clean.jpg", "ticket_template.jpg"]
    if nominal:
        candidates.insert(0, "ticket_template_white_nominal.jpg")

    for name in candidates:
        template_path = _asset_path("ticket", name)
        if template_path.exists():
            c.drawImage(ImageReader(str(template_path)), 0, 0, DESIGN_WIDTH, DESIGN_HEIGHT)
            return

    c.setFillColor(colors.white)
    c.rect(0, 0, DESIGN_WIDTH, DESIGN_HEIGHT, fill=1, stroke=0)


def _draw_dynamic_fields(c: canvas.Canvas, tp: DigitalTravelPass, ref: str) -> None:
    issued_at = tp.valid_from or tp.created_at
    valid_until = tp.valid_until
    # Bilhete de partida marcada (interurbano): a data que interessa no topo e
    # a da VIAGEM, nao a da emissao.
    header_dt = tp.departure_at or issued_at

    _text(c, 199, 467, ref, size=25, font="Helvetica-Bold", color=NAVY)
    _text(c, 674, 437, header_dt.strftime("%d/%m/%Y"), size=28, font="Helvetica-Bold", color=NAVY)
    _text(c, 674, 467, header_dt.strftime("%H:%M"), size=28, font="Helvetica-Bold", color=NAVY)

    _center_text_fit(
        c,
        _route_label(tp),
        center_x=526,
        top_y=555,
        max_width=720,
        max_size=68,
        min_size=36,
        color=NAVY,
    )

    _text_fit(c, 192, 762, tp.origin_stop or "-", max_width=255, max_size=45, min_size=28, color=NAVY)
    _right_text_fit(c, 856, 762, tp.destination_stop or "-", max_width=205, max_size=45, min_size=28, color=NAVY)

    _text_fit(c, 282, 901, _fare_label(tp), max_width=245, max_size=45, min_size=31, color=NAVY)
    if tp.status == DigitalTravelPass.Status.ACTIVE:
        status_color = ORANGE
    elif tp.status == DigitalTravelPass.Status.USED:
        status_color = RED
    else:
        status_color = NAVY
    _text_fit(
        c,
        689,
        911,
        _status_label(tp.status),
        max_width=178,
        max_size=40,
        min_size=28,
        color=status_color,
    )

    valid_value = valid_until.strftime("%d/%m/%Y %H:%M") if valid_until else "-"
    _text_fit(c, 446, 1013, valid_value, max_width=295, max_size=34, min_size=25, color=NAVY)

    _draw_passenger_block(c, tp)


def _draw_passenger_block(c: canvas.Canvas, tp: DigitalTravelPass) -> None:
    """Dados do passageiro DENTRO do cartao, ladeando o QR.

    Coluna esquerda (x 130..344): nome (ate 2 linhas) e documento.
    Coluna direita (x 688..906): lugar — a zona onde o template nominal tem o
    bloco "Apresente este QR code" apagado. So aparece em bilhetes nominais;
    o urbano ao portador continua limpo e mantem o texto de ajuda.
    """
    if not _is_nominal(tp):
        return

    left_x, left_width = 130, 214
    y = 1102
    if tp.passenger_name:
        y = _labeled_value(c, left_x, y, "PASSAGEIRO", tp.passenger_name, max_width=left_width, wrap=True)
    if tp.document_number:
        doc_label = dict(DigitalTravelPass.DocumentType.choices).get(tp.document_type, "DOCUMENTO")
        _labeled_value(c, left_x, y, doc_label.upper(), tp.document_number, max_width=left_width)

    if tp.seat_number:
        _labeled_value(c, 688, 1102, "LUGAR", tp.seat_number, max_width=218, max_size=44)


def _labeled_value(
    c: canvas.Canvas,
    x: float,
    y_top: float,
    label: str,
    value: str,
    *,
    max_width: float,
    max_size: int = 34,
    min_size: int = 21,
    wrap: bool = False,
) -> float:
    """Etiqueta laranja + valor navy; devolve o y_top da linha seguinte."""
    label_size = _fit_size(c, label, "Helvetica-Bold", max_width, 20, 13)
    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", label_size)
    c.drawString(x, _baseline(y_top, label_size), label)

    y = y_top + label_size + 8
    lines = [value]
    if wrap and c.stringWidth(value, "Helvetica-Bold", min_size) > max_width:
        lines = _split_two_lines(value)
    size = min(
        _fit_size(c, line, "Helvetica-Bold", max_width, max_size, min_size) for line in lines
    )
    for line in lines:
        _text(c, x, y, line, size=size, font="Helvetica-Bold", color=NAVY)
        y += size + 6
    return y + 18


def _split_two_lines(value: str) -> list[str]:
    words = value.split()
    if len(words) < 2:
        return [value]
    # Quebra no espaco que deixa as duas linhas mais equilibradas.
    best = min(
        range(1, len(words)),
        key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))),
    )
    return [" ".join(words[:best]), " ".join(words[best:])]


def _draw_qr(c: canvas.Canvas, data: str, ref: str) -> None:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=0)
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    c.setFillColor(colors.white)
    c.roundRect(354, _pdf_y(1070 + 291), 312, 291, 9, fill=1, stroke=0)
    # QR centred in the white card (fills the old right-side gap without
    # touching the yellow border around it).
    c.drawImage(ImageReader(qr_buf), 366, _pdf_y(1072 + 287), 287, 287)

    _center_text_fit(
        c,
        ticket_short_code(ref),
        center_x=512,
        top_y=1365,
        max_width=112,
        max_size=35,
        min_size=28,
        color=NAVY,
    )


def _text(c: canvas.Canvas, x: float, y_top: float, value: str, *, size: int, font: str, color) -> None:
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawString(x, _baseline(y_top, size), value)


def _text_fit(
    c: canvas.Canvas,
    x: float,
    y_top: float,
    value: str,
    *,
    max_width: float,
    max_size: int,
    min_size: int,
    color,
) -> None:
    size = _fit_size(c, value, "Helvetica-Bold", max_width, max_size, min_size)
    _text(c, x, y_top, value, size=size, font="Helvetica-Bold", color=color)


def _right_text_fit(
    c: canvas.Canvas,
    x_right: float,
    y_top: float,
    value: str,
    *,
    max_width: float,
    max_size: int,
    min_size: int,
    color,
) -> None:
    size = _fit_size(c, value, "Helvetica-Bold", max_width, max_size, min_size)
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", size)
    c.drawRightString(x_right, _baseline(y_top, size), value)


def _center_text_fit(
    c: canvas.Canvas,
    value: str,
    *,
    center_x: float,
    top_y: float,
    max_width: float,
    max_size: int,
    min_size: int,
    color,
) -> None:
    size = _fit_size(c, value, "Helvetica-Bold", max_width, max_size, min_size)
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", size)
    c.drawCentredString(center_x, _baseline(top_y, size), value)


def _fit_size(c: canvas.Canvas, value: str, font: str, max_width: float, max_size: int, min_size: int) -> int:
    size = max_size
    while size > min_size and c.stringWidth(value, font, size) > max_width:
        size -= 1
    return size


def _baseline(y_top: float, size: float) -> float:
    return DESIGN_HEIGHT - y_top - size * 0.84


def _pdf_y(y_from_top: float) -> float:
    return DESIGN_HEIGHT - y_from_top


def _route_label(tp: DigitalTravelPass) -> str:
    # Only the route at the top — origin/destination are printed below.
    return tp.route_code or tp.route_name or "BuzUp"


def _asset_path(folder: str, filename: str) -> Path:
    return Path(settings.BASE_DIR) / "static" / "assets" / folder / filename


def _fare_label(tp: DigitalTravelPass) -> str:
    """Preco na moeda escolhida na compra.

    O MZN continua a ser a moeda canonica (fare_amount); display_currency e
    display_fare_amount sao o retrato ZAR congelado no momento da compra,
    quando existirem. Sem eles, mostra-se o valor em meticais.
    """
    currency = (tp.display_currency or "MZN").upper()
    if currency != "MZN" and tp.display_fare_amount:
        return f"{_money(tp.display_fare_amount)} {currency}"
    return f"{_money(tp.fare_amount)} MZN"


def _money(value: Decimal | None) -> str:
    amount = Decimal(value or "0.00").quantize(Decimal("0.01"))
    return f"{amount:.2f}".replace(".", ",")


def _status_label(status: str) -> str:
    labels = {
        DigitalTravelPass.Status.ACTIVE: "ACTIVO",
        DigitalTravelPass.Status.USED: "USADO",
        DigitalTravelPass.Status.EXPIRED: "EXPIRADO",
        DigitalTravelPass.Status.CANCELLED: "CANCELADO",
        DigitalTravelPass.Status.REFUNDED: "REEMBOLSADO",
    }
    return labels.get(status, str(status).upper())
