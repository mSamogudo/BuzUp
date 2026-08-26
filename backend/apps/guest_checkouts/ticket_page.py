"""A pagina do bilhete que o passageiro abre a partir do SMS.

O link do SMS devolvia um PDF de 339 KB. Gerar custava 100 ms — o problema
nunca foi o servidor: era o TAMANHO. Num telemovel com dados moveis isso sao
segundos a olhar para um ecra branco, muitas vezes na paragem, com o autocarro
a chegar.

Esta pagina pesa cerca de 8 KB e nao pede um unico ficheiro extra: nem CSS, nem
tipos de letra, nem imagens. O QR e SVG desenhado a mao a partir da matriz.
Abre de imediato e, uma vez aberta, continua a ver-se sem rede — que e
exactamente a situacao de quem esta a embarcar.

O PDF continua a existir, em `/pdf/`, para quem o quiser imprimir ou guardar.
E o bilhete formal; esta pagina e o que se mostra ao revisor.
"""

from __future__ import annotations

import html

import qrcode

# Modulo do QR em unidades do SVG. Inteiro de proposito: com fraccoes, os
# quadrados encostam mal uns aos outros e alguns leitores falham a leitura.
MODULO = 4


def _qr_svg(dados: str) -> str:
    """O QR como SVG, desenhado a partir da matriz.

    Uma imagem PNG do mesmo QR ronda os 2 KB e fica desfocada quando o revisor
    aproxima o telemovel. Em SVG sao ~2 KB de texto que comprime bem e le-se
    nitido a qualquer tamanho.
    """
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    qr.add_data(dados)
    qr.make(fit=True)
    matriz = qr.get_matrix()
    lado = len(matriz) * MODULO

    # Um so `path` em vez de um `rect` por modulo: com ~1300 modulos, a
    # diferenca sao 40 KB de SVG contra 3.
    partes = []
    for y, linha in enumerate(matriz):
        x = 0
        while x < len(linha):
            if linha[x]:
                inicio = x
                while x < len(linha) and linha[x]:
                    x += 1
                partes.append(
                    f"M{inicio * MODULO} {y * MODULO}h{(x - inicio) * MODULO}v{MODULO}h-{(x - inicio) * MODULO}z")
            else:
                x += 1
    return (
        f'<svg class="qr" viewBox="0 0 {lado} {lado}" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-label="Codigo QR do bilhete">'
        f'<path fill="#000" d="{"".join(partes)}"/></svg>'
    )


def _linha(rotulo: str, valor: str) -> str:
    if not valor:
        return ""
    return (f'<div class="l"><span>{html.escape(rotulo)}</span>'
            f'<strong>{html.escape(valor)}</strong></div>')


def render_ticket_page(tp, *, pdf_url: str, operadora: str = "", emergencia: str = "") -> str:
    """A pagina de um bilhete. Tudo embutido, nada a ir buscar."""
    gc = tp.guest_checkout
    partida = ""
    if tp.departure_at:
        from django.utils import timezone

        local = tp.departure_at.astimezone(timezone.get_current_timezone())
        partida = local.strftime("%d/%m/%Y as %H:%M")

    preco = f"{tp.fare_amount} MZN"
    if tp.display_currency and tp.display_currency != "MZN" and tp.display_fare_amount:
        preco = f"{tp.display_fare_amount} {tp.display_currency} ({tp.fare_amount} MZN)"

    valido = tp.status == "active"
    return f"""<!doctype html>
<html lang="pt"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#071E49">
<title>Bilhete {html.escape(tp.short_code or "")}</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;padding:14px;background:#071E49;color:#15191E;
font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
.c{{max-width:420px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden}}
.h{{background:#071E49;color:#fff;padding:14px 16px}}
.h b{{display:block;font-size:15px;letter-spacing:.3px}}
.h span{{font-size:12px;opacity:.75}}
.q{{padding:18px 16px 8px;text-align:center}}
.qr{{width:min(62vw,230px);height:auto;display:block;margin:0 auto}}
.code{{margin-top:10px;font-size:26px;font-weight:800;letter-spacing:4px}}
.st{{display:inline-block;margin-top:6px;padding:3px 12px;border-radius:999px;
font-size:11px;font-weight:800;letter-spacing:.6px;
background:{"#E6F6EC" if valido else "#FDEAEA"};color:{"#1B7F3B" if valido else "#B3261E"}}}
.b{{padding:6px 16px 16px}}
.l{{display:flex;justify-content:space-between;gap:12px;padding:9px 0;
border-top:1px solid #EEF1F5;font-size:13.5px}}
.l span{{color:#6B7A8F}}
.l strong{{text-align:right;font-weight:700}}
.f{{padding:0 16px 18px}}
.f a{{display:block;text-align:center;padding:12px;border-radius:10px;
background:#F2F5F9;color:#1D5FA7;text-decoration:none;font-weight:700;font-size:13.5px}}
.e{{margin-top:10px;text-align:center;font-size:12px;color:#6B7A8F}}
.e a{{color:#1D5FA7}}
</style></head><body>
<div class="c">
  <div class="h">
    <b>{html.escape(tp.route_name or tp.route_code or "Bilhete")}</b>
    <span>{html.escape(operadora or "")}</span>
  </div>
  <div class="q">
    {_qr_svg(tp.token if hasattr(tp, "token") else "")}
    <div class="code">{html.escape(tp.short_code or "")}</div>
    <div class="st">{"VALIDO" if valido else "NAO VALIDO"}</div>
  </div>
  <div class="b">
    {_linha("Percurso", f"{tp.origin_stop} -> {tp.destination_stop}" if tp.origin_stop else "")}
    {_linha("Partida", partida)}
    {_linha("Passageiro", tp.passenger_name)}
    {_linha("Documento", tp.document_number)}
    {_linha("Lugar", tp.seat_number)}
    {_linha("Preco", preco)}
    {_linha("Referencia", gc.reference if gc else "")}
  </div>
  <div class="f">
    <a href="{html.escape(pdf_url)}">Descarregar o bilhete em PDF</a>
    {f'<div class="e">Emergencia: <a href="tel:{html.escape(emergencia)}">{html.escape(emergencia)}</a></div>' if emergencia else ""}
  </div>
</div>
</body></html>"""
