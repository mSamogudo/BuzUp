from __future__ import annotations

from django.db import transaction

from apps.cards.models import Card
from apps.cards.services import create_digital_card
from apps.passengers.models import PassengerAccount
from apps.users.otp import normalize_otp_phone
from apps.wallets.models import Wallet


def ensure_passenger_access_account(passenger: PassengerAccount, notify_by_sms: bool = True):
    from apps.sms.services.sender import send_sms
    from apps.users.models import User

    phone = normalize_otp_phone(passenger.phone_number)
    if not phone:
        raise ValueError("Telefone obrigatorio para criar conta de passageiro.")

    with transaction.atomic():
        passenger = PassengerAccount.objects.select_for_update().get(pk=passenger.pk)
        if passenger.phone_number != phone:
            passenger.phone_number = phone
            passenger.save(update_fields=["phone_number", "updated_at"])

        wallet, _ = Wallet.objects.get_or_create(passenger_account=passenger)
        digital_card = passenger.cards.filter(card_type=Card.CardType.DIGITAL).first()
        if digital_card is None:
            digital_card = create_digital_card(passenger)

        user, created = User.objects.get_or_create(
            username=f"passenger_{phone}",
            defaults={
                "email": f"{phone}@passenger.buzup.co.mz",
                "phone": phone,
                "first_name": passenger.full_name,
                "is_active": True,
            },
        )
        user.phone = phone
        user.first_name = passenger.full_name
        user.is_active = True
        if created:
            user.set_unusable_password()
        user.save()

    if notify_by_sms:
        send_sms(
            phone,
            (
                "BusUp: A sua conta foi criada. Aceda ao portal, escolha Entrar como "
                f"Passageiro e use este telefone para receber o codigo OTP. Cartao digital {digital_card.card_number}."
            ),
            purpose="PASSENGER_ACCOUNT_CREATED",
        )

    return user, wallet, digital_card
