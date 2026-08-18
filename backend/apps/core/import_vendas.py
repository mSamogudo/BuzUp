"""Carregar para a plataforma as vendas que ja aconteceram.

O operador traz anos de bilhetes vendidos noutro sistema (ou em papel) e quer
o historico dentro da plataforma: para os relatorios fecharem, para saber quem
viajou e quanto se facturou antes de a plataforma existir.

Tres cuidados que fazem a diferenca entre um historico e uma confusao:

1. **Um bilhete historico nao viaja.** Nasce `usado`, com a data em que foi
   usado e a validade expirada. Se nascesse activo, cada linha importada era um
   bilhete gratuito que alguem podia apresentar a bordo.

2. **Repetir o ficheiro nao duplica.** A referencia do operador e a chave: a
   segunda importacao da mesma linha e contada como "ja existia". Sem isto,
   carregar o ficheiro outra vez por engano dobrava a receita nos relatorios —
   e ninguem repararia ate ao fecho do mes.

3. **Nao se contacta ninguem.** Nao ha SMS, nao ha gateway de pagamento. Estas
   vendas ja foram cobradas; toca-lhes de novo seria cobrar a quem ja pagou e
   escrever a quem ja viajou.
"""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.core.import_csv import parse_excel_upload

#: Prefixo da referencia. Uma venda historica nunca se confunde com uma real —
#: nem numa listagem, nem numa procura, nem por acidente.
PREFIXO = "HIST"

VENDAS_HEADER_MAP = {
    "referencia": "reference", "referência": "reference", "reference": "reference",
    "ref": "reference", "numero do bilhete": "reference", "nº bilhete": "reference",
    "data": "date", "date": "date", "data da viagem": "date",
    "rota": "route", "route": "route", "codigo da rota": "route", "código da rota": "route",
    "origem": "origin", "origin": "origin",
    "destino": "destination", "destination": "destination",
    "passageiro": "passenger_name", "nome": "passenger_name", "passenger": "passenger_name",
    "documento": "document_number", "document": "document_number", "bi": "document_number",
    "telefone": "phone", "telemovel": "phone", "telemóvel": "phone", "phone": "phone",
    "valor": "amount", "preco": "amount", "preço": "amount", "amount": "amount",
    "metodo": "method", "método": "method", "pagamento": "method", "method": "method",
    "lugar": "seat", "assento": "seat", "seat": "seat",
}

OBRIGATORIOS = ["reference", "date", "amount"]

#: Como o operador escreve o meio de pagamento -> o que fica registado.
METODOS = {
    "dinheiro": "cash", "cash": "cash", "numerario": "cash", "numerário": "cash",
    "mpesa": "mpesa", "m-pesa": "mpesa", "m pesa": "mpesa",
    "emola": "emola", "e-mola": "emola", "e mola": "emola",
    "cartao": "card", "cartão": "card", "card": "card",
    "transferencia": "transfer", "transferência": "transfer", "transfer": "transfer",
}


def _data(valor: str):
    """Aceita o que o Excel e as pessoas escrevem, e diz nao ao resto."""
    texto = str(valor or "").strip()
    if not texto:
        return None
    # O openpyxl entrega datas como "2026-08-18 00:00:00".
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y",
                    "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _valor(bruto: str) -> Decimal | None:
    texto = str(bruto or "").strip().replace(" ", "")
    if not texto:
        return None
    # "1.500,00" e "1500.00" sao ambos escritos por gente real.
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        return None
    return valor if valor > 0 else None


