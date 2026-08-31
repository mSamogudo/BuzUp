"""`/api/shifts/` — listar, abrir, fechar, conferir e reabrir turnos.

As capacidades reaproveitam as que ja existem, e nao ha nenhuma nova:

- **ler** pede `agents.read` — quem ve os agentes ve os turnos deles;
- **abrir e fechar** pedem `agents.manage`, que e quem monta a operacao;
- **conferir e reabrir** pedem `payments.manage`. Conferir e um acto da
  tesouraria: quem faz a caixa nao pode ser quem a da por boa, senao a
  conferencia nao confere nada. Reabrir anda com ela porque desfaz o mesmo acto.
"""

from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.core.viewsets import BaseModelViewSet
from apps.shifts.api.serializers import (
    ShiftCloseSerializer,
    ShiftOpenSerializer,
    ShiftReopenSerializer,
    ShiftSerializer,
    ShiftVerifySerializer,
)
from apps.shifts.models import Shift
from apps.shifts.services import (
    ShiftError,
    abrir_turno,
    apurado_esperado,
    conferir_turno,
    fechar_turno,
    reabrir_turno,
)


class ShiftViewSet(BaseModelViewSet):
    queryset = (
        Shift.objects
        .select_related("agent_user", "agent_profile", "vehicle", "device", "verified_by")
        .all()
    )
    serializer_class = ShiftSerializer
    # Os turnos nao se criam nem se apagam por REST: abrem-se e fecham-se, que
    # sao actos com regras. Deixar o POST generico aberto permitia criar um
    # turno ja fechado, com o apurado que se quisesse.
    http_method_names = ["get", "post", "head", "options"]
    required_capabilities_by_action = {
        "list": ("agents.read",),
        "retrieve": ("agents.read",),
        "mine": ("pos.operate",),
        "open": ("agents.manage",),
        "close": ("agents.manage",),
        "verify": ("payments.manage",),
        "reopen": ("payments.manage",),
    }

    def create(self, request, *args, **kwargs):
        """POST /api/shifts/ nao cria nada.

        `post` tem de estar em `http_method_names` para as accoes (abrir,
        fechar, conferir, reabrir) funcionarem, e isso deixava a criacao
        generica do router alcancavel — para um superuser, que salta as
        capacidades, dava para criar um turno ja fechado com o apurado que se
        quisesse. Abrir um turno e um acto com regras, e passa por `open`.
        """
        return Response(
            {"detail": "Use POST /api/shifts/open/ para abrir um turno."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def get_queryset(self):
        qs = super().get_queryset()
        estado = (self.request.query_params.get("status") or "").strip()
        if estado:
            qs = qs.filter(status__in=[e.strip() for e in estado.split(",") if e.strip()])
        agente = (self.request.query_params.get("agent") or "").strip()
        if agente.isdigit():
            qs = qs.filter(agent_user_id=int(agente))
        viatura = (self.request.query_params.get("vehicle") or "").strip()
        if viatura.isdigit():
            qs = qs.filter(vehicle_id=int(viatura))
        desde = (self.request.query_params.get("date_from") or "").strip()
        if desde:
            qs = qs.filter(opened_at__date__gte=desde)
        ate = (self.request.query_params.get("date_to") or "").strip()
        if ate:
            qs = qs.filter(opened_at__date__lte=ate)
        # `?divergent=true` — so os que nao bateram certo. E por onde a
        # tesouraria comeca o dia.
        if (self.request.query_params.get("divergent") or "").lower() == "true":
            qs = qs.filter(~Q(difference=0), status__in=[Shift.Status.CLOSED, Shift.Status.VERIFIED])
        return qs

    def _resposta(self, shift):
        return Response(ShiftSerializer(shift).data)

    @action(detail=False, methods=["get"])
    def mine(self, request):
        """O turno aberto de quem esta a pedir, com o apurado ate agora.

        E o que o POS mostra ao agente: quanto ja tem em caixa antes de fechar,
        para o fecho nao ser uma surpresa.
        """
        shift = Shift.objects.filter(
            agent_user=request.user, status=Shift.Status.OPEN).first()
        if not shift:
            return Response({"shift": None})
        contas = apurado_esperado(shift)
        return Response({
            "shift": ShiftSerializer(shift).data,
            "running_total": {
                "cash_sales": str(contas["cash_sales"]),
                "expected": str(contas["expected"]),
                "tickets_count": contas["tickets_count"],
                "validations_count": contas["validations_count"],
                "validations_amount": str(contas["validations_amount"]),
            },
        })

    @action(detail=False, methods=["post"])
    def open(self, request):
        serializer = ShiftOpenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        from apps.devices.models import Device
        from apps.trips.models import Agent, Vehicle

        alvo = request.user
        agent_id = dados.get("agent_user")
        if agent_id and agent_id != request.user.id:
            from django.contrib.auth import get_user_model

            alvo = get_user_model().objects.filter(pk=agent_id).first()
            if alvo is None:
                return Response({"agent_user": ["Agente desconhecido."]},
                                status=status.HTTP_400_BAD_REQUEST)

        try:
            shift = abrir_turno(
                agent_user=alvo,
                agent_profile=Agent.objects.filter(user=alvo).first(),
                vehicle=Vehicle.objects.filter(pk=dados.get("vehicle")).first(),
                device=Device.objects.filter(pk=dados.get("device")).first(),
                float_amount=dados.get("float_amount"),
                opened_by=request.user,
            )
        except ShiftError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ShiftSerializer(shift).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        serializer = ShiftCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            shift = fechar_turno(
                self.get_object(),
                counted_amount=serializer.validated_data["counted_amount"],
                notes=serializer.validated_data.get("notes", ""),
            )
        except ShiftError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._resposta(shift)

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        serializer = ShiftVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            shift = conferir_turno(
                self.get_object(),
                verified_by=request.user,
                notes=serializer.validated_data.get("notes", ""),
            )
        except ShiftError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._resposta(shift)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        serializer = ShiftReopenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            shift = reabrir_turno(
                self.get_object(),
                motivo=serializer.validated_data["reason"],
                reopened_by=request.user,
            )
        except ShiftError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._resposta(shift)
