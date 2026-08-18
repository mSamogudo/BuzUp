"""Avisar por SMS quem vai a bordo.

O caso real: o autocarro avaria na estrada, a fronteira esta fechada, a partida
atrasa duas horas. E preciso avisar QUEM VAI NAQUELE AUTOCARRO — e so essas
pessoas.

Quem conta:
  - bilhete `activo`: comprou e ainda nao embarcou. Vai apanhar aquela partida.
  - bilhete `usado`: ja validou, esta a bordo. E precisamente quem mais precisa
    de saber que o autocarro parou.

Quem nao conta:
  - bilhetes cancelados, reembolsados ou expirados — nao viajam;
  - partidas ja concluidas ou canceladas. Um bilhete usado numa viagem que
    chegou ontem pertence a alguem que ja esta em casa; mandar-lhe um aviso de
    atraso e mandar spam a quem pagou.

Sem esta ultima regra, "avisar a rota" acabava por escrever a todos os
passageiros da historia daquela carreira.
"""

from __future__ import annotations

from apps.guest_checkouts.models import DigitalTravelPass
from apps.trips.models import Trip

#: Partidas cujos passageiros ainda estao em viagem (ou por embarcar).
VIAGENS_A_DECORRER = (
    Trip.Status.SCHEDULED,
    Trip.Status.BOARDING,
    Trip.Status.DEPARTED,
    Trip.Status.PAUSED,
)

#: Bilhetes de quem vai viajar ou esta a viajar.
BILHETES_A_BORDO = (
    DigitalTravelPass.Status.ACTIVE,
    DigitalTravelPass.Status.USED,
)


def bilhetes_a_bordo(*, trip=None, route=None):
    """Bilhetes de quem esta a viajar (ou prestes a) na partida ou na rota."""
    qs = (DigitalTravelPass.objects
          .select_related("trip", "guest_checkout")
          .filter(status__in=BILHETES_A_BORDO))

    if trip is not None:
        return qs.filter(trip=trip, trip__status__in=VIAGENS_A_DECORRER)
    if route is not None:
        return qs.filter(trip__route=route, trip__status__in=VIAGENS_A_DECORRER)
    return qs.none()


def destinatarios(*, trip=None, route=None) -> list[dict]:
    """Um destinatario por numero, com o nome de quem viaja.

    Numa compra de familia os bilhetes partilham o telemovel de quem pagou:
    enviar um SMS por bilhete seria cobrar tres mensagens para tocar uma vez no
    mesmo bolso.
    """
    por_numero: dict[str, dict] = {}
    for bilhete in bilhetes_a_bordo(trip=trip, route=route):
        numero = (bilhete.payer_phone or "").strip()
        if not numero:
            continue
        entrada = por_numero.setdefault(numero, {
            "phone": numero, "names": [], "passes": 0, "trip_ids": set(),
        })
        entrada["passes"] += 1
        if bilhete.passenger_name and bilhete.passenger_name not in entrada["names"]:
            entrada["names"].append(bilhete.passenger_name)
        if bilhete.trip_id:
            entrada["trip_ids"].add(bilhete.trip_id)
    return sorted(por_numero.values(), key=lambda e: e["phone"])


def enviar(*, body: str, trip=None, route=None, actor=None):
    """Envia o aviso e devolve o registo do envio.

    Uma mensagem que falha nao trava as seguintes: o autocarro que avariou nao
    espera pelo provedor de SMS.
    """
    from apps.sms.models import SmsBroadcast
    from apps.sms.services.sender import send_sms

    lista = destinatarios(trip=trip, route=route)
    registo = SmsBroadcast.objects.create(
        scope=SmsBroadcast.Scope.TRIP if trip is not None else SmsBroadcast.Scope.ROUTE,
        trip=trip, route=route, body=body,
        recipients=len(lista), sent_by=actor,
    )

    enviadas = falhadas = 0
    for destinatario in lista:
        try:
            sms = send_sms(
                destinatario["phone"], body, purpose="TRIP_BROADCAST",
                metadata={
                    "broadcast_id": registo.id,
                    "trip_id": trip.id if trip else None,
                    "route_id": route.id if route else None,
                },
            )
            from apps.sms.models import SmsMessage
            if sms.status == SmsMessage.Status.FAILED:
                falhadas += 1
            else:
                enviadas += 1
        except Exception:
            falhadas += 1

    registo.sent = enviadas
    registo.failed = falhadas
    registo.save(update_fields=["sent", "failed"])
    return registo
