from __future__ import annotations


def ticket_short_code(reference: str) -> str:
    value = "".join(ch for ch in str(reference or "").upper() if ch.isalnum())
    return value[-4:]


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
