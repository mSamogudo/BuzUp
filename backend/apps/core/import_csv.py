from __future__ import annotations

import io

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


def parse_excel_upload(file_content: bytes, required_fields: list[str], header_map: dict | None = None) -> tuple[list[dict], list[dict]]:
    wb = load_workbook(io.BytesIO(file_content), read_only=True)
    ws = wb.active
    rows_data = []
    errors = []
    hmap = header_map or {}

    headers = []
    for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if i == 1:
            raw = [str(c or "").strip().lower() for c in row]
            headers = [hmap.get(h, h) for h in raw]
            continue
        cleaned = {}
        for j, val in enumerate(row):
            if j < len(headers) and headers[j]:
                cleaned[headers[j]] = str(val or "").strip()
        missing = [f for f in required_fields if f not in cleaned or not cleaned[f]]
        if missing:
            errors.append({"row": i, "detail": f"Campos obrigatorios em falta: {', '.join(missing)}"})
            continue
        rows_data.append(cleaned)

    wb.close()
    return rows_data, errors


CARD_HEADER_MAP = {
    "uid do cartao (obrigatorio)": "card_uid",
    "uid do cartao": "card_uid",
    "card_uid": "card_uid",
    "lote": "issued_batch",
    "issued_batch": "issued_batch",
    "serial no lote": "batch_serial",
    "batch_serial": "batch_serial",
    "serial": "batch_serial",
    "fabricante": "manufacturer",
    "manufacturer": "manufacturer",
}


def import_cards(file_content: bytes) -> dict:
    from apps.cards.models import Card

    rows, errors = parse_excel_upload(file_content, ["card_uid"], header_map=CARD_HEADER_MAP)
    imported = 0

    for i, row in enumerate(rows, start=2):
        uid = row["card_uid"]
        if Card.objects.filter(card_uid=uid).exists():
            errors.append({"row": i, "detail": f"Cartao {uid} ja existe."})
            continue
        Card.objects.create(
            card_type=Card.CardType.PHYSICAL,
            card_uid=uid,
            card_number=row.get("card_number", ""),
            card_technology=row.get("card_technology", "nfc_uid"),
            issued_batch=row.get("issued_batch", ""),
            batch_serial=row.get("batch_serial", ""),
            manufacturer=row.get("manufacturer", ""),
            status=Card.Status.INACTIVE,
        )
        imported += 1

    return {"imported": imported, "errors": errors}


def import_stops(file_content: bytes) -> dict:
    from apps.routes.models import Stop

    rows, errors = parse_excel_upload(file_content, ["name"])
    imported = 0

    for i, row in enumerate(rows, start=2):
        Stop.objects.create(
            code=row.get("code", ""),
            name=row["name"],
            latitude=row.get("latitude") or None,
            longitude=row.get("longitude") or None,
        )
        imported += 1

    return {"imported": imported, "errors": errors}


def import_routes(file_content: bytes) -> dict:
    from apps.routes.models import Route

    rows, errors = parse_excel_upload(file_content, ["name"])
    imported = 0

    for i, row in enumerate(rows, start=2):
        Route.objects.create(
            code=row.get("code", ""),
            name=row["name"],
            description=row.get("description", ""),
        )
        imported += 1

    return {"imported": imported, "errors": errors}


def generate_card_template_excel() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Cartoes NFC"

    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="0D3B66", end_color="0D3B66", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin", color="D4D4D8"),
        right=Side(style="thin", color="D4D4D8"),
        top=Side(style="thin", color="D4D4D8"),
        bottom=Side(style="thin", color="D4D4D8"),
    )

    headers = [
        ("card_uid", "UID do Cartao (obrigatorio)"),
        ("issued_batch", "Lote"),
        ("batch_serial", "Serial no Lote"),
        ("manufacturer", "Fabricante"),
    ]
    for col, (key, label) in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=label)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    examples = [
        ["A1B2C3D4E5F6", "LOTE-2026-001", "001", "MIFARE"],
        ["G7H8I9J0K1L2", "LOTE-2026-001", "002", "MIFARE"],
        ["M3N4O5P6Q7R8", "LOTE-2026-001", "003", "NXP"],
    ]
    for r, row_data in enumerate(examples, 2):
        for c, val in enumerate(row_data, 1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.border = thin_border

    for col in range(1, len(headers) + 1):
        ws.column_dimensions[chr(64 + col)].width = 20

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


IMPORTERS = {
    "cards": import_cards,
    "stops": import_stops,
    "routes": import_routes,
}
