from django.db import models

from apps.core.models import BaseModel, active_unique_constraint


class PassengerAccount(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        BLOCKED = "blocked", "Bloqueado"
        SUSPENDED = "suspended", "Suspenso"
        CLOSED = "closed", "Encerrado"

    class DocumentType(models.TextChoices):
        BI = "bi", "B.I."
        PASSPORT = "passport", "Passaporte"
        DRIVING_LICENSE = "driving_license", "Carta de Conducao"

    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, db_index=True)
    email = models.EmailField(blank=True)
    document_type = models.CharField(max_length=20, choices=DocumentType.choices, blank=True, default="")
    document_number = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            active_unique_constraint("phone_number", name="uq_passenger_phone_active"),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"
