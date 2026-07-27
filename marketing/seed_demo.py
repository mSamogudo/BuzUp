# -*- coding: utf-8 -*-
"""Seed de DEMO para screenshots (staging). Idempotente-ish, aditivo.
Contexto: Maputo, Moçambique. Popula rotas, frota, motoristas, agentes,
passageiros+carteiras+cartões, tarifas, viagens, e — para o dashboard —
validações/recargas/pagamentos datados nos últimos 7 dias."""
import random
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

from apps.routes.models import Route, Stop, RouteStop
from apps.trips.models import Vehicle, Driver, Agent, Trip
from apps.fares.models import FareProduct, FareRule
from apps.passengers.models import PassengerAccount
from apps.wallets.models import Wallet, WalletTransaction
from apps.cards.models import Card
from apps.validations.models import ValidationEvent
from apps.payments.models import PaymentIntent
from apps.devices.models import Device
from apps.packages.models import Package
from apps.users.models import User, Role, UserRole

random.seed(7)
now = timezone.now()
lnow = timezone.localtime(now)

def backdate(qs_model, pk, **fields):
    qs_model.objects.filter(pk=pk).update(**fields)

# ---------------- STOPS ----------------
STOPS = ["Baixa","Praça 25 de Junho","Museu","Costa do Sol","Zimpeto","Estádio do Zimpeto",
 "Benfica","Matola Gare","Matola Rio","Xipamanine","Magoanine","Junta","Marracuene",
 "Aeroporto","Hospital Central","Universidade E. Mondlane","Maxaquene","Malhangalene",
 "Alto Maé","Polana","Sommerschield","Praça dos Combatentes","Fajardo","Laulane",
 "Jardim","Chamanculo","Mavalane","T3","Ferroviário","George Dimitrov"]
stopo = {}
for nm in STOPS:
    s, _ = Stop.objects.get_or_create(name=nm, defaults={"status": "active"})
    stopo[nm] = s

# ---------------- ROUTES + ROUTESTOPS ----------------
ROUTES = [
 ("L1","Baixa – Zimpeto",["Baixa","Museu","Maxaquene","Benfica","Zimpeto","Estádio do Zimpeto"]),
 ("L2","Museu – Costa do Sol",["Museu","Polana","Sommerschield","Costa do Sol"]),
 ("L3","Combatentes – Matola",["Praça dos Combatentes","Xipamanine","Fajardo","Matola Gare","Matola Rio"]),
 ("L4","Xipamanine – Magoanine",["Xipamanine","Chamanculo","Laulane","Magoanine"]),
 ("L5","Baixa – Aeroporto",["Baixa","Alto Maé","Malhangalene","Mavalane","Aeroporto"]),
 ("L6","Junta – Marracuene",["Junta","Ferroviário","T3","Marracuene"]),
 ("L7","Baixa – Hospital Central",["Baixa","Jardim","Hospital Central","Universidade E. Mondlane"]),
]
routeo = []
for code, name, stops in ROUTES:
    r, _ = Route.objects.get_or_create(code=code, defaults={"name": name, "status": "active"})
    routeo.append(r)
    for direction in ("outbound", "inbound"):
        seq = stops if direction == "outbound" else list(reversed(stops))
        for i, nm in enumerate(seq, 1):
            RouteStop.objects.get_or_create(
                route=r, direction=direction, sequence=i,
                defaults={"stop": stopo[nm], "distance_from_start_km": Decimal(str(round(i * 1.8, 2)))})

# ---------------- VEHICLES ----------------
MK = [("Yutong","ZK6120"),("Higer","KLQ6119"),("Zhongtong","LCK6127"),
      ("TATA","Starbus"),("Toyota","Coaster"),("Golden Dragon","XML6125")]
REGS = ["AAB-14-MP","ABC-27-MC","AAD-56-MP","AGT-09-MC","AMR-31-MP",
        "ADX-77-MC","AEE-12-MP","AFT-44-MC","AKL-63-MP","ANU-88-MC","APQ-21-MP","ARS-38-MC"]
veho = []
for i, reg in enumerate(REGS):
    mk, mdl = MK[i % len(MK)]
    v, _ = Vehicle.objects.get_or_create(registration=reg, defaults={
        "make": mk, "model_name": mdl,
        "seated_capacity": random.choice([28,32,45,50]),
        "standing_capacity": random.choice([10,15,20,25]),
        "status": random.choice(["active","active","active","active","maintenance"])})
    veho.append(v)

