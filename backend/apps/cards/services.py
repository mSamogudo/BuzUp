from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.cards.models import Card
from apps.passengers.models import PassengerAccount
from apps.wallets.models import Wallet


class CardError(Exception):
    pass


def activate_card(card: Card) -> Card:
    if card.status != Card.Status.INACTIVE:
        raise CardError(f"Cartao {card.card_number} nao pode ser activado no estado {card.status}.")

    with transaction.atomic():
        card = Card.objects.select_for_update().get(pk=card.pk)
        if not card.wallet:
            passenger = PassengerAccount.objects.create(
                full_name=f"Cartao {card.card_number}",
                phone_number="",
                status=PassengerAccount.Status.ACTIVE,
            )
            wallet = Wallet.objects.create(passenger_account=passenger)
            card.wallet = wallet
            card.passenger_account = passenger

        card.status = Card.Status.ACTIVE
        card.activated_at = timezone.now()
        card.save(update_fields=["status", "activated_at", "wallet", "passenger_account", "updated_at"])

    return card


def create_digital_card(passenger: PassengerAccount) -> Card:
    wallet = getattr(passenger, "wallet", None)
    if not wallet:
        wallet = Wallet.objects.create(passenger_account=passenger)

    card = Card.objects.create(
        card_type=Card.CardType.DIGITAL,
        passenger_account=passenger,
        wallet=wallet,
        status=Card.Status.ACTIVE,
        activated_at=timezone.now(),
    )
    return card


def assign_card_to_passenger(card: Card, passenger: PassengerAccount, notify_sms: bool = True) -> Card:
    """Assign a card to a passenger.

    Pass `notify_sms=False` when the caller wants to send the notification at
    a later moment (e.g. after a deferred payment confirmation in the card
    recovery flow). Default behaviour preserves backwards-compat: the SMS is
    sent immediately for direct admin assignment.
    """
    if card.status != Card.Status.INACTIVE:
        raise CardError(f"Cartao {card.card_number} deve estar inactivo para atribuir.")

    with transaction.atomic():
        card = Card.objects.select_for_update().get(pk=card.pk)
        wallet = getattr(passenger, "wallet", None)
        if not wallet:
            wallet = Wallet.objects.create(passenger_account=passenger)

        card.passenger_account = passenger
        card.wallet = wallet
        card.status = Card.Status.ACTIVE
        card.activated_at = timezone.now()
        card.save(update_fields=["passenger_account", "wallet", "status", "activated_at", "updated_at"])

    if notify_sms and passenger.phone_number:
        try:
            from apps.sms.services.sender import send_sms
            send_sms(passenger.phone_number, f"BusUp: Cartao {card.card_number} activado e vinculado a sua conta.", purpose="CARD_ASSIGNED")
        except Exception:
            pass

    return card


def block_card(card: Card) -> Card:
    if card.status != Card.Status.ACTIVE:
        raise CardError(f"Cartao {card.card_number} nao pode ser bloqueado no estado {card.status}.")

    card.status = Card.Status.BLOCKED
    card.blocked_at = timezone.now()
    card.save(update_fields=["status", "blocked_at", "updated_at"])
    return card


def replace_card(old_card: Card, new_card: Card) -> Card:
    if old_card.status not in (Card.Status.ACTIVE, Card.Status.BLOCKED, Card.Status.LOST):
        raise CardError(f"Cartao {old_card.card_number} nao pode ser substituido no estado {old_card.status}.")
    if new_card.status != Card.Status.INACTIVE:
        raise CardError(f"Cartao substituto {new_card.card_number} deve estar inactivo.")

    with transaction.atomic():
        old_card = Card.objects.select_for_update().get(pk=old_card.pk)
        new_card = Card.objects.select_for_update().get(pk=new_card.pk)

        new_card.wallet = old_card.wallet
        new_card.passenger_account = old_card.passenger_account
        new_card.status = Card.Status.ACTIVE
        new_card.activated_at = timezone.now()
        new_card.save(update_fields=["wallet", "passenger_account", "status", "activated_at", "updated_at"])

        old_card.status = Card.Status.REPLACED
        old_card.replaced_by = new_card
        old_card.save(update_fields=["status", "replaced_by", "updated_at"])

    return new_card


def link_card_to_passenger(card: Card, passenger: PassengerAccount) -> Card:
    if card.status != Card.Status.ACTIVE:
        raise CardError(f"Cartao {card.card_number} deve estar activo para vincular.")

    with transaction.atomic():
        card = Card.objects.select_for_update().get(pk=card.pk)
        wallet = getattr(passenger, "wallet", None)
        if not wallet:
            wallet = Wallet.objects.create(passenger_account=passenger)

        card.passenger_account = passenger
        card.wallet = wallet
        card.save(update_fields=["passenger_account", "wallet", "updated_at"])

    return card
