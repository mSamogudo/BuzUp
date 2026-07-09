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
    _draw_template(c)
    _draw_dynamic_fields(c, travel_pass, ref)
    _draw_qr(c, token, ref)
    c.restoreState()


def _draw_template(c: canvas.Canvas) -> None:
    template_path = _asset_path("ticket", "ticket_template_clean.jpg")
    if not template_path.exists():
        template_path = _asset_path("ticket", "ticket_template.jpg")

    if template_path.exists():
        c.drawImage(ImageReader(str(template_path)), 0, 0, DESIGN_WIDTH, DESIGN_HEIGHT)
        return

    c.setFillColor(colors.HexColor("#061A3A"))
    c.rect(0, 0, DESIGN_WIDTH, DESIGN_HEIGHT, fill=1, stroke=0)


def _draw_dynamic_fields(c: canvas.Canvas, tp: DigitalTravelPass, ref: str) -> None:
    issued_at = tp.valid_from or tp.created_at
    valid_until = tp.valid_until

    _text(c, 199, 467, ref, size=25, font="Helvetica-Bold", color=NAVY)
    _text(c, 674, 437, issued_at.strftime("%d/%m/%Y"), size=28, font="Helvetica-Bold", color=NAVY)
    _text(c, 674, 467, issued_at.strftime("%H:%M"), size=28, font="Helvetica-Bold", color=NAVY)

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

    _text_fit(c, 282, 901, f"{_money(tp.fare_amount)} MZN", max_width=245, max_size=45, min_size=31, color=NAVY)
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
    return tp.route_code or tp.route_name or "BusUp"


def _asset_path(folder: str, filename: str) -> Path:
    return Path(settings.BASE_DIR) / "static" / "assets" / folder / filename


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