# ---------------- DRIVERS (+users p/ alguns) ----------------
DRIVERS = ["Fernando Chissano","Custódio Mabjaia","Alberto Nhaca","Dércio Muianga",
 "Rogério Sitoe","Belmiro Tembe","Jaime Macuácua","Nélson Cossa","Ivan Zandamela","Aníbal Langa"]
drole = Role.objects.filter(code="driver").first()
drvo = []
for nm in DRIVERS:
    d = Driver.objects.filter(full_name=nm).first()
    if not d:
        d = Driver.objects.create(full_name=nm,
            phone="+2588" + str(random.choice([2,3,4,5])) + str(random.randint(1000000,9999999)),
            license_number="MZ-" + str(random.randint(100000,999999)), status="active")
    drvo.append(d)
for i in range(3):
    d = drvo[i]
    if not d.user:
        un = "motorista%d" % (i + 1)
        u, _ = User.objects.get_or_create(username=un, defaults={
            "email": "%s@busup.mz" % un, "phone": d.phone, "is_active": True})
        u.set_password("Busup@2026"); u.save()
        if drole: UserRole.objects.get_or_create(user=u, role=drole)
        d.user = u; d.save(update_fields=["user"])

# ---------------- AGENTS (+users p/ alguns) ----------------
AGENTS = ["Sérgio Matola","Paulo Nhantumbo","Hélder Chaúque","Lúcia Mondlane","Aida Come","Osvaldo Bila"]
arole = Role.objects.filter(code="agent").first()
ago = []
for nm in AGENTS:
    a = Agent.objects.filter(full_name=nm).first() or Agent.objects.create(
        full_name=nm, phone="+2588" + str(random.choice([2,3,6,7])) + str(random.randint(1000000,9999999)),
        status="active")
    ago.append(a)
for i in range(2):
    a = ago[i]
    if not a.user:
        un = "agente%d" % (i + 1)
        u, _ = User.objects.get_or_create(username=un, defaults={"email": "%s@busup.mz" % un, "is_active": True})
        u.set_password("Busup@2026"); u.save()
        if arole: UserRole.objects.get_or_create(user=u, role=arole)
        a.user = u; a.save(update_fields=["user"])

# ---------------- FARES ----------------
fp_single, _ = FareProduct.objects.get_or_create(name="Viagem simples", defaults={"product_type":"single_trip","status":"active"})
fp_daily, _  = FareProduct.objects.get_or_create(name="Passe diário",   defaults={"product_type":"daily_pass","status":"active"})
fp_month, _  = FareProduct.objects.get_or_create(name="Passe mensal",   defaults={"product_type":"monthly_pass","status":"active"})
for r in routeo:
    FareRule.objects.get_or_create(fare_product=fp_single, route=r, passenger_class="standard",
        defaults={"calculation_method":"fixed","fixed_amount":Decimal(random.choice(["12.00","15.00","18.00","20.00"]))})

# ---------------- PACKAGES ----------------
Package.objects.get_or_create(name="Passe Mensal Urbano", defaults={
    "discount_type":"free_trips","discount_value":Decimal("0"),"price":Decimal("750.00"),
    "validity_days":30,"max_trips":60,"status":"active"})
Package.objects.get_or_create(name="Passe Estudante", defaults={
    "discount_type":"percentage","discount_value":Decimal("30"),"price":Decimal("450.00"),
    "validity_days":30,"max_trips":0,"status":"active"})

# ---------------- PASSENGERS + WALLETS + CARDS ----------------
FIRST = ["João","Maria","Carlos","Ana","Paulo","Fátima","Nuno","Isabel","Rui","Teresa","Hélio",
 "Cristina","Manuel","Sónia","Edson","Vânia","Gil","Cátia","Denilson","Márcia","Osvaldo","Lurdes",
 "Yolanda","Nélio","Bruno","Sheila","Kevin","Telma","Adérito","Elsa","Jéssica","Wilson"]
LAST = ["Cossa","Mabjaia","Tembe","Sitoe","Nhaca","Macuácua","Zandamela","Chissano","Muianga","Come",
 "Mondlane","Nhantumbo","Chaúque","Matsinhe","Bila","Langa","Mucavele","Fumo","Simango","Guambe"]
