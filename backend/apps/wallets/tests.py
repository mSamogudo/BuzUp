"""Testes do nucleo financeiro da carteira (credito/debito/atomicidade)."""
from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.passengers.models import PassengerAccount
from apps.wallets.models import Wallet, WalletTransaction
from apps.wallets.services import (
    InsufficientBalanceError,
    WalletBlockedError,
    credit_wallet,
    debit_wallet,
)


class WalletServiceTests(TestCase):
    def setUp(self):
        self.pa = PassengerAccount.objects.create(
            full_name="Teste", phone_number="258840000001",
        )
        self.wallet = Wallet.objects.create(
            passenger_account=self.pa, balance_cached=Decimal("100.00"),
        )

    def _credit(self, amount, ref):
        return credit_wallet(
            wallet=self.wallet, amount=Decimal(amount),
            tx_type=WalletTransaction.Type.TOPUP, reference=ref, notify=False,
        )

    def _debit(self, amount, ref):
        return debit_wallet(
            wallet=self.wallet, amount=Decimal(amount),
            tx_type=WalletTransaction.Type.FARE_DEBIT, reference=ref, notify=False,
        )

    def test_credit_increases_balance(self):
        tx = self._credit("50.00", "TOP-credit-1")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance_cached, Decimal("150.00"))
        self.assertEqual(tx.balance_after, Decimal("150.00"))
        self.assertEqual(tx.direction, WalletTransaction.Direction.CREDIT)

    def test_debit_decreases_balance(self):
        tx = self._debit("30.00", "VAL-debit-1")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance_cached, Decimal("70.00"))
        self.assertEqual(tx.signed_amount, Decimal("-30.00"))

    def test_debit_insufficient_raises_and_keeps_balance(self):
        with self.assertRaises(InsufficientBalanceError):
            self._debit("150.00", "VAL-over-1")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance_cached, Decimal("100.00"))
        self.assertFalse(
            WalletTransaction.objects.filter(reference="VAL-over-1").exists()
        )

    def test_debit_blocked_wallet_raises(self):
        self.wallet.status = Wallet.Status.BLOCKED if hasattr(Wallet.Status, "BLOCKED") else self.wallet.status
        self.wallet.save(update_fields=["status"])
        if self.wallet.status == Wallet.Status.ACTIVE:
            self.skipTest("Wallet sem estado BLOCKED")
        with self.assertRaises(WalletBlockedError):
            self._debit("10.00", "VAL-blocked-1")

    def test_unique_reference_prevents_double_spend(self):
        self._debit("10.00", "VAL-dup-1")
        # Uma segunda transacao com a MESMA reference rebenta com IntegrityError
        # (a guarda real contra duplo-debito de validacoes idempotentes).
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._debit("10.00", "VAL-dup-1")
        self.wallet.refresh_from_db()
        # So o primeiro debito persistiu.
        self.assertEqual(self.wallet.balance_cached, Decimal("90.00"))

    def test_credit_then_debit_sequence(self):
        self._credit("200.00", "TOP-seq-1")
        self._debit("250.00", "VAL-seq-1")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance_cached, Decimal("50.00"))
