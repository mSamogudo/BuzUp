from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.cards.models import Card
from apps.passengers.models import PassengerAccount
from apps.wallets.models import Wallet


class CardError(Exception):
    pass


# Porque e que todas as guardas de estado aqui vivem DENTRO do `atomic`:
#
# Estava escrito ao contrario — lia-se `card.status` no objecto que chegava,
# levantava-se o erro, e so depois se abria a transaccao com
# `select_for_update`. Entre a leitura e o bloqueio ha uma janela, e o cartao
# e precisamente o sitio onde ela custa dinheiro:
#
#   duas atribuicoes do mesmo cartao a passageiros diferentes, ao mesmo tempo,
#   passavam as duas a guarda. A primeira atribuia-o ao A e mandava-lhe SMS a
#   dizer que o cartao era dele; a segunda ficava com a ultima palavra e punha
#   a carteira do B. O A tinha a confirmacao no telemovel e um cartao que
#   descontava da conta de outra pessoa.
#
# O mesmo em `replace_card`: duas substituicoes do mesmo cartao deixavam dois
# cartoes activos a apontar para a mesma carteira.
#
# Ler o estado da LINHA BLOQUEADA fecha a janela: a segunda chamada so le
# depois de a primeira ter gravado, e ve o estado ja mudado.


def activate_card(card: Card) -> Card:
    with transaction.atomic():
        card = Card.objects.select_for_update().get(pk=card.pk)
        if card.status != Card.Status.INACTIVE:
            raise CardError(f"Cartao {card.card_number} nao pode ser activado no estado {card.status}.")
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
    with transaction.atomic():
        card = Card.objects.select_for_update().get(pk=card.pk)
        if card.status != Card.Status.INACTIVE:
            raise CardError(f"Cartao {card.card_number} deve estar inactivo para atribuir.")
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
            send_sms(passenger.phone_number, f"BuzUp: Cartao {card.card_number} activado e vinculado a sua conta.", purpose="CARD_ASSIGNED")
        except Exception:
            pass

    return card


def block_card(card: Card) -> Card:
    with transaction.atomic():
        card = Card.objects.select_for_update().get(pk=card.pk)
        if card.status != Card.Status.ACTIVE:
            raise CardError(f"Cartao {card.card_number} nao pode ser bloqueado no estado {card.status}.")
        card.status = Card.Status.BLOCKED
        card.blocked_at = timezone.now()
        card.save(update_fields=["status", "blocked_at", "updated_at"])
    return card


def replace_card(old_card: Card, new_card: Card) -> Card:
    with transaction.atomic():
        # Sempre pela mesma ordem (o pk mais baixo primeiro): duas
        # substituicoes cruzadas a bloquear os mesmos dois cartoes por ordens
        # opostas dao um impasse entre si.
        primeiro, segundo = sorted([old_card.pk, new_card.pk])
        travados = {
            c.pk: c for c in Card.objects.select_for_update().filter(
                pk__in=[primeiro, segundo]).order_by("pk")
        }
        old_card = travados[old_card.pk]
        new_card = travados[new_card.pk]

        if old_card.status not in (Card.Status.ACTIVE, Card.Status.BLOCKED, Card.Status.LOST):
            raise CardError(f"Cartao {old_card.card_number} nao pode ser substituido no estado {old_card.status}.")
        if new_card.status != Card.Status.INACTIVE:
            raise CardError(f"Cartao substituto {new_card.card_number} deve estar inactivo.")

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
    with transaction.atomic():
        card = Card.objects.select_for_update().get(pk=card.pk)
        if card.status != Card.Status.ACTIVE:
            raise CardError(f"Cartao {card.card_number} deve estar activo para vincular.")
        wallet = getattr(passenger, "wallet", None)
        if not wallet:
            wallet = Wallet.objects.create(passenger_account=passenger)

        card.passenger_account = passenger
        card.wallet = wallet
        card.save(update_fields=["passenger_account", "wallet", "updated_at"])

    return card