pax = []
seen_ph = set(PassengerAccount.objects.values_list("phone_number", flat=True))
while len(pax) < 45:
    fn = random.choice(FIRST) + " " + random.choice(LAST)
    ph = "+2588" + str(random.choice([2,3,4,5,6,7])) + str(random.randint(1000000,9999999))
    if ph in seen_ph:
        continue
    seen_ph.add(ph)
    p = PassengerAccount.objects.create(full_name=fn, phone_number=ph, status="active",
        document_type=random.choice(["bi","bi","passport",""]),
        document_number=str(random.randint(100000000,999999999)))
    w = Wallet.objects.create(passenger_account=p, status="active",
        balance_cached=Decimal(str(random.choice([50,80,120,150,200,250,300,420,500,650,800,1200]))))
    if random.random() < 0.7:
        Card.objects.create(card_type="physical", card_uid="04%d" % random.randint(10**13, 10**14 - 1),
            card_technology="mifare_desfire", wallet=w, passenger_account=p, status="active", activated_at=now)
    else:
        Card.objects.create(card_type="digital", card_technology="qr_code",
            wallet=w, passenger_account=p, status="active", activated_at=now)
    pax.append((p, w))

# ---------------- TRIPS ----------------
for d in range(0, 7):
    for _ in range(random.randint(3, 6)):
        r = random.choice(routeo); v = random.choice(veho); dr = random.choice(drvo); ag = random.choice(ago)
        dep = (lnow - timedelta(days=d)).replace(hour=random.randint(5,19),
                minute=random.choice([0,15,30,45]), second=0, microsecond=0)
        if d == 0:
            st = random.choice(["scheduled","boarding","departed","completed","completed"])
        else:
            st = "completed"
        t = Trip.objects.create(route=r, vehicle=v, driver=dr, agent=ag, status=st,
            planned_departure_at=dep, planned_arrival_at=dep + timedelta(hours=1))
        if st in ("departed","completed"):
            t.actual_departure_at = dep
        if st == "completed":
            t.actual_arrival_at = dep + timedelta(hours=1)
        t.save()

# ---------------- VALIDATIONS (revenue + charts) ----------------
AMTS = ["10.00","12.00","15.00","15.00","18.00","20.00","25.00"]
vcount = {"approved":0,"denied":0}
vi = 0
def mk_val(dt, approved):
    global vi
    vi += 1
    p, w = random.choice(pax)
    r = random.choice(routeo)
    amt = Decimal(random.choice(AMTS))
    ve = ValidationEvent.objects.create(
        validation_type=random.choice(["card_pay_as_you_go","card_pay_as_you_go","qr_pay_as_you_go"]),
        passenger_account=p, wallet=w, route=r,
        amount_debited=amt if approved else Decimal("0.00"),
        status="approved" if approved else "denied",
        failure_reason="" if approved else "insufficient_balance",
        idempotency_key="seed-val-%s-%d-%d" % (dt.strftime("%Y%m%d"), vi, random.randint(1000,9999)))
    backdate(ValidationEvent, ve.pk, created_at=dt, updated_at=dt)
    vcount["approved" if approved else "denied"] += 1

for d in range(1, 7):
    base = (lnow - timedelta(days=d))
    for _ in range(random.randint(45, 75)):
        dt = base.replace(hour=random.randint(5,20), minute=random.randint(0,59), second=0, microsecond=0)
        mk_val(dt, random.random() > 0.08)
# hoje — espalhado por hora até agora
for _ in range(random.randint(60, 85)):
    h = random.randint(5, max(6, lnow.hour))
    dt = lnow.replace(hour=h, minute=random.randint(0,59), second=0, microsecond=0)
    if dt > now:
        dt = now - timedelta(minutes=random.randint(1, 40))
    mk_val(dt, random.random() > 0.06)

# ---------------- TOP-UPS (WalletTransaction) ----------------
ti = 0
def mk_topup(dt):
    global ti
    ti += 1
    p, w = random.choice(pax)
    amt = Decimal(random.choice(["50.00","100.00","100.00","150.00","200.00","250.00","300.00","500.00"]))
    bb = w.balance_cached
    wt = WalletTransaction.objects.create(wallet=w, type="topup", direction="credit",
        amount=amt, signed_amount=amt, balance_before=bb, balance_after=bb + amt,
        reference="TOPUP-%s-%d-%d" % (dt.strftime("%Y%m%d"), ti, random.randint(1000,9999)),
        source=random.choice(["mpesa","emola","pos"]), status="confirmed")
    backdate(WalletTransaction, wt.pk, created_at=dt, updated_at=dt)

