"""PDF + Excel renderers for the unified report builder.

Both renderers share the BuzUp / TPM-TUR / UpDigital branding used in the
agent revenue admin exports (see `apps.agent_api.exporters`). We deliberately
mirror the look and feel so the operator gets consistent reports across all
admin areas.
"""
from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

NAVY = colors.HexColor("#071E49")
ORANGE = colors.HexColor("#E47B11")
GREY = colors.HexColor("#6B6356")
LIGHT_GREY = colors.HexColor("#E7E1D4")
SOFT_BG = colors.HexColor("#F7F4EE")


def _asset(*parts):
    return Path(settings.BASE_DIR) / "static" / "assets" / Path(*parts)


def _safe_image(path: Path):
    try:
        if path.exists():
            return ImageReader(str(path))
    except Exception:
        return None
    return None


def _branding_image(field_name: str):
    """ImageReader do logo configurado no portal (apps.branding), ou None.

    Permite que os relatorios usem os logos carregados pelo gestor, caindo para
    os ficheiros estaticos quando nenhum logo foi definido.
    """
    try:
        from apps.branding.models import BrandingSettings

        f = getattr(BrandingSettings.load(), field_name, None)
        if not f or not f.name:
            return None
        try:
            return _safe_image(Path(f.path))
        except (NotImplementedError, ValueError):
            f.open("rb")
            try:
                return ImageReader(io.BytesIO(f.read()))
            finally:
                f.close()
    except Exception:
        return None


#: Os estados, por escrito. Vivem AQUI e nao no construtor de linhas porque o
#: ecra ja os traduz — e usa o valor cru para escolher a cor do distintivo.
#: Traduzir a montante pintava tudo de cinzento.
#:
#: Num PDF nao ha distintivo nenhum: sai o que la estiver escrito, e
#: `confirmed` nao diz nada a quem fecha as contas do mes.
# Cada rotulo diz, entre parenteses, o que aquela linha faz ao dinheiro. E a
# unica coluna que separa receita de nao-receita neste relatorio, e sair de la
# «guest_digital_travel_pass» obrigava quem le a saber o modelo de dados.
TIPOS_DE_VALIDACAO = {
    "card_pay_as_you_go": "Cartao (pago a bordo)",
    "qr_pay_as_you_go": "QR (pago a bordo)",
    "digital_travel_pass": "Passe da app (ja pago)",
    "guest_digital_travel_pass": "Bilhete (ja pago)",
}


ESTADOS = {
    "confirmed": "Confirmado", "pending": "Pendente", "failed": "Falhado",
    "cancelled": "Cancelado", "expired": "Expirado", "refunded": "Reembolsado",
    "active": "Activo", "used": "Usado", "approved": "Aprovado",
    "denied": "Recusado", "issued": "Emitido", "paid": "Pago",
    "created": "Criado", "reversed": "Revertido", "draft": "Rascunho",
}


#: Totais que sao contagens, nao dinheiro. Tudo o resto que apareca num cartao
#: e dinheiro e tem de sair formatado — a regra e esta e nao uma lista de
#: sufixos, porque um total novo com um nome novo saia como «30387.80», cru, ao
#: lado de «6 184,00 MZN». Quem le nao tem de adivinhar que sao a mesma moeda.
CONTAGENS = {"count", "confirmed_count", "approved_count", "quantity"}


def _e_dinheiro(key: str) -> bool:
    if key in CONTAGENS or key.endswith("_count"):
        return False
    return (
        key.endswith("amount")
        or key.endswith("debited")
        or key.endswith("embarcado")
        or key.startswith("total")
        or key in {"valor", "total"}
    )


def _apresentar(key: str, value, *, para: str = "pdf"):
    """O valor como ele deve aparecer no documento.

    Um unico sitio a decidir isso, para o PDF e o Excel nunca discordarem —
    que e como se descobre, tarde, que o Excel dizia «confirmed» e o PDF
    «Confirmado» para a mesma linha.

    **O dinheiro e a excepcao, e e deliberada.** No PDF vai formatado («1
    650,00»), porque la o que conta e ler. No Excel vai como NUMERO, com o
    formato aplicado a celula: formatar o dinheiro em texto deixava a folha
    bonita e impossivel de somar — e somar a coluna e a primeira coisa que
    quem recebe a folha vai fazer.
    """
    if key == "validation_type" and isinstance(value, str):
        return TIPOS_DE_VALIDACAO.get(value.strip(), value.replace("_", " ").capitalize())
    if key == "status" and isinstance(value, str):
        v = value.strip()
        return ESTADOS.get(v.lower(), v.replace("_", " ").capitalize() if v else "—")
    if _e_dinheiro(key) and value not in (None, ""):
        if para == "xlsx":
            try:
                return float(Decimal(str(value)))
            except (InvalidOperation, ValueError, TypeError):
                return value
        # Sem a moeda: ela esta no cabecalho da coluna. Repetida em 62 linhas
        # so rouba largura ao numero.
        return _dinheiro(value).removesuffix(" MZN")
    return value


