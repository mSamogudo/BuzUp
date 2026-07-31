"""Codigo curto do bilhete — o que o passageiro le quando o QR nao passa.

Eram 4 caracteres sobre um alfabeto hexadecimal (16^4 = 65 536). Num autocarro
com 60 bilhetes, dois partilharem o codigo tinha perto de 3% de hipoteses, e
quando isso acontece a validacao recusa os DOIS: um passageiro com bilhete
valido fica em terra. Estes testes fixam os 6 caracteres novos e garantem que
os bilhetes antigos, impressos com 4, continuam a validar.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.guest_checkouts.ticket_codes import (
    SHORT_CODE_LENGTH,
    ticket_reference,
    ticket_short_code,
)
from apps.validations.services import _resolve_digital_travel_pass


class ShortCodeLengthTests(TestCase):
    def test_new_codes_are_six_characters(self):
        self.assertEqual(SHORT_CODE_LENGTH, 6)
        self.assertEqual(ticket_short_code("GC-A1B2C3D4E5F60718"), "F60718")

    def test_length_can_be_asked_for_explicitly(self):
        """A validacao de um bilhete antigo precisa de recalcular com 4."""
        self.assertEqual(ticket_short_code("GC-A1B2C3D4E5F60718", 4), "0718")

    def test_symbols_and_dashes_do_not_count(self):
        self.assertEqual(ticket_short_code("GC-AB12-03"), "AB1203")

    def test_reference_shorter_than_the_code_is_not_padded(self):
        self.assertEqual(ticket_short_code("AB1"), "AB1")


class ShortCodeLookupTests(TestCase):
    """A procura tem de aceitar o que esta impresso, seja de 4 ou de 6."""

    def _pass(self, reference: str, *, legacy_length: int | None = None):
        gc = GuestCheckout.objects.create(
            reference=reference,
            payer_phone="841000000",
            origin_stop="A", destination_stop="B",
            quantity=1,
            unit_amount=Decimal("100.00"),
            total_amount=Decimal("100.00"),
            status=GuestCheckout.Status.ISSUED,
        )
        raw, token_hash = DigitalTravelPass.generate_token()
        tp = DigitalTravelPass.objects.create(
            guest_checkout=gc,
            payer_phone="841000000",
            origin_stop="A", destination_stop="B",
            fare_amount=Decimal("100.00"),
            token=raw, token_hash=token_hash,
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=1),
        )
        length = legacy_length or SHORT_CODE_LENGTH
        tp.short_code = ticket_short_code(ticket_reference(tp), length)
        tp.save(update_fields=["short_code", "updated_at"])
        return tp

    def test_current_ticket_is_found_by_its_six_character_code(self):
        tp = self._pass("GC-11112222333344445")
        self.assertEqual(len(tp.short_code), 6)
        self.assertEqual(_resolve_digital_travel_pass(tp.short_code).id, tp.id)

    def test_ticket_printed_before_the_change_still_validates(self):
        """Bilhetes de 4 caracteres continuam em circulacao — recusa-los seria
        deixar em terra passageiros que pagaram."""
        tp = self._pass("GC-99998888777766665", legacy_length=4)
        self.assertEqual(len(tp.short_code), 4)
        self.assertEqual(_resolve_digital_travel_pass(tp.short_code).id, tp.id)

    def test_lowercase_and_spaces_are_forgiven(self):
        tp = self._pass("GC-ABCDEF0123456789A")
        found = _resolve_digital_travel_pass(f" {tp.short_code.lower()} ")
        self.assertEqual(found.id, tp.id)

    def test_six_characters_separate_tickets_that_shared_the_old_four(self):
        """O caso que motivou a mudanca: duas referencias com o mesmo fim de 4.

        Com 4 caracteres os dois bilhetes eram indistinguiveis e a validacao
        recusava ambos. Com 6 cada um encontra o seu.
        """
        a = self._pass("GC-1111111111AA0718")
        b = self._pass("GC-2222222222BB0718")

        self.assertEqual(ticket_short_code(a.guest_checkout.reference, 4),
                         ticket_short_code(b.guest_checkout.reference, 4))
        self.assertNotEqual(a.short_code, b.short_code)
        self.assertEqual(_resolve_digital_travel_pass(a.short_code).id, a.id)
        self.assertEqual(_resolve_digital_travel_pass(b.short_code).id, b.id)

    def test_garbage_input_is_refused(self):
        self._pass("GC-33334444555566667")
        for bad in ["", "AB", "ABC", "A" * 9, "AB-CD/EF"]:
            with self.assertRaises(DigitalTravelPass.DoesNotExist, msg=f"aceitou {bad!r}"):
                _resolve_digital_travel_pass(bad)
