from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.sms.services.sender import send_sms


def issue_guest_pass(guest_checkout: GuestCheckout) -> list[DigitalTravelPass]:
    passes = []
    with transaction.atomic():
        gc = GuestCheckout.objects.select_for_update().get(pk=guest_checkout.pk)
        if gc.status == GuestCheckout.Status.ISSUED:
            return list(gc.travel_passes.all())

        gc.status = GuestCheckout.Status.ISSUED
        gc.save(update_fields=["status", "updated_at"])

        for _ in range(gc.quantity):
            raw_token, token_hash = DigitalTravelPass.generate_token()
            travel_pass = DigitalTravelPass.objects.create(
                guest_checkout=gc,
                payer_phone=gc.payer_phone,
                route_code=gc.route_code,
                route_name=gc.route_name,
                origin_stop=gc.origin_stop,
                destination_stop=gc.destination_stop,
                origin_stop_ref=gc.origin_stop_ref,
                destination_stop_ref=gc.destination_stop_ref,
                trip=gc.trip,
                fare_amount=gc.unit_amount,
                token=raw_token,
                token_hash=token_hash,
                delivery_channel=DigitalTravelPass.DeliveryChannel.SMS,
                valid_from=timezone.now(),
                valid_until=timezone.now() + timedelta(hours=24),
            )
            travel_pass._raw_token = raw_token
            passes.append(travel_pass)

    for p in passes:
        _deliver_pass_sms(gc, p)

    return passes


def _deliver_pass_sms(gc: GuestCheckout, travel_pass: DigitalTravelPass):
    raw_token = getattr(travel_pass, "_raw_token", None)
    if not raw_token:
        return
    base = str(getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/")
    ticket_url = f"{base}/api/public/ticket/{raw_token}/" if base else f"/api/public/ticket/{raw_token}/"
    message = (
        f"BusUp: Bilhete {gc.route_name or gc.route_code} "
        f"{gc.origin_stop} -> {gc.destination_stop}. "
        f"Ref: {gc.reference}. "
        f"Link: {ticket_url}"
    )
    send_sms(gc.payer_phone, message, purpose="GUEST_PASS_DELIVERY")
