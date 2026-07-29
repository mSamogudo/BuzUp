from django.db import models

from apps.core.models import BaseModel


class ServiceRequest(BaseModel):
    """Pedido de contacto vindo do site publico (landing).

    Fica no sistema em vez de virar um email perdido: a equipa comercial
    trabalha a lista no portal e o estado acompanha o funil.
    """

    class Interest(models.TextChoices):
        OPERATOR = "operator", "Operador de transporte"
        COMPANY = "company", "Empresa"
        SCHOOL = "school", "Escola ou instituicao"
        OTHER = "other", "Outro"

    class Status(models.TextChoices):
        NEW = "new", "Novo"
        CONTACTED = "contacted", "Contactado"
        QUALIFIED = "qualified", "Qualificado"
        CLOSED = "closed", "Fechado"

    name = models.CharField(max_length=160)
    organization = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=32)
    email = models.EmailField(blank=True)
    interest = models.CharField(max_length=16, choices=Interest.choices, default=Interest.OPERATOR)
    fleet_size = models.CharField(max_length=32, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    source = models.CharField(max_length=64, default="landing")

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"{self.name} ({self.organization or self.phone}) [{self.status}]"