def _stringify(value):
    if isinstance(value, datetime):
        # Hora de MAPUTO, nao UTC.
        #
        # O `strftime` numa data com fuso escreve o fuso que a data traz — e o
        # Django guarda tudo em UTC. O PDF mostrava a partida das 05:00 como
        # «03:00» e a das 15:30 como «13:30»: o horario inteiro lido com duas
        # horas de atraso, num documento que o operador usa para saber a que
        # horas sai o autocarro.
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime("%d/%m/%Y %H:%M")
    if value is None:
        return ""
    return str(value)


_NUM_SUFFIXES = ("MZN", "MT", "%")


def _is_numeric_cell(txt: str) -> bool:
    """True para valores que devem ser alinhados a direita (numeros/moeda)."""
    s = txt.strip()
    if not s or not any(ch.isdigit() for ch in s):
        return False
    for suf in _NUM_SUFFIXES:
        if s.endswith(suf):
            s = s[: -len(suf)].strip()
            break
    core = s.replace(" ", "").replace(",", "").replace(".", "").replace("-", "").replace("+", "")
    return core.isdigit()


def _quebrar(c, txt: str, font: str, size: float, max_w: float, maximo: int = 4) -> list[str]:
    """O texto em linhas que cabem em `max_w`, sem partir palavras."""
    palavras = (txt or "").split()
    linhas: list[str] = []
    actual = ""
    for p in palavras:
        tentativa = f"{actual} {p}".strip()
        if c.stringWidth(tentativa, font, size) <= max_w:
            actual = tentativa
        else:
            if actual:
                linhas.append(actual)
            actual = p
            if len(linhas) == maximo - 1:
                # A ultima linha leva o resto, cortado se for preciso.
                resto = " ".join(palavras[palavras.index(p):])
                linhas.append(_fit_text(c, resto, font, size, max_w))
                return linhas
    if actual:
        linhas.append(actual)
    return linhas


def _fit_text(c, txt: str, font: str, size: float, max_w: float) -> str:
    """Corta com reticencias SO quando o texto realmente nao cabe em max_w."""
    if not txt or c.stringWidth(txt, font, size) <= max_w:
        return txt
    ell = "…"
    lo, hi = 0, len(txt)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if c.stringWidth(txt[:mid] + ell, font, size) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return (txt[:lo] + ell) if lo > 0 else ell


def _rotulo_de_coluna(key: str, label: str) -> str:
    """O titulo da coluna, com a moeda quando a coluna e de dinheiro.

    Assim o numero de cada linha fica limpo e continua a dizer-se em que
    moeda esta — que num relatorio que sai de Mocambique para uma fronteira
    nao e detalhe."""
    return f"{label} (MZN)" if _e_dinheiro(key) else label


