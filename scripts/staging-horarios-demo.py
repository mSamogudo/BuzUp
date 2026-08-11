"""Horarios para todas as rotas + geracao de um mes de partidas.

Ate aqui so a L1 tinha horario; as restantes linhas urbanas nao tinham
partida nenhuma e as de longo curso tinham viagens soltas, criadas a mao.
Aqui da-se horario a todas e usa-se o gerador do proprio produto
(`generate_daily_trips`), para os dados de demonstracao nascerem pelo mesmo
caminho que a operacao real usa — e para o separador "Horarios" do portal
ter o que mostrar.

As viagens de longo curso ja criadas sao ligadas ao horario respectivo antes
de gerar. Sem isso o gerador nao as reconhecia (procura por horario, nao por
rota) e criava uma segunda partida a mesma hora.
"""

from datetime import time, timedelta

from django.utils import timezone

from apps.routes.models import Route
from apps.trips.models import Driver, RouteSchedule, Trip, Vehicle
from apps.trips.services import generate_daily_trips

DIAS = 30

# rota -> (inicio, fim, frequencia em minutos, viatura)
# Urbanas: de meia em meia hora das 06:00 as 20:00, como a L1 ja fazia.
# Longo curso: a frequencia recria exactamente as partidas do dia
#   MZ-NEL   05:00 + 420min = 12:00
#   MPT-XAI  06:00 + 450min = 13:30
#   MPT-MAN  07:00 + 240min = 11:00 e 15:00
PLANO = {
    "L2": (time(6, 0), time(20, 0), 30, "AAD-56-MP"),
    "L3": (time(6, 0), time(20, 0), 30, "ABC-27-MC"),
    "L4": (time(6, 0), time(20, 0), 30, "AGT-09-MC"),
    "L5": (time(6, 0), time(20, 0), 30, "AMR-31-MP"),
    "L6": (time(6, 0), time(20, 0), 30, "ADX-77-MC"),
    "L7": (time(6, 0), time(20, 0), 30, "AFT-44-MC"),
    "RT-BAIXA-ALBAZINE": (time(5, 30), time(20, 30), 30, "AKL-63-MP"),
    "MZ-NEL": (time(5, 0), time(12, 0), 420, "AAB-14-MP"),
    "MPT-XAI": (time(6, 0), time(13, 30), 450, "AEE-12-MP"),
    "MPT-MAN": (time(7, 0), time(15, 0), 240, "ANU-88-MC"),
}

motoristas = list(Driver.objects.all().order_by("id"))
agora = timezone.localtime()
hoje = agora.date()

print("=" * 70)
print("1) HORARIOS")
print("=" * 70)

horarios = list(RouteSchedule.objects.filter(status=RouteSchedule.Status.ACTIVE))
for i, (codigo, (inicio, fim, freq, matricula)) in enumerate(PLANO.items()):
    rota = Route.objects.filter(code=codigo, status=Route.Status.ACTIVE).first()
    if not rota:
        print(f"  {codigo}: rota nao encontrada, saltada")
        continue
    if RouteSchedule.objects.filter(route=rota, status=RouteSchedule.Status.ACTIVE).exists():
        print(f"  {codigo}: ja tinha horario")
        continue
    s = RouteSchedule.objects.create(
        route=rota,
        vehicle=Vehicle.objects.filter(registration=matricula).first(),
        driver=motoristas[(i + 1) % len(motoristas)] if motoristas else None,
        start_time=inicio, end_time=fim, frequency_minutes=freq,
        days_of_week=[], status=RouteSchedule.Status.ACTIVE,
    )
    horarios.append(s)
    print(f"  {codigo:20} {inicio}-{fim} de {freq} em {freq} min  {matricula}")

print()
print("=" * 70)
print("2) LIGAR AS VIAGENS SOLTAS AO HORARIO")
print("=" * 70)

for s in RouteSchedule.objects.filter(status=RouteSchedule.Status.ACTIVE).select_related("route"):
    soltas = Trip.objects.filter(route=s.route, schedule__isnull=True,
                                 planned_departure_at__gte=agora)
    n = 0
    for t in soltas:
        h = timezone.localtime(t.planned_departure_at).time()
        # So liga se a hora bate certo com o que o horario geraria.
        minutos = h.hour * 60 + h.minute
        inicio = s.start_time.hour * 60 + s.start_time.minute
        fim = s.end_time.hour * 60 + s.end_time.minute
        if inicio <= minutos <= fim and (minutos - inicio) % s.frequency_minutes == 0:
            t.schedule = s
            t.save(update_fields=["schedule", "updated_at"])
            n += 1
    if n:
        print(f"  {s.route.code:20} +{n} viagens ligadas")

print()
print("=" * 70)
print(f"3) GERAR {DIAS} DIAS")
print("=" * 70)

total = 0
por_rota = {}
for d in range(DIAS):
    dia = hoje + timedelta(days=d)
    for s in RouteSchedule.objects.filter(status=RouteSchedule.Status.ACTIVE).select_related("route"):
        novas = generate_daily_trips(s, dia)
        total += len(novas)
        por_rota[s.route.code] = por_rota.get(s.route.code, 0) + len(novas)

for codigo, n in sorted(por_rota.items()):
    print(f"  {codigo:20} +{n}")
print(f"  -> {total} viagens criadas")

# O gerador cria o dia INTEIRO, incluindo as horas de hoje que ja passaram.
# Uma partida passada nao se vende (fecha 15 min antes), mas fica a sujar a
# lista do portal. Removem-se so as de HOJE, e so as que ninguem usou —
# viagens de dias anteriores sao historico e nao se tocam.
from apps.guest_checkouts.models import GuestCheckout

candidatas = Trip.objects.filter(
    status=Trip.Status.SCHEDULED,
    planned_departure_at__lt=timezone.now(),
    planned_departure_at__date=hoje,
)
com_bilhete = set(
    GuestCheckout.objects.filter(trip__in=candidatas).values_list("trip_id", flat=True)
)
apagaveis = candidatas.exclude(id__in=com_bilhete)
n_apagadas = apagaveis.count()
apagaveis.delete()
print(f"  -> {n_apagadas} partidas de hoje ja passadas (e sem bilhetes) removidas")
if com_bilhete:
    print(f"  -> {len(com_bilhete)} mantidas por terem bilhetes associados")