def import_vendas_historicas(file_content: bytes) -> dict:
    from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
    from apps.guest_checkouts.ticket_codes import ticket_reference, ticket_short_code
    from apps.payments.models import PaymentIntent
    from apps.routes.models import Route

    linhas, erros = parse_excel_upload(file_content, OBRIGATORIOS, header_map=VENDAS_HEADER_MAP)
    importadas = repetidas = 0
    total = Decimal("0.00")

    rotas_por_codigo = {r.code.upper(): r for r in Route.all_objects.all() if r.code}
    rotas_por_nome = {r.name.strip().lower(): r for r in Route.all_objects.all()}

    for i, linha in enumerate(linhas, start=2):
        bruta = str(linha["reference"]).strip()
        referencia = f"{PREFIXO}-{bruta.upper()}"

        if GuestCheckout.all_objects.filter(reference=referencia).exists():
            repetidas += 1
            continue

        data = _data(linha["date"])
        if data is None:
            erros.append({"row": i, "detail": f"Data invalida: {linha['date']!r}."})
            continue

        valor = _valor(linha["amount"])
        if valor is None:
            erros.append({"row": i, "detail": f"Valor invalido: {linha['amount']!r}."})
            continue

        chave_rota = str(linha.get("route") or "").strip()
        rota = (rotas_por_codigo.get(chave_rota.upper())
                or rotas_por_nome.get(chave_rota.lower())) if chave_rota else None
        if chave_rota and rota is None:
            erros.append({"row": i, "detail": f"Rota '{chave_rota}' nao existe na plataforma."})
            continue

        # A viagem aconteceu naquele dia: guarda-se o fim do dia para a partida
        # e a validade, que e o que faz o bilhete estar expirado hoje.
        momento = timezone.make_aware(
            datetime.combine(data, time(23, 59)), timezone.get_current_timezone())

        with transaction.atomic():
            checkout = GuestCheckout.objects.create(
                reference=referencia,
                payer_phone=str(linha.get("phone") or "").strip(),
                buyer_name=str(linha.get("passenger_name") or "").strip()[:255],
                route_code=rota.code if rota else chave_rota[:32],
                route_name=rota.name if rota else "",
                origin_stop=str(linha.get("origin") or "").strip()[:255],
                destination_stop=str(linha.get("destination") or "").strip()[:255],
                quantity=1,
                unit_amount=valor,
                total_amount=valor,
                status=GuestCheckout.Status.ISSUED,
            )
            cru, resumo = DigitalTravelPass.generate_token()
            bilhete = DigitalTravelPass.objects.create(
                guest_checkout=checkout,
                payer_phone=checkout.payer_phone,
                passenger_name=checkout.buyer_name,
                document_number=str(linha.get("document_number") or "").strip()[:64],
                seat_number=str(linha.get("seat") or "").strip()[:8],
                route_code=checkout.route_code,
                route_name=checkout.route_name,
                origin_stop=checkout.origin_stop,
                destination_stop=checkout.destination_stop,
                departure_at=momento,
                fare_amount=valor,
                token=cru, token_hash=resumo,
                # Nasce USADO: uma venda historica e uma viagem que ja
                # aconteceu. Activo, cada linha importada seria um bilhete
                # gratuito que alguem podia apresentar a bordo.
                status=DigitalTravelPass.Status.USED,
                valid_from=momento,
                valid_until=momento,
                used_at=momento,
            )
            bilhete.short_code = ticket_short_code(ticket_reference(bilhete))
            bilhete.save(update_fields=["short_code", "updated_at"])

            metodo = METODOS.get(str(linha.get("method") or "").strip().lower(), "")
            PaymentIntent.objects.create(
                reference=f"PAY-{referencia}",
                idempotency_key=f"import-{referencia}",
                purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
                amount=valor,
                payer_phone=checkout.payer_phone,
                provider=metodo,
                channel="import",
                status=PaymentIntent.Status.CONFIRMED,
                guest_checkout=checkout,
                confirmed_at=momento,
                metadata={"historico": True, "referencia_origem": bruta},
            )
            # A data em que a venda ENTRA nos relatorios tem de ser a da venda,
            # nao a do dia em que se carregou o ficheiro. `auto_now_add` ignora
            # o que se passe no create(), por isso corrige-se logo a seguir.
            GuestCheckout.objects.filter(pk=checkout.pk).update(created_at=momento)
            PaymentIntent.objects.filter(guest_checkout=checkout).update(created_at=momento)
            DigitalTravelPass.objects.filter(pk=bilhete.pk).update(created_at=momento)

        importadas += 1
        total += valor

    return {
        "imported": importadas,
        "duplicates": repetidas,
        "total_amount": str(total),
        "errors": erros,
    }
