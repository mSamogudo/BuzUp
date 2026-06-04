import hashlib
import secrets

from django.db import models

from apps.core.models import BaseModel, active_unique_constraint


class Card(BaseModel):
    class CardType(models.TextChoices):
        PHYSICAL = "physical", "Fisico"
        DIGITAL = "digital", "Digital"

    class Status(models.TextChoices):
        INACTIVE = "inactive", "Inactivo"
        ACTIVE = "active", "Activo"
        BLOCKED = "blocked", "Bloqueado"
        LOST = "lost", "Perdido"
        REPLACED = "replaced", "Substituido"
        RETIRED = "retired", "Retirado"

    class Technology(models.TextChoices):
        NFC_UID = "nfc_uid", "NFC UID"
        MIFARE_CLASSIC = "mifare_classic", "MIFARE Classic"
        MIFARE_DESFIRE = "mifare_desfire", "MIFARE DESFire"
        QR_CODE = "qr_code", "QR Code"
        OTHER = "other", "Outro"

    card_type = models.CharField(max_length=16, choices=CardType.choices, default=CardType.PHYSICAL)
    card_uid = models.CharField(max_length=64, db_index=True, blank=True)
    card_number = models.CharField(max_length=32, blank=True, db_index=True)
    card_technology = models.CharField(max_length=24, choices=Technology.choices, default=Technology.NFC_UID)
    qr_token = models.CharField(max_length=128, unique=True, blank=True, null=True)
    qr_token_hash = models.CharField(max_length=128, blank=True)
    wallet = models.ForeignKey(
        "wallets.Wallet", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="cards",
    )
    passenger_account = models.ForeignKey(
        "passengers.PassengerAccount", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="cards",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.INACTIVE)
    issued_batch = models.CharField(max_length=64, blank=True)
    batch_serial = models.CharField(max_length=32, blank=True)
    manufacturer = models.CharField(max_length=64, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    blocked_at = models.DateTimeField(null=True, blank=True)
    replaced_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="replaces",
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            active_unique_constraint("card_uid", name="uq_card_uid_active"),
        ]
        indexes = [
            models.Index(fields=["card_type", "status"]),
            models.Index(fields=["card_uid", "status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.card_number:
            from apps.core.utils import generate_sequential_code
            prefix = "DIG" if self.card_type == self.CardType.DIGITAL else "NFC"
            self.card_number = generate_sequential_code(prefix, Card, "card_number")
        if self.card_type == self.CardType.DIGITAL and not self.qr_token:
            raw = secrets.token_urlsafe(32)
            self.qr_token = raw
            self.qr_token_hash = hashlib.sha256(raw.encode()).hexdigest()
            self.card_technology = self.Technology.QR_CODE
            if not self.card_uid:
                self.card_uid = f"DIG-{self.qr_token_hash[:16].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.card_number} [{self.card_type}/{self.status}]"

    @property
    def is_physical(self):
        return self.card_type == self.CardType.PHYSICAL

    @property
    def is_digital(self):
        return self.card_type == self.CardType.DIGITAL
