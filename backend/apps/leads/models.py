from django.db import models


class ContactLead(models.Model):
    """A public inquiry from the marketing site (contact form or app waitlist)."""

    class Source(models.TextChoices):
        CONTACT = "contact", "Formulário de contacto"
        WAITLIST = "waitlist", "Lista de espera da app"

    class Profile(models.TextChoices):
        PASSENGER = "passageiro", "Passageiro"
        OPERATOR = "operador", "Operador de transporte"
        PUBLIC_ENTITY = "municipio", "Município / Entidade pública"
        PARTNER = "parceiro", "Parceiro / Ponto de recarga"
        PRESS = "imprensa", "Imprensa"
        OTHER = "outro", "Outro"

    source = models.CharField(max_length=16, choices=Source.choices, default=Source.CONTACT)
    profile = models.CharField(max_length=32, choices=Profile.choices, blank=True)

    name = models.CharField(max_length=120, blank=True)
    organization = models.CharField(max_length=160, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    message = models.TextField(blank=True)

    # Provenance / triage
    locale = models.CharField(max_length=8, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=400, blank=True)
    handled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contacto / Lead"
        verbose_name_plural = "Contactos / Leads"
        indexes = [
            models.Index(fields=["source", "handled"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self) -> str:
        who = self.name or self.email
        return f"[{self.get_source_display()}] {who}"
