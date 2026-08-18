"""Aviso por SMS a quem vai a bordo.

Dois passos de proposito. Um envio destes custa dinheiro, chega a telemoveis de
pessoas reais e nao se desfaz — quem envia tem de ver quantas pessoas vai tocar
ANTES de tocar nelas.
"""

from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import audit
from apps.core.permissions import HasCapabilities
from apps.routes.models import Route
from apps.sms import broadcast
from apps.trips.models import Trip

#: Duas mensagens (2 x 160). Chega para "o autocarro avariou, seguimos as 14h";
#: acima disto o custo multiplica-se por cada passageiro sem ninguem reparar.
LIMITE_CARACTERES = 320


class BroadcastSerializer(serializers.Serializer):
    trip_id = serializers.IntegerField(required=False, allow_null=True)
    route_id = serializers.IntegerField(required=False, allow_null=True)
    body = serializers.CharField(max_length=LIMITE_CARACTERES, allow_blank=True, required=False)
    preview = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if not attrs.get("trip_id") and not attrs.get("route_id"):
            raise serializers.ValidationError("Indique a partida ou a rota a avisar.")
        if attrs.get("trip_id") and attrs.get("route_id"):
            raise serializers.ValidationError(
                "Indique a partida OU a rota — avisar as duas mandaria a mesma "
                "mensagem duas vezes a quem esta na partida."
            )
        if not attrs.get("preview") and not (attrs.get("body") or "").strip():
            raise serializers.ValidationError({"body": "Escreva a mensagem a enviar."})
        return attrs


class TripBroadcastView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("broadcasts.send",)

    def post(self, request):
        serializer = BroadcastSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        trip = rota = None
        if data.get("trip_id"):
            trip = Trip.objects.select_related("route").filter(pk=data["trip_id"]).first()
            if not trip:
                return Response({"detail": "Partida nao encontrada."}, status=status.HTTP_404_NOT_FOUND)
        else:
            rota = Route.objects.filter(pk=data["route_id"]).first()
            if not rota:
                return Response({"detail": "Rota nao encontrada."}, status=status.HTTP_404_NOT_FOUND)

        lista = broadcast.destinatarios(trip=trip, route=rota)
        corpo = (data.get("body") or "").strip()
        # Segmentos de SMS: o operador tem de saber que uma mensagem de 200
        # caracteres custa o dobro de uma de 150, vezes o numero de passageiros.
        segmentos = max(1, -(-len(corpo) // 160)) if corpo else 0

        if data["preview"]:
            return Response({
                "preview": True,
                "recipients": len(lista),
                "segments": segmentos,
                "messages": len(lista) * segmentos,
                # Numeros mascarados: pre-visualizar quem vai receber nao e
                # razao para despejar a lista telefonica dos passageiros.
                "sample": [
                    {"phone": _mascarar(d["phone"]),
                     "passengers": d["names"][:3], "passes": d["passes"]}
                    for d in lista[:8]
                ],
                "scope": "trip" if trip else "route",
                "target": (f"{trip.route.code} · {trip.planned_departure_at:%d/%m %H:%M}"
                           if trip and trip.planned_departure_at
                           else (trip.route.code if trip else f"{rota.code} — {rota.name}")),
            })

        if not lista:
            return Response(
                {"detail": "Nao ha ninguem a bordo para avisar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        registo = broadcast.enviar(body=corpo, trip=trip, route=rota, actor=request.user)
        audit(
            "SMS_BROADCAST_SENT", actor=request.user,
            entity_type="sms_broadcast", entity_id=str(registo.id),
            after={
                "scope": registo.scope,
                "trip_id": trip.id if trip else None,
                "route_id": rota.id if rota else None,
                "recipients": registo.recipients,
                "sent": registo.sent,
                "failed": registo.failed,
                "body": corpo[:200],
            },
        )
        return Response({
            "broadcast_id": registo.id,
            "recipients": registo.recipients,
            "sent": registo.sent,
            "failed": registo.failed,
        }, status=status.HTTP_201_CREATED)


def _mascarar(numero: str) -> str:
    digitos = "".join(c for c in (numero or "") if c.isdigit())
    return f"***{digitos[-4:]}" if len(digitos) >= 4 else digitos
