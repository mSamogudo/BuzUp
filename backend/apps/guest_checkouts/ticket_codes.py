from __future__ import annotations

# Comprimento do codigo curto que o passageiro le em voz alta quando o QR nao
# passa (chuva, ecra rachado, camara suja).
#
# Eram 4 caracteres. A referencia e `GC-` + hex do uuid4, ou seja o alfabeto e
# `0-9A-F` e nao as 36 letras e digitos: 4 caracteres davam 16^4 = 65 536
# codigos. A procura e feita dentro da mesma viagem, e num autocarro com 60
# bilhetes a probabilidade de dois partilharem o codigo andava perto de 3%.
# Quando isso acontece a validacao nao valida o bilhete errado — recusa os dois
# — e um passageiro com bilhete valido fica em terra. Com 6 caracteres o espaco
# passa a 16^6 = 16,7 milhoes e o caso deixa de ser realista.
#
# Os bilhetes antigos ficam com o codigo de 4 que ja lhes foi impresso; a
# validacao aceita os dois comprimentos (ver `find_pass_by_token_or_short_code`).
SHORT_CODE_LENGTH = 6


def ticket_short_code(reference: str, length: int = SHORT_CODE_LENGTH) -> str:
    value = "".join(ch for ch in str(reference or "").upper() if ch.isalnum())
    return value[-length:]


def ticket_reference(travel_pass, sequence: int | None = None, total: int | None = None) -> str:
    guest_checkout = getattr(travel_pass, "guest_checkout", None)
    if guest_checkout:
        base_reference = guest_checkout.reference
    else:
        base_reference = str(getattr(travel_pass, "uuid", ""))[:12].upper()

    if not guest_checkout:
        return base_reference

    ticket_total = total if total is not None else _ticket_total(travel_pass)
    if ticket_total <= 1:
        return base_reference

    ticket_sequence = sequence if sequence is not None else _ticket_sequence(travel_pass)
    width = max(2, len(str(ticket_total)))
    return f"{base_reference}-{ticket_sequence:0{width}d}"


def _ticket_total(travel_pass) -> int:
    guest_checkout = getattr(travel_pass, "guest_checkout", None)
    if not guest_checkout:
        return 1
    if getattr(guest_checkout, "quantity", 1) > 1:
        return guest_checkout.quantity
    guest_checkout_id = getattr(travel_pass, "guest_checkout_id", None)
    if not guest_checkout_id:
        return 1
    return travel_pass.__class__.objects.filter(guest_checkout_id=guest_checkout_id).count()


def _ticket_sequence(travel_pass) -> int:
    guest_checkout_id = getattr(travel_pass, "guest_checkout_id", None)
    if not guest_checkout_id or not getattr(travel_pass, "pk", None):
        return 1

    ids = travel_pass.__class__.objects.filter(
        guest_checkout_id=guest_checkout_id,
    ).order_by("created_at", "id").values_list("id", flat=True)
    for index, travel_pass_id in enumerate(ids, start=1):
        if travel_pass_id == travel_pass.id:
            return index
    return 1