for d in range(1, 7):
    base = (lnow - timedelta(days=d))
    for _ in range(random.randint(12, 22)):
        mk_topup(base.replace(hour=random.randint(6,20), minute=random.randint(0,59), second=0, microsecond=0))
for _ in range(random.randint(14, 24)):
    dt = lnow.replace(hour=random.randint(6, max(7, lnow.hour)), minute=random.randint(0,59), second=0, microsecond=0)
    if dt > now:
        dt = now - timedelta(minutes=random.randint(1, 60))
    mk_topup(dt)

# ---------------- PAYMENTS (PaymentIntent) ----------------
pi = 0
for d in range(0, 7):
    base = (lnow - timedelta(days=d))
    for _ in range(random.randint(12, 20)):
        pi += 1
        prov = random.choice(["mpesa","mpesa","emola"])
        amt = Decimal(random.choice(["50.00","100.00","150.00","200.00","300.00","500.00"]))
        conf = base.replace(hour=random.randint(6,20), minute=random.randint(0,59), second=0, microsecond=0)
        if conf > now:
            conf = now - timedelta(minutes=random.randint(1, 90))
        p, w = random.choice(pax)
        obj = PaymentIntent.objects.create(
            reference="PI-%s-%d-%d" % (base.strftime("%Y%m%d"), pi, random.randint(1000,9999)),
            idempotency_key="idem-%s-%d-%d" % (base.strftime("%Y%m%d"), pi, random.randint(10000,99999)),
            purpose="mobile_wallet_topup", amount=amt, payer_phone=p.phone_number,
            provider=prov, status="confirmed", wallet=w)
        backdate(PaymentIntent, obj.pk, created_at=conf, updated_at=conf, confirmed_at=conf)
for _ in range(5):
    pi += 1
    p, w = random.choice(pax)
    PaymentIntent.objects.create(
        reference="PI-PEND-%d-%d" % (pi, random.randint(1000,9999)),
        idempotency_key="idem-pend-%d-%d" % (pi, random.randint(10000,99999)),
        purpose="mobile_wallet_topup", amount=Decimal("150.00"), payer_phone=p.phone_number,
        provider=random.choice(["mpesa","emola"]), status="pending", wallet=w)

# ---------------- DEVICES ----------------
for i in range(7):
    Device.objects.get_or_create(serial_number="SUNMI-P2-%04d" % (i + 1), defaults={
        "device_type": "pos_terminal", "model_name": random.choice(["P2 Lite","V2 Pro","D3 Mini"]),
        "manufacturer": random.choice(["SUNMI","Urovo"]),
        "status": "active" if i < 5 else "pending_activation",
        "activation_code": str(random.randint(100000, 999999)),
        "app_version": "1.3.4", "app_version_code": 8,
        "assigned_agent": ago[i % len(ago)] if i < 5 else None,
        "capabilities": ["nfc_reader","qr_scanner"],
        "last_seen_at": now - timedelta(minutes=random.randint(1, 240)) if i < 5 else None,
        "activated_at": now - timedelta(days=random.randint(1, 30)) if i < 5 else None})

# ---------------- SUMMARY ----------------
from django.db.models import Sum
print("=== SEED COMPLETO ===")
print("Rotas:", Route.objects.count(), "| Paragens:", Stop.objects.count(),
      "| Veiculos:", Vehicle.objects.count(), "| Motoristas:", Driver.objects.count(),
      "| Agentes:", Agent.objects.count())
print("Passageiros:", PassengerAccount.objects.count(),
      "| Carteiras (saldo total):", Wallet.objects.filter(status="active").aggregate(s=Sum("balance_cached"))["s"],
      "| Cartoes:", Card.objects.count())
print("Viagens:", Trip.objects.count(),
      "| Validacoes:", ValidationEvent.objects.count(), vcount,
      "| Top-ups:", WalletTransaction.objects.filter(type="topup").count(),
      "| Pagamentos:", PaymentIntent.objects.count(), "| Dispositivos:", Device.objects.count())
tr = ValidationEvent.objects.filter(status="approved").aggregate(s=Sum("amount_debited"))["s"]
print("Receita total validacoes:", tr, "MZN")
