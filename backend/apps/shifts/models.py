"""Turnos de agente: quem esteve com que autocarro, e quanto dinheiro entregou.

Um turno prende um agente a uma viatura durante um periodo e fecha caixa. Ate
aqui o sistema sabia o que cada agente vendeu (`AgentDayClose`, por dia) e em
que terminal esteve (`PosSession`, por dispositivo), mas nao sabia responder a
pergunta que a tesouraria faz todos os dias: *este agente entregou o dinheiro
que devia?*

O turno e a unidade que responde. Fecha-se com quatro numeros:

- **fundo de maneio** — o troco com que o agente comecou, e que tem de devolver;
- **apurado esperado** — o que a caixa devia ter, calculado PELO SERVIDOR a
  partir das vendas ligadas ao turno;
- **contado** — o que o agente diz ter na mao;
- **diferenca** — contado menos esperado, que e o unico numero que interessa
  quando nao da zero.

O esperado nao vem do cliente de proposito. Se viesse, o agente declarava o que
lhe convinha e a diferenca dava sempre zero: a conferencia deixava de conferir
alguma coisa.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Shift(BaseModel):
    class Status(models.TextChoices):
        OPEN = "open", "Aberto"
        CLOSED = "closed", "Fechado"
        VERIFIED = "verified", "Conferido"

    agent_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="shifts",
    )
    #: Perfil de agente, quando existe. O utilizador e que manda — um agente
    #: pode ser desligado do perfil sem que o turno dele deixe de ter dono.
    agent_profile = models.ForeignKey(
        "trips.Agent",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="shifts",
    )
    #: A viatura que o agente acompanhou. Opcional: ha turnos de balcao, sem
    #: autocarro nenhum, e recusa-los obrigava a inventar uma viatura falsa.
    vehicle = models.ForeignKey(
        "trips.Vehicle",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="shifts",
    )
    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="shifts",
    )

    opened_at = models.DateTimeField(auto_now_add=True, db_index=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="shifts_opened",
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="shifts_verified",
    )

    #: Troco inicial. Sai da tesouraria e volta a ela no fim.
    float_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    #: O que a caixa devia ter. Calculado no fecho, nunca recebido do cliente.
    expected_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    #: O que o agente contou.
    counted_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    #: `counted - expected`. Guardado em vez de calculado a cada leitura para o
    #: relatorio poder ordenar e filtrar por diferenca sem varrer as vendas.
    difference = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    #: Contagens do momento do fecho, para o historico nao mudar quando as
    #: vendas forem reconciliadas mais tarde.
    tickets_count = models.PositiveIntegerField(default=0)
    validations_count = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True)
    #: Porque e que o turno foi reaberto. Reabrir sem dizer porque era apagar a
    #: unica pista de que a conta ja tinha sido dada por boa uma vez.
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-opened_at",)
        indexes = [
            models.Index(fields=["agent_user", "status"]),
            models.Index(fields=["status", "opened_at"]),
        ]

    def __str__(self):
        return f"Turno {self.pk} | {self.agent_user_id} | {self.status}"

    @property
    def is_open(self) -> bool:
        return self.status == self.Status.OPEN