def _draw_col_headers(c, x_left, y, columns, col_widths, line_h, width):
    c.setFillColor(NAVY)
    c.rect(x_left, y - line_h, width, line_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    x = x_left
    for (key, label), w in zip(columns, col_widths):
        c.drawString(x + 2, y - line_h + 1.5 * mm,
                     _fit_text(c, _rotulo_de_coluna(key, label), "Helvetica-Bold", 8, w - 4))
        x += w
    return y - line_h


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------



def _some_no_fundo(imagem, fundo=(0x07, 0x1E, 0x49), limite=0.22) -> bool:
    """Parte deste logotipo desaparece sobre a faixa azul-escura?

    A primeira versao disto media a luminancia MEDIA e deixava passar o
    logotipo da TPM-TUR: o simbolo e laranja e azul vivo, e a media dava
    «claro». Mas por baixo dele esta «TPM-TUR S.A. / TRANSPORTE E TURISMO»
    escrito em azul-escuro — e essa parte, sobre a faixa, nao se lia.

    Por isso nao se pergunta «este logotipo e claro?». Pergunta-se o que
    interessa: **que fracao dele fica indistinguivel do fundo?** Acima de 22%
    dos pixeis opacos, poe-se uma placa clara por tras.

    Em caso de duvida devolve True — a placa nunca esconde nada, e um
    logotipo sobre placa le-se sempre; sem placa, pode nao se ler.
    """
    try:
        im = getattr(imagem, "_image", None)
        if im is None:
            imagem.getSize()
            im = getattr(imagem, "_image", None)
        if im is None:
            return True

        im = im.convert("RGBA")
        px = im.load()
        passo_x = max(1, im.width // 60)
        passo_y = max(1, im.height // 60)
        perto = opacos = 0
        for y in range(0, im.height, passo_y):
            for x in range(0, im.width, passo_x):
                r, g, b, a = px[x, y]
                if a <= 40:
                    continue
                opacos += 1
                # Distancia ao fundo, normalizada. Perto = confunde-se.
                d = ((r - fundo[0]) ** 2 + (g - fundo[1]) ** 2 + (b - fundo[2]) ** 2) ** 0.5
                if d < 110:
                    perto += 1
        return (perto / opacos) > limite if opacos else True
    except Exception:
        return True


def _load_logos() -> dict:
    """Logótipos do cabeçalho e do rodapé, lidos UMA vez por documento.

    Um relatório no tecto tem 193 páginas e o logótipo é desenhado em todas.
    Sem isto, cada página reabria e descodificava o PNG e o reportlab voltava
    a hashá-lo em MD5 para o deduplicar: eram 12,8 dos 16,3 segundos do
    relatório, com um dos dois workers preso todo esse tempo. Lidos aqui, o
    reportlab reconhece o mesmo objecto e reaproveita-o.
    """
    # O logotipo do cabecalho desenha-se sobre uma faixa azul-escura, e pode
    # vir de onde o gestor quiser — o portal aceita qualquer arte. Em vez de
    # adivinhar, mede-se: se uma parte dele se confundir com o fundo, leva
    # uma placa clara por tras. Ver `_some_no_fundo`.
    cabecalho = (
        _branding_image("report_logo")
        or _branding_image("primary_logo")
        or _safe_image(_asset("tpm-tur-logo", "tpm_dark.png"))
        or _safe_image(_asset("tpm-tur-logo", "tpm_light.png"))
    )
    return {
        "header": cabecalho,
        "header_precisa_de_placa": bool(cabecalho) and _some_no_fundo(cabecalho),
        "footer": (
            _branding_image("powered_by_logo")
            or _safe_image(_asset("up-digital-logo", "up_digital_dark.png"))
            or _safe_image(_asset("up-digital-logo", "up_digital_light.png"))
        ),
    }



#: Colunas que NUNCA podem sair cortadas.
#:
#: «1650…» num relatorio financeiro nao e um numero mais curto — e outro
#: numero. O mesmo para uma data: «2026-09-2…» nao se sabe se e 25 ou 29.
#: Estas recebem a largura de que precisam antes de as outras repartirem o
#: que sobra.
def _e_intocavel(key: str) -> bool:
    return (
        key.endswith("amount")
        or key.endswith("_at")
        # `payer` e curto e fixo — «***6613», sete caracteres — mas ficava com
        # o que sobrasse e saia «***6…», que nao identifica ninguem. Uma coluna
        # que nao se le ocupa espaco e nao vale nada; ou cabe, ou nao devia la
        # estar. Reservar-lhe a largura exacta custa quase nada as outras.
        or key in {"created_at", "quantity", "status", "method", "valor",
                   "total", "payer", "documento", "validation_type"}
    )


def _larguras_das_colunas(c, columns, sample, avail):
    """Reparte a largura da pagina pelas colunas.

    Antes era tudo proporcional ao comprimento do conteudo, com tecto de 30
    caracteres. Numa pagina com doze colunas, as referencias — que chegam ao
    tecto — ficavam com a maior fatia e o dinheiro com o que sobrasse: saia
    «1650…» e «3300…».

    Agora as colunas intocaveis levam o que precisam primeiro. O resto
    reparte o que sobra, e sao essas que encolhem — uma referencia cortada
    ainda se reconhece pelo principio; um valor cortado, nao.
    """
    fonte, tamanho, folga = "Helvetica", 8, 10
    minimos, pesos = [], []

    for key, label in columns:
        mais_largo = max(
            [c.stringWidth(_stringify(_apresentar(key, r.get(key))), fonte, tamanho)
             for r in sample] or [0.0]
        )
        preciso = max(mais_largo,
                      c.stringWidth(_rotulo_de_coluna(key, label), "Helvetica-Bold", tamanho)) + folga
        minimos.append(preciso if _e_intocavel(key) else 0.0)
        pesos.append(min(max(len(label), 6), 30) if _e_intocavel(key) else
                     min(max(len(label), _maior_texto(sample, key), 6), 30))

    reservado = sum(minimos)
    if reservado >= avail:
        # Nem as intocaveis cabem: ha colunas a mais para uma A4. Reparte-se
        # tudo por proporcao e o utilizador que escolha menos colunas — e
        # para isso que a escolha de colunas existe.
        total = sum(pesos) or 1
        return [avail * (w / total) for w in pesos]

    sobra = avail - reservado
    pesos_livres = [w if m == 0.0 else 0.0 for w, m in zip(pesos, minimos)]
    total_livre = sum(pesos_livres) or 1
    return [
        m if m > 0.0 else sobra * (w / total_livre)
        for m, w in zip(minimos, pesos_livres)
    ]


def _maior_texto(sample, key) -> int:
    return max([len(_stringify(_apresentar(key, r.get(key)))) for r in sample] or [0])


def render_pdf(
    title: str,
    period_from: str,
    period_to: str,
    columns: list[tuple[str, str]],
    rows: list[dict],
    totals: dict | None = None,
    filters_summary: str = "",
    escopo: str = "",
) -> bytes:
    buf = io.BytesIO()
    page = landscape(A4)
    width, height = page
    c = canvas.Canvas(buf, pagesize=page)
    logos = _load_logos()

    _draw_header(c, width, height, title=title, period_from=period_from,
                 period_to=period_to, logos=logos)

    y = height - 32 * mm

    if filters_summary:
        c.setFillColor(GREY)
        c.setFont("Helvetica", 9)
        c.drawString(10 * mm, y, f"Filtros: {filters_summary}")
        y -= 5 * mm

    if totals:
        y = _draw_totals(c, width, y, totals)

    # O que este relatorio conta, e o que nao conta. Vai debaixo dos cartoes
    # porque e ali que a pergunta nasce: alguem le o total, compara com o
    # painel, e nao bate certo. A resposta tem de estar na mesma folha.
    if escopo:
        # Em linhas, e nao cortado com reticencias. O escopo deixou de ser uma
        # etiqueta e passou a ser um aviso — «nao some isto com aquele
        # relatorio» — e um aviso truncado a meio e pior do que nenhum.
        c.setFillColor(GREY)
        c.setFont("Helvetica-Oblique", 8)
        for linha in _quebrar(c, escopo, "Helvetica-Oblique", 8, width - 20 * mm):
            c.drawString(10 * mm, y, linha)
            y -= 4 * mm
        y -= 1 * mm

    sample = rows[:200]
    avail = width - 20 * mm
    col_widths = _larguras_das_colunas(c, columns, sample, avail)

    y = _draw_table(c, x_left=10 * mm, y=y, width=width - 20 * mm,
                   columns=columns, col_widths=col_widths,
                   rows=rows, page_size=page,
                   title=title, period_from=period_from, period_to=period_to,
                   logos=logos)

    _draw_footer(c, width, logos)
    c.save()
    return buf.getvalue()


def _draw_header(c, width, height, *, title, period_from, period_to, logos=None):
    band_h = 22 * mm
    c.setFillColor(NAVY)
    c.rect(0, height - band_h, width, band_h, fill=1, stroke=0)

    logo = (logos or {}).get("header") if logos is not None else (
        _branding_image("report_logo")
        or _branding_image("primary_logo")
        or _safe_image(_asset("tpm-tur-logo", "tpm_dark.png"))
        or _safe_image(_asset("tpm-tur-logo", "tpm_light.png"))
    )
    if logo:
        try:
            iw, ih = logo.getSize()
            # A largura NAO pode ser livre: escalava-se so pela altura, e um
            # logotipo comprido — o carregado no portal pode ter qualquer
            # proporcao — entrava por cima do titulo, que comeca aos 60mm.
            #
            # A caixa e de 13mm de alto por 42mm de largo, e o logo cabe nela
            # sem deformar: encolhe pelo lado que primeiro toca no limite.
            caixa_h, caixa_w = 13 * mm, 42 * mm
            escala = min(caixa_w / iw, caixa_h / ih)
            target_w, target_h = iw * escala, ih * escala
            x = 8 * mm
            y = height - band_h + (band_h - target_h) / 2

            # A placa. Existe porque o logotipo da TPM-TUR tem o simbolo
            # colorido mas a razao social escrita em azul-escuro — que sobre a
            # faixa, tambem azul-escura, desaparecia. Com a placa, qualquer
            # arte que o gestor carregue le-se.
            if (logos or {}).get("header_precisa_de_placa"):
                folga = 2 * mm
                c.setFillColor(colors.white)
                c.setStrokeColor(colors.white)
                c.roundRect(x - folga, y - folga,
                            target_w + 2 * folga, target_h + 2 * folga,
                            2 * mm, fill=1, stroke=0)

            c.drawImage(logo, x, y, width=target_w, height=target_h, mask="auto")
        except Exception:
            pass

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(60 * mm, height - 10 * mm, "BuzUp | Relatorio Administrativo")
    c.setFont("Helvetica", 9)
    c.drawString(60 * mm, height - 15 * mm, "TPM-TUR S.A. | Transporte cashless de Mocambique")

    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(width - 10 * mm, height - 10 * mm, title)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 8)
    # Nem todos os documentos que usam este cabecalho tem periodo (o manifesto
    # de bordo e de uma partida, nao de um intervalo); sem isto saia
    # "Periodo:  - " a seco.
    gerado = f"Gerado {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    periodo = f"Periodo: {period_from} - {period_to} | " if (period_from or period_to) else ""
    c.drawRightString(width - 10 * mm, height - 15 * mm, f"{periodo}{gerado}")


#: Os totais, por escrito e em portugues. As chaves vinham do dicionario do
#: construtor e sairiam como «CONFIRMED COUNT» — nome de variavel, num cartao
#: que e a primeira coisa que se le no documento.
ROTULOS_DE_TOTAL = {
    "count": "Linhas",
    "confirmed_count": "Confirmadas",
    "approved_count": "Aprovadas",
    "total_amount": "Total",
    "total_debited": "Cobrado a bordo",
    "total_embarcado": "Bilhetes embarcados",
}


def _rotulo_de_total(chave: str) -> str:
    return ROTULOS_DE_TOTAL.get(chave, chave.replace("_", " ").capitalize())


def _dinheiro(valor) -> str:
    """68650.00 → «68 650,00 MZN».

    Como se le em Mocambique: virgula decimal e espaco nos milhares. O cartao
    do topo dizia «68650.00» — um numero que quem fecha as contas tem de
    contar com o dedo para saber se sao sessenta e oito mil ou seiscentos e
    oitenta e seis.
    """
    try:
        n = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return str(valor)
    inteiro, _, decimal = f"{n:.2f}".partition(".")
    sinal, inteiro = ("-", inteiro[1:]) if inteiro.startswith("-") else ("", inteiro)
    grupos = []
    while len(inteiro) > 3:
        grupos.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    grupos.insert(0, inteiro)
    # Espaco NORMAL, e nao o fino inquebravel: as fontes base do PDF
    # (Helvetica) nao tem o glifo do U+202F e desenhavam um quadrado preto no
    # meio do numero — «68<quadrado>650,00».
    corpo = " ".join(grupos)
    return f"{sinal}{corpo},{decimal} MZN"


def _draw_totals(c, width, y, totals):
    """Os cartoes do topo.

    O texto estava encostado ao bordo de cima: o rotulo com a linha de base a
    6 pontos do topo — ou seja, com as maiusculas a sair fora — e o valor logo
    a seguir, deixando dois tercos do cartao vazios. Aqui o cartao tem uma
    margem que se ve, e o valor assenta no meio do espaco que sobra.
    """
    if not totals:
        return y

    box_w = (width - 20 * mm - (len(totals) - 1) * 4) / max(1, len(totals))
    box_h = 18 * mm
    margem = 4.5 * mm
    x = 10 * mm

    for chave, valor in totals.items():
        c.setStrokeColor(LIGHT_GREY)
        c.setFillColor(colors.white)
        c.roundRect(x, y - box_h, box_w, box_h, 4, fill=1, stroke=1)

        c.setFillColor(GREY)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(x + margem, y - margem - 2, _rotulo_de_total(chave).upper())

        # O valor encolhe se nao couber. Um total cortado a meio num cartao e
        # pior do que um total pequeno: «68 650,00» a sair «68 65» le-se como
        # outro numero.
        # `_e_dinheiro` e nao um teste proprio: era aqui que o cartao decidia o
        # formato por conta propria («amount» ou «debited» no nome), e por isso
        # o `total_embarcado` — que nao tem nem uma nem outra — saiu «30387.80»
        # ao lado de «6 184,00 MZN». Duas regras para a mesma pergunta acabam
        # sempre a responder coisas diferentes.
        texto = _dinheiro(valor) if _e_dinheiro(chave) else _stringify(valor)
        tamanho = 15
        largura_util = box_w - 2 * margem
        while tamanho > 8 and c.stringWidth(texto, "Helvetica-Bold", tamanho) > largura_util:
            tamanho -= 0.5
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", tamanho)
        c.drawString(x + margem, y - box_h + margem, texto)

        x += box_w + 4
    return y - box_h - 6 * mm


def _draw_table(c, *, x_left, y, width, columns, col_widths, rows, page_size,
                title="", period_from="", period_to="", logos=None):
    line_h = 6 * mm
    page_w, page_h = page_size
    # A quebra de pagina tem de respeitar o rodape (14mm) + uma linha.
    min_y = 14 * mm + line_h + 2 * mm

    y = _draw_col_headers(c, x_left, y, columns, col_widths, line_h, width)

    if not rows:
        c.setFillColor(GREY)
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(x_left + 4, y - 4 * mm, "Sem registos no periodo / filtros indicados.")
        return y - 8 * mm

    # Um relatorio no tecto tem 5000 linhas x 8 colunas = 40 000 celulas, e
    # cada uma media o texto com `stringWidth` — 13s de worker preso, e neste
    # servidor um worker preso e um dos dois que servem a operacao inteira.
    # Os valores repetem-se muito (estado, rota, tipo, datas do mesmo dia),
    # por isso guarda-se o resultado por (texto, largura da coluna). A cache
    # vive so durante este documento: nao ha risco de ficar desactualizada.
    cell_cache: dict[tuple[str, int, bool], tuple[str, bool]] = {}

    #: Colunas que NUNCA se alinham a direita, mesmo quando o valor so tem
    #: digitos. Um codigo de bilhete como «425692» nao e uma quantidade — e
    #: alinha-lo a direita, ao lado de «4B1DAA» a esquerda, faz a coluna
    #: parecer partida.
    nunca_a_direita = {"bilhete", "reference", "sale_reference", "card_uid",
                       "documento", "msisdn", "payer", "short_code"}

    def _cell(txt: str, w: float, key_col: str = ""):
        key = (txt, int(w), key_col in nunca_a_direita)
        hit = cell_cache.get(key)
        if hit is None:
            numerico = _is_numeric_cell(txt) and key_col not in nunca_a_direita
            hit = (_fit_text(c, txt, "Helvetica", 8, w - 4), numerico)
            cell_cache[key] = hit
        return hit

    for i, row in enumerate(rows):
        if y < min_y:
            _draw_footer(c, page_w, logos)
            c.showPage()
            _draw_header(c, page_w, page_h, title=title, period_from=period_from,
                         period_to=period_to, logos=logos)
            y = page_h - 30 * mm
            y = _draw_col_headers(c, x_left, y, columns, col_widths, line_h, width)

        if i % 2 == 1:
            c.setFillColor(SOFT_BG)
            c.rect(x_left, y - line_h, width, line_h, fill=1, stroke=0)
        c.setFillColor(NAVY)
        c.setFont("Helvetica", 8)
        x = x_left
        baseline = y - line_h + 1.8 * mm
        for (key, _), w in zip(columns, col_widths):
            fitted, numeric = _cell(_stringify(_apresentar(key, row.get(key))), w, key)
            if numeric:
                c.drawRightString(x + w - 2, baseline, fitted)
            else:
                c.drawString(x + 2, baseline, fitted)
            x += w
        y -= line_h
    return y - 4 * mm


def _draw_footer(c, width, logos=None):
    band_h = 14 * mm
    c.setFillColor(SOFT_BG)
    c.rect(0, 0, width, band_h, fill=1, stroke=0)
    up = (logos or {}).get("footer") if logos is not None else (
        _branding_image("powered_by_logo")
        or _safe_image(_asset("up-digital-logo", "up_digital_dark.png"))
        or _safe_image(_asset("up-digital-logo", "up_digital_light.png"))
    )
    c.setFillColor(GREY)
    c.setFont("Helvetica", 8)
    c.drawString(10 * mm, band_h / 2 - 2, "BuzUp | TPM-TUR S.A. | Documento gerado automaticamente.")

    if up:
        try:
            iw, ih = up.getSize()
            target_h = 7 * mm
            target_w = iw * target_h / ih
            x_logo = width - 8 * mm - target_w
            c.drawImage(up, x_logo, (band_h - target_h) / 2,
                       width=target_w, height=target_h, mask="auto")
            # «powered by» e a legenda do logo, por isso vai colada a ele e
            # alinhada pelo meio. Estava fixa a 10 mm da margem esquerda, numa
            # segunda linha debaixo do texto do rodape e a meia folha de
            # distancia do logo — a legendar coisa nenhuma.
            etiqueta = "powered by"
            c.setFont("Helvetica", 7)
            c.drawString(
                x_logo - 2 * mm - c.stringWidth(etiqueta, "Helvetica", 7),
                band_h / 2 - 2.5, etiqueta,
            )
        except Exception:
            # Sem logo nao se escreve a legenda: sozinha nao quer dizer nada.
            pass


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------

def render_xlsx(
    title: str,
    period_from: str,
    period_to: str,
    columns: list[tuple[str, str]],
    rows: list[dict],
    totals: dict | None = None,
    filters_summary: str = "",
    escopo: str = "",
) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumo"

    ws["A1"] = title
    ws["A1"].font = Font(size=14, bold=True, color="071E49")
    ws["A2"] = f"Periodo: {period_from} a {period_to}"
    ws["A3"] = f"Filtros: {filters_summary}" if filters_summary else ""
    ws["A4"] = f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    # O que este relatorio conta, e o que nao conta. Ver `render_pdf`.
    # (A4 ja era do «Gerado em» — escrever aqui por cima apagava-o.)
    ws["A5"] = escopo or ""

    if totals:
        ws["A6"] = "Totais"
        ws["A6"].font = Font(bold=True)
        for i, (label, value) in enumerate(totals.items(), start=7):
            ws.cell(row=i, column=1, value=label.replace("_", " ").upper()).font = Font(bold=True)
            ws.cell(row=i, column=2, value=value)
        ws.column_dimensions["A"].width = 32
        ws.column_dimensions["B"].width = 22

    # Data sheet
    data_ws = wb.create_sheet(title="Dados")
    head_fill = PatternFill("solid", fgColor="071E49")
    head_font = Font(bold=True, color="FFFFFF")
    border = Border(left=Side(style="thin", color="DDDDDD"),
                    right=Side(style="thin", color="DDDDDD"),
                    top=Side(style="thin", color="DDDDDD"),
                    bottom=Side(style="thin", color="DDDDDD"))

    for col_i, (key, label) in enumerate(columns, start=1):
        cell = data_ws.cell(row=1, column=col_i, value=_rotulo_de_coluna(key, label))
        cell.fill = head_fill
        cell.font = head_font
        cell.alignment = Alignment(horizontal="left", vertical="center")
        cell.border = border
        data_ws.column_dimensions[get_column_letter(col_i)].width = max(14, min(40, len(label) + 8))

    for r_i, row in enumerate(rows, start=2):
        for c_i, (key, _) in enumerate(columns, start=1):
            value = _apresentar(key, row.get(key), para="xlsx")
            if isinstance(value, datetime):
                # Hora local, como no PDF. Ver `_stringify`.
                if timezone.is_aware(value):
                    value = timezone.localtime(value)
                value = value.strftime("%d/%m/%Y %H:%M")
            elif isinstance(value, (Decimal,)):
                value = float(value)
            cell = data_ws.cell(row=r_i, column=c_i, value=value)
            cell.border = border
            if isinstance(value, (int, float)):
                cell.alignment = Alignment(horizontal="right")
                if _e_dinheiro(key):
                    # Numero a serio, com o formato mocambicano aplicado a
                    # celula. A folha soma-se; o ecra le-se.
                    cell.number_format = "#,##0.00"
    data_ws.freeze_panes = "A2"

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
