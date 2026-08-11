"""Preparacao dos dados para a demonstracao a TPM-TUR.

Faz tres coisas:

1. Fecha as viagens de teste que ficaram presas em "embarque"/"partiu" com
   datas de Julho. Enquanto uma viagem esta nesses estados nao ha limite de
   tempo para a venda — so a "programada" e que fecha 15 minutos antes da
   partida — por isso apareciam a venda no site com o botao activo.

2. Cria uma rota INTERPROVINCIAL e uma INTERURBANA. So existiam carreiras
   urbanas e a internacional; sem elas nao se mostra o manifesto, a escolha
   de lugar nem a exigencia de documento.

3. Agenda partidas para 14 dias nas tres rotas de longo curso.

Correr com: docker exec -i buzup_backend_staging python manage.py shell < demo_tpm.py
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.utils import timezone

from apps.fares import matrix as tabela
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Driver, Trip, Vehicle

agora = timezone.localtime()
hoje = agora.date()
DIAS = 14

print("=" * 64)
print("1) FECHAR VIAGENS VELHAS")
print("=" * 64)

limite = agora - timedelta(hours=24)
velhas = Trip.objects.filter(
    status__in=[Trip.Status.BOARDING, Trip.Status.DEPARTED],
    planned_departure_at__lt=limite,
)
for t in velhas:
    print(f"  fecha viagem {t.id:4} {t.route.code:22} {timezone.localtime(t.planned_departure_at):%d/%m %H:%M}  ({t.status})")
n = velhas.update(status=Trip.Status.COMPLETED, activity_closed_at=agora, updated_at=agora)
print(f"  -> {n} viagens fechadas")


def paragem(codigo, nome):
    s = Stop.objects.filter(code=codigo).first()
    if s:
        return s
    return Stop.objects.create(code=codigo, name=nome, status="active")


def montar_rota(codigo, nome, tipo, paragens_km, base, por_paragem):
    """Cria (ou completa) a rota, as paragens nos dois sentidos e a tabela."""
    rota = Route.objects.filter(code=codigo).first()
    if not rota:
        rota = Route.objects.create(code=codigo, name=nome, service_type=tipo,
                                    status=Route.Status.ACTIVE)
        print(f"  rota criada: {codigo} ({tipo})")
    else:
        print(f"  rota ja existia: {codigo}")

    for i, (cod, nm, km) in enumerate(paragens_km, start=1):
        s = paragem(cod, nm)
        RouteStop.objects.get_or_create(
            route=rota, stop=s, direction=RouteStop.Direction.OUTBOUND,
            defaults={"sequence": i, "distance_from_start_km": Decimal(str(km))},
        )
    # Sem sentido de volta o regresso nem e um trajecto valido.
    r = tabela.ensure_return_direction(rota)
    print(f"    volta: {r}")

    precos = tabela.fill_by_distance(rota, base=base, per_stop=por_paragem)
    res = tabela.write_matrix(rota, precos)
    m = tabela.read_matrix(rota)
    print(f"    tabela: {res} -> {m['pairs_priced']}/{m['pairs_total']} trajectos com preco")
    return rota


print()
print("=" * 64)
print("2) ROTAS DE LONGO CURSO")
print("=" * 64)

print(" INTERPROVINCIAL — Maputo - Xai-Xai")
xai = montar_rota(
    "MPT-XAI", "Maputo - Xai-Xai", Route.ServiceType.INTERPROVINCIAL,
    [
        ("ST-MAPUTO-JUNTA", "Maputo (Junta)", 0),
        ("ST-MARRACUENE", "Marracuene", 30),
        ("ST-MANHICA", "Manhiça", 80),
        ("ST-MACIA", "Macia", 130),
        ("ST-XAI-XAI", "Xai-Xai", 200),
    ],
    base="250", por_paragem="200",
)

print()
print(" INTERURBANA — Maputo - Manhiça")
man = montar_rota(
    "MPT-MAN", "Maputo - Manhiça", Route.ServiceType.URBAN,
    [
        ("ST-MAPUTO-JUNTA", "Maputo (Junta)", 0),
        ("ST-MARRACUENE", "Marracuene", 30),
        ("ST-BOBOLE", "Bobole", 45),
        ("ST-MANHICA", "Manhiça", 80),
    ],
    base="50", por_paragem="40",
)

nel = Route.objects.get(code="MZ-NEL")
print()
print(" INTERNACIONAL — MZ-NEL (ja existia, so agendar)")


print()
print("=" * 64)
print("3) AGENDAR PARTIDAS (%d dias)" % DIAS)
print("=" * 64)

motoristas = list(Driver.objects.all().order_by("id"))


def viatura(reg):
    return Vehicle.objects.get(registration=reg)


PLANO = [
    # rota, viatura, horas de partida, horas de viagem
    (nel, viatura("AAB-14-MP"), [time(5, 0), time(12, 0)], 7),
    (xai, viatura("AEE-12-MP"), [time(6, 0), time(13, 30)], 4),
    (man, viatura("ANU-88-MC"), [time(7, 0), time(11, 0), time(15, 0)], 2),
]

criadas = saltadas = 0
for idx, (rota, v, horas, duracao) in enumerate(PLANO):
    condutor = motoristas[idx % len(motoristas)] if motoristas else None
    n_rota = 0
    for d in range(DIAS):
        dia = hoje + timedelta(days=d)
        for h in horas:
            quando = timezone.make_aware(datetime.combine(dia, h))
            # Nada de agendar partidas para tras: no primeiro dia so entram as
            # que ainda faltam, com uma hora de folga para dar tempo a compra.
            if quando <= agora + timedelta(hours=1):
                continue
            if Trip.objects.filter(route=rota, planned_departure_at=quando).exists():
                saltadas += 1
                continue
            Trip.objects.create(
                route=rota, vehicle=v, driver=condutor,
                status=Trip.Status.SCHEDULED,
                planned_departure_at=quando,
                planned_arrival_at=quando + timedelta(hours=duracao),
            )
            criadas += 1
            n_rota += 1
    print(f"  {rota.code:10} {v.registration:12} {v.seated_capacity:2} lugares  "
          f"{condutor.full_name if condutor else '-':22} +{n_rota} partidas")

print(f"  -> {criadas} criadas, {saltadas} ja existiam")
