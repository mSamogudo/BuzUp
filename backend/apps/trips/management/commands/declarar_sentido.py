"""Declara o sentido de partidas ja criadas, pela hora a que saem.

O campo `Trip.direction` nasceu vazio em tudo o que ja existia — de proposito.
Nao ha na base de dados nada que diga para onde ia uma partida criada antes do
campo existir, e inventar-lhe um sentido punha passageiros no autocarro errado.
Enquanto fica vazio, a partida aparece nas pesquisas dos dois lados, que e
exactamente o comportamento que havia antes.

Quem sabe e o operador: numa carreira TPM-TUR, a saida das 03:00 e a das 13:30
tem cada uma o seu lado, e isso esta no horario da empresa, nao nos dados.
Este comando pega nessa informacao e escreve-a.

    manage.py declarar_sentido RT-MAPUTO-X-NELSPRUIT --ida 03:00 --volta 13:30

Por omissao so mostra o que faria. Escrever exige `--aplicar`.
"""

from __future__ import annotations

from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.routes.models import Route
from apps.trips.models import Trip


def _horas(valores: list[str] | None) -> list:
    saida = []
    for v in valores or []:
        try:
            saida.append(datetime.strptime(v.strip(), "%H:%M").time())
        except ValueError as e:
            raise CommandError(f"Hora invalida: {v!r}. Use HH:MM (ex.: 03:00).") from e
    return saida


class Command(BaseCommand):
    help = "Declara o sentido (ida/volta) das partidas de uma rota, pela hora de saida."

    def add_arguments(self, parser):
        parser.add_argument("rota", help="Codigo da rota (ex.: RT-MAPUTO-X-NELSPRUIT).")
        parser.add_argument("--ida", nargs="*", default=[], metavar="HH:MM",
                            help="Horas de partida que sao IDA.")
        parser.add_argument("--volta", nargs="*", default=[], metavar="HH:MM",
                            help="Horas de partida que sao VOLTA.")
        parser.add_argument("--incluir-passadas", action="store_true",
                            help="Tambem as partidas que ja sairam (por omissao so as futuras).")
        parser.add_argument("--aplicar", action="store_true",
                            help="Escrever. Sem isto so mostra o que faria.")

    def handle(self, *args, **opts):
        rota = Route.objects.filter(code=opts["rota"]).first()
        if not rota:
            raise CommandError(f"Rota {opts['rota']!r} nao encontrada.")

        ida = _horas(opts["ida"])
        volta = _horas(opts["volta"])
        if not ida and not volta:
            raise CommandError("Indique pelo menos --ida ou --volta.")
        repetidas = set(ida) & set(volta)
        if repetidas:
            # A mesma hora nos dois lados nao e uma escolha: e um engano de
            # digitacao que deixaria metade das partidas com o sentido errado.
            horas = ", ".join(h.strftime("%H:%M") for h in sorted(repetidas))
            raise CommandError(f"A(s) hora(s) {horas} estao em --ida e em --volta ao mesmo tempo.")

        qs = Trip.objects.filter(route=rota, direction="")
        if not opts["incluir_passadas"]:
            qs = qs.filter(planned_departure_at__gte=timezone.now())

        tz = timezone.get_current_timezone()
        planeado: dict[int, str] = {}
        sem_regra = []
        for t in qs.order_by("planned_departure_at"):
            if not t.planned_departure_at:
                continue
            hora = t.planned_departure_at.astimezone(tz).time().replace(second=0, microsecond=0)
            if hora in ida:
                planeado[t.id] = Trip.Direction.OUTBOUND
            elif hora in volta:
                planeado[t.id] = Trip.Direction.INBOUND
            else:
                sem_regra.append((t, hora))

        contagem = {"outbound": 0, "inbound": 0}
        for sentido in planeado.values():
            contagem[sentido] += 1
        self.stdout.write(f"Rota {rota.code} — {rota.name}")
        self.stdout.write(f"  ida:   {contagem['outbound']} partida(s)")
        self.stdout.write(f"  volta: {contagem['inbound']} partida(s)")
        if sem_regra:
            # Ficam vazias, e continuam a aparecer nos dois lados. Dize-lo em
            # voz alta: um silencio aqui parecia "esta tudo tratado".
            horas = sorted({h.strftime("%H:%M") for _t, h in sem_regra})
            self.stdout.write(self.style.WARNING(
                f"  SEM REGRA: {len(sem_regra)} partida(s) as {', '.join(horas)} — "
                f"ficam sem sentido declarado e continuam a aparecer nos dois lados."
            ))

        if not planeado:
            self.stdout.write("Nada a fazer.")
            return
        if not opts["aplicar"]:
            self.stdout.write(self.style.WARNING("Simulacao. Repita com --aplicar para escrever."))
            return

        with transaction.atomic():
            for sentido in (Trip.Direction.OUTBOUND, Trip.Direction.INBOUND):
                ids = [i for i, s in planeado.items() if s == sentido]
                if ids:
                    Trip.objects.filter(id__in=ids).update(direction=sentido)
        self.stdout.write(self.style.SUCCESS(f"Escrito: {len(planeado)} partida(s)."))
