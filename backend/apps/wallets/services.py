from __future__ import annotations

import logging
from decimal import Decimal
from uuid import uuid4

from django.db import transaction

from apps.wallets.models import Wallet, WalletTransaction

logger = logging.getLogger(__name__)


class InsufficientBalanceError(Exception):
    pass


class WalletBlockedError(Exception):
    pass


def _ensure_wallet_active(wallet: Wallet):
    if wallet.status != Wallet.Status.ACTIVE:
        raise WalletBlockedError(f"Wallet {wallet.uuid} is {wallet.status}.")


def _notify_transaction(wallet: Wallet, tx: WalletTransaction):
    try:
        phone = ""
        if wallet.passenger_account:
            phone = wallet.passenger_account.phone_number
        if not phone:
            return

        from apps.sms.services.sender import send_sms

        if tx.direction == WalletTransaction.Direction.CREDIT:
            msg = f"BuzUp: Recarga de {tx.amount:,.2f} MZN confirmada. Novo saldo: {tx.balance_after:,.2f} MZN. Ref: {tx.reference}"
        else:
            msg = f"BuzUp: Debito de {tx.amount:,.2f} MZN. Novo saldo: {tx.balance_after:,.2f} MZN. Ref: {tx.reference}"

        send_sms(phone, msg, purpose="TRANSACTION_NOTIFICATION")
    except Exception:
        logger.exception("Failed to send transaction SMS")


def credit_wallet(
    wallet: Wallet,
    amount: Decimal,
    tx_type: str,
    source: str = "",
    reference: str | None = None,
    metadata: dict | None = None,
    notify: bool = True,
) -> WalletTransaction:
    _ensure_wallet_active(wallet)
    ref = reference or f"TXN-{uuid4().hex[:16].upper()}"

    with transaction.atomic():
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        balance_before = wallet.balance_cached
        balance_after = balance_before + amount

        tx = WalletTransaction.objects.create(
            wallet=wallet,
            type=tx_type,
            direction=WalletTransaction.Direction.CREDIT,
            amount=amount,
            signed_amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference=ref,
            source=source,
            status=WalletTransaction.Status.CONFIRMED,
            metadata=metadata or {},
        )

        wallet.balance_cached = balance_after
        wallet.save(update_fields=["balance_cached", "updated_at"])

    if notify:
        _notify_transaction(wallet, tx)

    return tx


def debit_wallet(
    wallet: Wallet,
    amount: Decimal,
    tx_type: str,
    source: str = "",
    reference: str | None = None,
    metadata: dict | None = None,
    notify: bool = True,
) -> WalletTransaction:
    _ensure_wallet_active(wallet)
    ref = reference or f"TXN-{uuid4().hex[:16].upper()}"

    with transaction.atomic():
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        balance_before = wallet.balance_cached

        if balance_before < amount:
            raise InsufficientBalanceError(
                f"Balance {balance_before} insufficient for debit of {amount}."
            )

        balance_after = balance_before - amount

        tx = WalletTransaction.objects.create(
            wallet=wallet,
            type=tx_type,
            direction=WalletTransaction.Direction.DEBIT,
            amount=amount,
            signed_amount=-amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference=ref,
            source=source,
            status=WalletTransaction.Status.CONFIRMED,
            metadata=metadata or {},
        )

        wallet.balance_cached = balance_after
        wallet.save(update_fields=["balance_cached", "updated_at"])

    if notify:
        _notify_transaction(wallet, tx)

    return tx
