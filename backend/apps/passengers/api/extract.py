from __future__ import annotations

import io
from datetime import timedelta
from decimal import Decimal

from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.passengers.models import PassengerAccount
from apps.reports.exporters import _asset, _branding_image, _safe_image
from apps.wallets.models import WalletTransaction


class PassengerExtractView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            passenger = PassengerAccount.objects.select_related("wallet").get(pk=pk)
        except PassengerAccount.DoesNotExist:
            return Response({"detail": "Passageiro nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        now = timezone.now()
        if date_from:
            from django.utils.dateparse import parse_date
            dt_from = timezone.make_aware(timezone.datetime.combine(parse_date(date_from), timezone.datetime.min.time()))
        else:
            dt_from = now - timedelta(days=30)

        if date_to:
            from django.utils.dateparse import parse_date
            dt_to = timezone.make_aware(timezone.datetime.combine(parse_date(date_to), timezone.datetime.min.time())) + timedelta(days=1)
        else:
            dt_to = now + timedelta(days=1)

        wallet = getattr(passenger, "wallet", None)
        txs = []
        if wallet:
            txs = list(WalletTransaction.objects.filter(
                wallet=wallet,
                created_at__gte=dt_from,
                created_at__lt=dt_to,
            ).order_by("-created_at")[:200])

        pdf = _generate_extract_pdf(passenger, wallet, txs, dt_from, dt_to)
        response = HttpResponse(pdf, content_type="application/pdf")
        name = passenger.full_name.replace(" ", "_")
        response["Content-Disposition"] = f'attachment; filename="extracto_{name}.pdf"'
        return response


def _generate_extract_pdf(passenger, wallet, txs, dt_from, dt_to) -> bytes:
    buf = io.BytesIO()
    width, height = A4
    c = canvas.Canvas(buf, pagesize=A4)

    accent = colors.HexColor("#0D3B66")
    gray = colors.HexColor("#71717a")
    light = colors.HexColor("#f4f4f5")

    c.setFillColor(accent)
    c.rect(0, height - 25 * mm, width, 25 * mm, fill=1, stroke=0)

    # Logo do branding (report_logo/primary_logo) com fallback estatico.
    logo = (
        _branding_image("report_logo")
        or _branding_image("primary_logo")
        or _safe_image(_asset("tpm-tur-logo", "tpm_dark.png"))
    )
    text_x = 15 * mm
    if logo:
        try:
            iw, ih = logo.getSize()
            lh = 12 * mm
            lw = iw * lh / ih
            c.drawImage(logo, 15 * mm, height - 19 * mm, width=lw, height=lh, mask="auto")
            text_x = 15 * mm + lw + 5 * mm
        except Exception:
            pass

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(text_x, height - 15 * mm, "BuzUp")
    c.setFont("Helvetica", 8)
    c.drawString(text_x, height - 20 * mm, "Extracto de Transaccoes")
    c.drawRightString(width - 15 * mm, height - 15 * mm, f"Emitido: {dt_from.strftime('%d/%m/%Y')} a {dt_to.strftime('%d/%m/%Y')}")

    y = height - 35 * mm
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(15 * mm, y, passenger.full_name)
    y -= 5 * mm
    c.setFont("Helvetica", 9)
    c.setFillColor(gray)
    details = []
    if passenger.phone_number:
        details.append(f"Tel: {passenger.phone_number}")
    if passenger.email:
        details.append(f"Email: {passenger.email}")
    if passenger.document_number:
        details.append(f"Doc: {passenger.document_number}")
    c.drawString(15 * mm, y, " | ".join(details))
    y -= 5 * mm
    if wallet:
        c.drawString(15 * mm, y, f"Saldo actual: {wallet.balance_cached:,.2f} {wallet.currency}")
    y -= 8 * mm

    c.setStrokeColor(light)
    c.setLineWidth(0.5)
    c.line(15 * mm, y, width - 15 * mm, y)
    y -= 6 * mm

    headers = ["Data/Hora", "Referencia", "Tipo", "Valor", "Saldo Antes", "Saldo Depois"]
    col_x = [15, 50, 95, 125, 150, 175]

    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 7)
    for i, h in enumerate(headers):
        c.drawString(col_x[i] * mm, y, h)
    y -= 3 * mm
    c.setStrokeColor(accent)
    c.setLineWidth(0.5)
    c.line(15 * mm, y, width - 15 * mm, y)
    y -= 5 * mm

    c.setFont("Helvetica", 7)
    total_credit = Decimal("0.00")
    total_debit = Decimal("0.00")

    for tx in txs:
        if y < 20 * mm:
            c.showPage()
            y = height - 20 * mm
            c.setFont("Helvetica", 7)

        c.setFillColor(colors.black)
        c.drawString(col_x[0] * mm, y, tx.created_at.strftime("%d/%m/%Y %H:%M"))
        c.drawString(col_x[1] * mm, y, tx.reference[:18])
        c.drawString(col_x[2] * mm, y, tx.type.replace("_", " ")[:12])

        if tx.direction == "credit":
            c.setFillColor(colors.HexColor("#2A9D8F"))
            c.drawString(col_x[3] * mm, y, f"+{tx.amount:,.2f}")
            total_credit += tx.amount
        else:
            c.setFillColor(colors.HexColor("#D62828"))
            c.drawString(col_x[3] * mm, y, f"-{tx.amount:,.2f}")
            total_debit += tx.amount

        c.setFillColor(gray)
        c.drawString(col_x[4] * mm, y, f"{tx.balance_before:,.2f}")
        c.drawString(col_x[5] * mm, y, f"{tx.balance_after:,.2f}")

        y -= 4 * mm

    y -= 4 * mm
    c.setStrokeColor(accent)
    c.line(15 * mm, y, width - 15 * mm, y)
    y -= 6 * mm
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(15 * mm, y, f"Total Creditos: {total_credit:,.2f} MZN")
    c.drawString(95 * mm, y, f"Total Debitos: {total_debit:,.2f} MZN")
    c.drawString(width - 60 * mm, y, f"Transaccoes: {len(txs)}")

    up = (
        _branding_image("powered_by_logo")
        or _safe_image(_asset("up-digital-logo", "up_digital_dark.png"))
    )
    if up:
        try:
            iw, ih = up.getSize()
            lh = 6 * mm
            lw = iw * lh / ih
            c.drawImage(up, (width - lw) / 2, 6 * mm, width=lw, height=lh, mask="auto")
            c.save()
            return buf.getvalue()
        except Exception:
            pass
    c.setFillColor(colors.HexColor("#a1a1aa"))
    c.setFont("Helvetica", 5)
    c.drawCentredString(width / 2, 8 * mm, "powered by UpDigital | buzup.co.mz")

    c.save()
    return buf.getvalue()
