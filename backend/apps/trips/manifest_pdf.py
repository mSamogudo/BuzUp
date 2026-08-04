"""Manifesto de bordo em PDF.

O documento que sai daqui é o que se entrega numa fiscalização, o que segue
para a seguradora depois de um sinistro e o que fica em arquivo. Por isso
carrega o essencial no topo — rota, viatura, motorista, hora de partida e
quantos seguiram — e a lista completa por baixo, com o lugar bem visível.

Reaproveita o cabeçalho e o rodapé dos relatórios (`apps.reports.exporters`)
para o documento ser reconhecível como sendo da mesma casa, e para herdar a
leitura única dos logótipos: sem isso, um manifesto de 60 passageiros voltava
a descodificar o mesmo PNG em cada página.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from apps.reports.exporters import (
    GREY,
    NAVY,
    SOFT_BG,
    _draw_footer,
    _draw_header,
    _fit_text,
    _load_logos,
)

BOARDING_LABELS = {
    "aboard": "A bordo",
    # "Por embarcar" nao cabia na coluna e saia cortado ("Por embar...").
    "expected": "Aguarda",
    "no_show": "Faltou",
}
GREEN = colors.HexColor("#2A9D8F")
AMBER = colors.HexColor("#B58900")
RED = colors.HexColor("#D32F2F")
BOARDING_COLOURS = {"aboard": GREEN, "expected": AMBER, "no_show": RED}

# O manifesto formal (interprovincial/internacional) leva os dados de contacto
# — e para isso que existe. Numa carreira urbana esses dados nem sao pedidos ao
# passageiro, por isso as colunas sairiam vazias e so roubavam largura.
COLUMNS_FORMAL = [
    ("seat", "Lugar", 12),
    ("passenger_name", "Passageiro", 40),
    ("document", "Documento", 24),
    ("phone", "Telefone", 24),
    ("emergency", "Emergencia", 42),
    ("destination", "Destino", 26),
    ("payment_label", "Pagamento", 22),
    ("fare_amount", "Valor", 18),
    ("boarding", "Estado", 28),
]

COLUMNS_SIMPLE = [
    ("seat", "Lugar", 12),
    ("passenger_name", "Passageiro", 40),
    ("origin", "Origem", 30),
    ("destination", "Destino", 30),
    ("channel_label", "Venda", 18),
    ("payment_label", "Pagamento", 24),
    ("fare_amount", "Valor", 20),
    ("boarding", "Estado", 28),
]


def _hora(iso: str) -> str:
    if not iso:
        return "-"
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso


def render_manifest_pdf(data: dict) -> bytes:
    colunas = COLUMNS_FORMAL if data.get("formal") else COLUMNS_SIMPLE
    buf = io.BytesIO()
    page = A4                      # retrato: a lista é longa, não larga
    width, height = page
    c = canvas.Canvas(buf, pagesize=page)
    logos = _load_logos()

    totals = data.get("totals") or {}
    titulo = f"Manifesto de bordo — {data.get('route_code') or ''}"

    # O cabecalho partilhado escreve o titulo a direita e o periodo ao centro;
    # com um titulo longo os dois textos montavam um em cima do outro. Aqui o
    # periodo vai vazio e a hora de partida aparece na ficha, que e onde faz
    # sentido lê-la.
    _draw_header(c, width, height, title=titulo,
                 period_from="", period_to="", logos=logos)

    y = height - 30 * mm
    y = _ficha(c, width, y, data, totals)
    y = _resumo(c, width, y, totals)
    y = _pagamentos(c, width, y, totals)

    col_widths = _larguras(width, colunas)
    y = _cabecalho_tabela(c, y, col_widths, width, colunas)

    linhas = data.get("entries") or []
    if not linhas:
        c.setFillColor(GREY)
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(12 * mm, y - 6 * mm, "Nenhum passageiro registado nesta viagem.")
        y -= 12 * mm
    else:
        y = _linhas(c, y, linhas, col_widths, page, titulo, data, logos, width, colunas)

    _assinaturas(c, y, width)
    _draw_footer(c, width, logos)
    c.save()
    return buf.getvalue()


def _larguras(width: float, colunas) -> list[float]:
    total_peso = sum(peso for _, _, peso in colunas)
    disponivel = width - 24 * mm
    return [disponivel * (peso / total_peso) for _, _, peso in colunas]


def _ficha(c, width, y, data, totals) -> float:
    """Rota, viatura, motorista e partida — o que identifica a viagem."""
    campos = [
        ("Rota", f"{data.get('route_code', '')} {data.get('route_name', '')}".strip() or "-"),
        ("Viatura", data.get("vehicle") or "-"),
        ("Motorista", data.get("driver") or "-"),
        ("Partida", _hora(data.get("departed_at") or data.get("planned_departure_at", ""))),
    ]
    c.setFillColor(SOFT_BG)
    c.rect(12 * mm, y - 16 * mm, width - 24 * mm, 16 * mm, fill=1, stroke=0)
    x = 15 * mm
    largura = (width - 30 * mm) / len(campos)
    for label, valor in campos:
        c.setFillColor(GREY)
        c.setFont("Helvetica", 7)
        c.drawString(x, y - 6 * mm, label.upper())
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x, y - 12 * mm, _fit_text(c, valor, "Helvetica-Bold", 9, largura - 4))
        x += largura
    return y - 22 * mm


def _resumo(c, width, y, totals) -> float:
    """Os números que se lêem primeiro: quantos seguiram, quantos faltaram."""
    caixas = [
        ("A BORDO", str(totals.get("aboard", 0)), GREEN),
        ("POR EMBARCAR", str(totals.get("expected", 0)), AMBER),
        ("FALTAS", str(totals.get("no_show", 0)), RED),
        ("LUGARES", f"{totals.get('aboard', 0)}/{totals.get('capacity') or '-'}", NAVY),
        ("VALOR", f"{totals.get('fare_total', '0.00')} MZN", NAVY),
    ]
    largura = (width - 24 * mm - (len(caixas) - 1) * 3 * mm) / len(caixas)
    x = 12 * mm
    for label, valor, cor in caixas:
        c.setStrokeColor(colors.HexColor("#E7E1D4"))
        c.setFillColor(colors.white)
        c.roundRect(x, y - 15 * mm, largura, 15 * mm, 2 * mm, fill=1, stroke=1)
        c.setFillColor(GREY)
        c.setFont("Helvetica", 6.5)
        c.drawString(x + 3 * mm, y - 5.5 * mm, label)
        c.setFillColor(cor)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(x + 3 * mm, y - 12 * mm, valor)
        x += largura + 3 * mm
    return y - 21 * mm


def _pagamentos(c, width, y, totals) -> float:
    """Repartição por forma de pagamento.

    É a linha que o motorista confere no fecho: o que entrou por M-Pesa e
    e-Mola foi recebido por ele; o que saiu de cartão ou saldo já estava
    cobrado e não lhe passou pelas mãos.
    """
    reparticao = totals.get("by_payment") or []
    if not reparticao:
        return y

    c.setFillColor(GREY)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(12 * mm, y - 4 * mm, "POR FORMA DE PAGAMENTO")
    y -= 8 * mm

    x = 12 * mm
    for item in reparticao:
        texto = f"{item['label']}: {item['amount']} MZN ({item['count']})"
        largura = c.stringWidth(texto, "Helvetica-Bold", 8) + 8 * mm
        if x + largura > width - 12 * mm:      # passa à linha seguinte
            x = 12 * mm
            y -= 7 * mm
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.HexColor("#E7E1D4"))
        c.roundRect(x, y - 5.5 * mm, largura - 2 * mm, 6.5 * mm, 1.5 * mm, fill=1, stroke=1)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x + 3 * mm, y - 3.8 * mm, texto)
        x += largura
    return y - 10 * mm


def _cabecalho_tabela(c, y, col_widths, width, colunas) -> float:
    linha_h = 6 * mm
    c.setFillColor(NAVY)
    c.rect(12 * mm, y - linha_h, width - 24 * mm, linha_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7.5)
    x = 12 * mm
    for (_, label, _), w in zip(colunas, col_widths):
        c.drawString(x + 2, y - linha_h + 1.9 * mm, label)
        x += w
    return y - linha_h


def _linhas(c, y, linhas, col_widths, page, titulo, data, logos, width, colunas) -> float:
    linha_h = 5.6 * mm
    page_w, page_h = page
    min_y = 34 * mm      # deixa espaco para as assinaturas e o rodape

    for i, entrada in enumerate(linhas):
        if y < min_y:
            _draw_footer(c, page_w, logos)
            c.showPage()
            _draw_header(c, page_w, page_h, title=titulo,
                         period_from=_hora(data.get("departed_at", "")), period_to="",
                         logos=logos)
            y = page_h - 30 * mm
            y = _cabecalho_tabela(c, y, col_widths, width, colunas)

        if i % 2 == 1:
            c.setFillColor(SOFT_BG)
            c.rect(12 * mm, y - linha_h, width - 24 * mm, linha_h, fill=1, stroke=0)

        x = 12 * mm
        base = y - linha_h + 1.7 * mm
        for (chave, _, _), w in zip(colunas, col_widths):
            if chave == "emergency":
                # Nome e numero juntos: numa emergencia le-se uma coisa so.
                nome = entrada.get("emergency_name") or ""
                tel = entrada.get("emergency_phone") or ""
                valor = f"{nome} {tel}".strip() or "-"
            elif chave == "phone":
                valor = entrada.get("phone") or "-"
            else:
                valor = str(entrada.get(chave, "") or "")
            if chave == "boarding":
                c.setFillColor(BOARDING_COLOURS.get(valor, NAVY))
                c.setFont("Helvetica-Bold", 7.5)
                valor = BOARDING_LABELS.get(valor, valor)
            elif chave == "seat":
                c.setFillColor(NAVY)
                c.setFont("Helvetica-Bold", 8)
            else:
                c.setFillColor(NAVY)
                c.setFont("Helvetica", 7.5)
            fonte = "Helvetica-Bold" if chave in ("seat", "boarding") else "Helvetica"
            tamanho = 8 if chave == "seat" else 7.5
            c.drawString(x + 2, base, _fit_text(c, valor, fonte, tamanho, w - 4))
            x += w
        y -= linha_h
    return y


def _assinaturas(c, y, width) -> None:
    """Duas linhas para assinar: sem isto, o papel não fecha nada."""
    if y < 32 * mm:
        return
    y = max(y - 8 * mm, 24 * mm)
    largura = (width - 30 * mm) / 2
    for i, label in enumerate(("Motorista", "Fiscalizacao / Terminal")):
        x = 12 * mm + i * (largura + 6 * mm)
        c.setStrokeColor(colors.HexColor("#B7C4D3"))
        c.line(x, y, x + largura - 6 * mm, y)
        c.setFillColor(GREY)
        c.setFont("Helvetica", 7)
        c.drawString(x, y - 4 * mm, label)
