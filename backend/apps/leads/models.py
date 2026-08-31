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

    class OperationType(models.TextChoices):
        """Que transporte a operacao faz — a pergunta "Tipo de operacao" do site.

        Nao se confunde com `interest`, que diz QUEM contacta (operador,
        empresa, escola). Sao dois eixos: uma escola e sempre `school`, e o
        transporte dela pode ser urbano ou interurbano.
        """

        URBAN = "urban", "Urbano"
        INTERCITY = "intercity", "Interurbano"
        INTERNATIONAL = "international", "Internacional"
        INSTITUTIONAL = "institutional", "Empresa ou escola"

    #: Areas do produto que o interessado pediu para ver, no formulario do site.
    #:
    #: Lista, e nao escolha unica: quem procura bilhetica quer quase sempre ver
    #: mais do que uma coisa, e obrigar a escolher uma so perdia a informacao
    #: que diz ao comercial o que preparar para a reuniao.
    TOPICS = [
        ("online_sales", "Venda online"),
        ("onboard_validation", "Validacao a bordo"),
        ("nfc_cards", "Cartoes NFC"),
        ("reports", "Relatorios"),
        ("packages", "Pacotes e subsidios"),
    ]

    class Status(models.TextChoices):
        NEW = "new", "Novo"
        CONTACTED = "contacted", "Contactado"
        QUALIFIED = "qualified", "Qualificado"
        CLOSED = "closed", "Fechado"

    name = models.CharField(max_length=160)
    # O site ja pedia o cargo e a resposta era deitada fora: nao havia coluna
    # nem campo no serializer. Quem recebe o pedido nao sabia se falava com o
    # dono da frota ou com quem faz as escalas.
    role = models.CharField(max_length=120, blank=True)
    organization = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=32)
    email = models.EmailField(blank=True)
    interest = models.CharField(max_length=16, choices=Interest.choices, default=Interest.OPERATOR)
    fleet_size = models.CharField(max_length=32, blank=True)
    operation_type = models.CharField(
        max_length=16, choices=OperationType.choices, blank=True, default="",
    )
    topics = models.JSONField(default=list, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    source = models.CharField(max_length=64, default="landing")

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"{self.name} ({self.organization or self.phone}) [{self.status}]"
