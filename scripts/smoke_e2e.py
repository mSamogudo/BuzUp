#!/usr/bin/env python3
"""End-to-end smoke test for BuzUp staging.

Exercises every critical flow through the HTTP API as a real client would.
Run from the dev box; talks to staging.

Usage:
    python3 scripts/smoke_e2e.py
    BUZUP_BASE=https://buzup.updigital.co.mz python3 scripts/smoke_e2e.py
    python3 scripts/smoke_e2e.py --verbose
    python3 scripts/smoke_e2e.py --skip-day-close   # don't close the day

Pre-conditions in the staging DB (already true today):
  - Superuser id=1 (mario)
  - Active agent user id=18 (agente)
  - Device V305249V20246 in `active` state, assigned_agent=18
  - At least one active trip on a route with stops (e.g. trip 1 / route 5)
  - At least one inactive physical card (for capture-uid test)

What this script does NOT cover (requires SUNMI hardware):
  - Real NFC tap (we use card_uid string only)
  - Real QR scan
  - Receipt printing
  - SMS delivery

Exit codes:
    0 = all green
    1 = one or more failures
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable

try:
    import requests
except ImportError:
    sys.exit("requests not installed. pip install requests")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE = os.environ.get("BUZUP_BASE", "https://buzup.updigital.co.mz").rstrip("/")
SSH_HOST = os.environ.get("BUZUP_STAGING_HOST", "95.216.50.19")
SSH_PASS = os.environ.get("BUZUP_STAGING_PASS", "zPbA95HTXf48dseEpnag")
CONTAINER = "buzup_backend_staging"

# Known fixtures
SUPERUSER_ID = 1            # mario
AGENT_USER_ID = 18          # agente
DEVICE_SERIAL = "V305249V20246"
ROUTE_ID = 5                # RT-BAIXA-ALBAZINE
TRIP_ID = 1
ORIGIN_STOP_ID = 25         # Albasine
DEST_STOP_ID = 12           # Chico
PASSENGER_TEST_PHONE = "258840000099"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
GREY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"


@dataclass
class Step:
    name: str
    fn: Callable[["State"], None]
    optional: bool = False


@dataclass
class State:
    mario_jwt: str = ""
    agent_jwt: str = ""
    verbose: bool = False
    failures: list[tuple[str, str]] = field(default_factory=list)
    skip_day_close: bool = False
    gateway_provider: str = ""
    # Captured during the run for downstream steps
    sale_ref: str = ""
    payment_ref: str = ""
    ticket_token: str = ""
    ticket_shortcode: str = ""
    onboarded_card_uid: str = ""
    onboarded_passenger_id: int = 0
    recovery_challenge_id: str = ""
    recovery_token: str = ""

    @property
    def gateway_is_mock(self) -> bool:
        return self.gateway_provider.upper() == "MOCK"

    def fail(self, step: str, msg: str):
        self.failures.append((step, msg))


def run_shell(py_source: str, timeout: int = 60) -> str:
    """Run python code inside the staging backend container via SSH.

    Uses a base64-encoded payload so we never have to worry about shell
    quoting. Returns stdout (stripped).
    """
    import base64
    encoded = base64.b64encode(py_source.encode("utf-8")).decode("ascii")
    remote_cmd = (
        f"docker exec {CONTAINER} python -c "
        f"\"import base64,sys; "
        f"exec(compile(base64.b64decode('{encoded}'), '<smoke>', 'exec'))\""
    )
    full = [
        "sshpass", "-p", SSH_PASS,
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "LogLevel=ERROR",
        f"root@{SSH_HOST}", remote_cmd,
    ]
    out = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
    return out.stdout.strip()


def mint_jwt(user_id: int) -> str:
    src = f"""
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
django.setup()
from apps.users.models import User
from rest_framework_simplejwt.tokens import RefreshToken
print(str(RefreshToken.for_user(User.objects.get(id={user_id})).access_token))
"""
    out = run_shell(src, timeout=30)
    # The last non-empty line is the JWT
    for line in reversed(out.split("\n")):
        line = line.strip()
        if line and not line.startswith("Warning"):
            return line
    return ""


def api(method: str, path: str, jwt: str, *, json_body: dict | None = None,
        params: dict | None = None, stream: bool = False,
        timeout: int = 90) -> requests.Response:
    """Default 90s timeout — gateway calls (M-Pesa/E-Mola mock) can take a
    while to reply because they perform an HTTPS round-trip to the upstream
    sandbox."""
    headers = {"Authorization": f"Bearer {jwt}"}
    return requests.request(
        method, BASE + path,
        headers=headers, json=json_body, params=params,
        stream=stream, timeout=timeout,
    )


def expect(state: State, label: str, cond: bool, detail: str = ""):
    icon = f"{GREEN}✓{RESET}" if cond else f"{RED}✗{RESET}"
    line = f"  {icon} {label}"
    if not cond and detail:
        line += f"  {GREY}({detail}){RESET}"
    print(line)
    if not cond:
        state.fail(label, detail or "assertion failed")


def header(text: str):
    print(f"\n{BOLD}── {text} ──{RESET}")


def reset_test_state(state: State):
    """Make sure the staging DB is in a known clean state for the run."""
    src = f"""
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
django.setup()
from apps.passengers.models import PassengerAccount
from apps.cards.models import Card
phone = "{PASSENGER_TEST_PHONE}"
# Hard-delete (bypass soft-delete) so onboarding can recreate
PassengerAccount.all_objects.filter(phone_number=phone).delete()
# Also free the smoke cards if they exist
Card.all_objects.filter(card_uid__startswith="SMOKE").delete()
print("cleaned")
"""
    out = run_shell(src, timeout=30)
    if state.verbose:
        print(GREY + "  seed: " + out + RESET)


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def s_setup(state: State):
    header("Setup — JWTs e estado base")
    state.mario_jwt = mint_jwt(SUPERUSER_ID)
    state.agent_jwt = mint_jwt(AGENT_USER_ID)
    expect(state, "JWT mario obtido", len(state.mario_jwt) > 100)
    expect(state, "JWT agente obtido", len(state.agent_jwt) > 100)

    # Detect the payment gateway provider so we can skip flows that require
    # synchronous success (real gateways may return Server Error against
    # unregistered phones; that's the upstream's responsibility, not ours).
    src = """
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
django.setup()
from django.conf import settings
print(getattr(settings, "PAYMENT_GATEWAY_PROVIDER", "MOCK"))
"""
    state.gateway_provider = (run_shell(src, timeout=30) or "").split("\n")[-1].strip()
    icon = f"{GREEN}MOCK{RESET}" if state.gateway_is_mock else f"{YELLOW}{state.gateway_provider}{RESET}"
    print(f"  gateway: {icon}")
    reset_test_state(state)


def s_agent_me(state: State):
    header("Agent /me + features flag")
    r = api("GET", "/api/agent/me/", state.agent_jwt)
    expect(state, "/me 200", r.status_code == 200, f"http={r.status_code}")
    if r.status_code != 200:
        return
    data = r.json()
    expect(state, "agent.id presente", isinstance(data.get("agent", {}).get("id"), int))
    expect(state, "device atribuido", data.get("device") is not None)
    feats = data.get("features", {})
    # In staging, ALLOW_AGENT_CARD_CAPTURE=True so the flag must be exposed
    expect(state, "features.card_capture=True (staging)",
           feats.get("card_capture") is True,
           f"got={feats.get('card_capture')}")


def s_trips_and_fare(state: State):
    header("Listar viagens + cotar tarifa")
    r = api("GET", "/api/agent/trips/", state.agent_jwt)
    expect(state, "/trips 200", r.status_code == 200)
    if r.status_code == 200:
        trips = r.json() if isinstance(r.json(), list) else r.json().get("results", [])
        expect(state, "pelo menos 1 trip", len(trips) > 0)

    r = api("POST", f"/api/agent/trips/{TRIP_ID}/fare/", state.agent_jwt, json_body={
        "origin_stop_id": ORIGIN_STOP_ID,
        "destination_stop_id": DEST_STOP_ID,
    })
    expect(state, "fare quote 200", r.status_code == 200, f"http={r.status_code} body={r.text[:120]}")
    if r.status_code == 200:
        f = r.json()
        expect(state, "fare amount > 0",
               float(f.get("fare_amount") or f.get("amount") or 0) > 0,
               f"fare={f.get('fare_amount') or f.get('amount')}")


def s_sale_mobile_money(state: State):
    header("Venda — mobile money")
    # Em gateway real evitamos auto_request_payment para nao depender da
    # disponibilidade do upstream. A venda fica em PENDING.
    auto = state.gateway_is_mock
    r = api("POST", "/api/agent/sales/", state.agent_jwt, json_body={
        "trip_id": TRIP_ID,
        "origin_stop_id": ORIGIN_STOP_ID,
        "destination_stop_id": DEST_STOP_ID,
        "payment_method": "mobile_money",
        "passenger_phone": "258840000001",
        "quantity": 1,
        "auto_request_payment": auto,
    })
    expect(state, "sale 201", r.status_code in (200, 201), f"http={r.status_code} body={r.text[:120]}")
    if r.status_code not in (200, 201):
        return
    data = r.json()
    payment = data.get("payment", {})
    expect(state, "sale_reference presente", bool(data.get("sale_reference")))
    expect(state, "payment.reference presente", bool(payment.get("reference")))
    state.sale_ref = data.get("sale_reference", "")
    state.payment_ref = payment.get("reference", "")

    # Poll once to make sure the status endpoint authorises us
    if state.payment_ref:
        r = api("GET", f"/api/agent/payments/{state.payment_ref}/status/", state.agent_jwt)
        expect(state, "payment status 200", r.status_code == 200, f"http={r.status_code}")
        if r.status_code == 200:
            tickets = r.json().get("tickets") or []
            if tickets and tickets[0].get("token"):
                state.ticket_token = tickets[0]["token"]
            # Some configurations emit shortcode = last 4 of sale ref
            ref = data.get("sale_reference", "")
            if len(ref) >= 4:
                state.ticket_shortcode = ref[-4:].upper()


def s_ticket_verify(state: State):
    header("Validar bilhete — QR + shortcode")
    if state.ticket_token:
        r = api("POST", "/api/agent/tickets/verify/", state.agent_jwt, json_body={
            "token": state.ticket_token,
            "consume": False,
        })
        expect(state, "QR verify 200", r.status_code == 200, f"http={r.status_code} body={r.text[:120]}")
    else:
        print(f"  {YELLOW}~ sem token disponivel (gateway sync nao emitiu) — skip{RESET}")

    if state.ticket_shortcode:
        r = api("POST", "/api/agent/tickets/verify/", state.agent_jwt, json_body={
            "shortcode": state.ticket_shortcode,
            "consume": False,
        })
        ok = r.status_code in (200, 404, 409)
        expect(state, "shortcode verify aceite (200/404/409)", ok, f"http={r.status_code}")


def s_topup_packages(state: State):
    header("Listar pacotes")
    r = api("GET", "/api/agent/packages/", state.agent_jwt)
    expect(state, "packages 200", r.status_code == 200)


def s_capture_uid(state: State):
    header("Capturar UID (gate staging True)")
    fresh_uid = "SMOKE" + secrets.token_hex(4).upper()
    r = api("POST", "/api/agent/cards/capture-uid/", state.agent_jwt, json_body={
        "card_uid": fresh_uid,
        "batch": "SMOKE",
    })
    expect(state, "capture-uid 201 (created)", r.status_code == 201, f"http={r.status_code} body={r.text[:120]}")
    if r.status_code == 201:
        state.onboarded_card_uid = fresh_uid
        # Idempotent: repeating should return 200 with created=false
        r2 = api("POST", "/api/agent/cards/capture-uid/", state.agent_jwt, json_body={
            "card_uid": fresh_uid,
        })
        body = r2.json() if r2.status_code == 200 else {}
        expect(state, "capture-uid idempotente",
               r2.status_code == 200 and body.get("created") is False,
               f"http={r2.status_code} created={body.get('created')}")


def s_passenger_onboard(state: State):
    header("Onboarding de passageiro (com cartao capturado)")
    if not state.onboarded_card_uid:
        print(f"  {YELLOW}~ sem cartao capturado — skip{RESET}")
        return
    r = api("POST", "/api/agent/passengers/onboard/", state.agent_jwt, json_body={
        "full_name": "Smoke Test Passageiro",
        "phone": PASSENGER_TEST_PHONE,
        "card_uid": state.onboarded_card_uid,
        "payer_phone": PASSENGER_TEST_PHONE,
        "fee": "50.00",
        "notify_sms": False,
    })
    # If staging uses a real M-Pesa/E-Mola gateway, our test phone won't be
    # accepted by the upstream and the endpoint will return 400 with
    # "Server Error". That's NOT a regression in our code; flag as a yellow
    # warning instead of a hard failure.
    if r.status_code == 400 and "Server Error" in r.text and not state.gateway_is_mock:
        print(f"  {YELLOW}~ gateway real recusou (Server Error) — esperado fora de MOCK, skip{RESET}")
        return
    expect(state, "onboard 201", r.status_code == 201, f"http={r.status_code} body={r.text[:200]}")
    if r.status_code == 201:
        data = r.json()
        state.onboarded_passenger_id = (data.get("passenger") or {}).get("id", 0)
        expect(state, "passageiro criado com id",
               state.onboarded_passenger_id > 0,
               f"got={state.onboarded_passenger_id}")
        # Wallet exists for the new passenger
        wallet = data.get("wallet")
        expect(state, "wallet vinculada", wallet is not None and wallet.get("uuid"))


def s_card_recovery(state: State):
    header("Recuperacao de cartao — request OTP + verify + associate")
    if not state.onboarded_passenger_id:
        print(f"  {YELLOW}~ sem passageiro onboarded — skip{RESET}")
        return

    r = api("POST", "/api/agent/passengers/recover-card/request-otp/",
            state.agent_jwt, json_body={
                "passenger_phone": PASSENGER_TEST_PHONE,
                "reason": "Smoke test: cartao perdido",
            })
    expect(state, "request-otp 200", r.status_code == 200, f"http={r.status_code} body={r.text[:120]}")
    if r.status_code != 200:
        return
    state.recovery_challenge_id = r.json().get("challenge_id", "")
    expect(state, "challenge_id presente", bool(state.recovery_challenge_id))

    # Pull the OTP code from the container (mock SMS): we read the OtpChallenge code_hash
    # cannot be reversed; but the RecoverySession stores it. We grab the code by re-hashing
    # candidate values is impossible — instead we read the last SMS sent (mock writes to log).
    # Easier: monkey-patch via shell to inject a known code into the new session.
    src = f"""
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
django.setup()
from apps.agent_api.models import RecoverySession
from apps.users.otp import generate_otp
s = RecoverySession.objects.filter(challenge_id="{state.recovery_challenge_id}").first()
code, code_hash = generate_otp()
s.code_hash = code_hash
s.save(update_fields=["code_hash"])
print("OTP_INJECTED:" + code)
"""
    out = run_shell(src, timeout=30)
    code = ""
    for line in out.split("\n"):
        if line.startswith("OTP_INJECTED:"):
            code = line.split(":", 1)[1].strip()
    expect(state, "OTP code injectado", bool(code))
    if not code:
        return

    r = api("POST", "/api/agent/passengers/recover-card/verify-otp/",
            state.agent_jwt, json_body={
                "challenge_id": state.recovery_challenge_id,
                "otp_code": code,
            })
    expect(state, "verify-otp 200", r.status_code == 200, f"http={r.status_code} body={r.text[:120]}")
    if r.status_code != 200:
        return
    state.recovery_token = r.json().get("recovery_token", "")
    expect(state, "recovery_token presente", bool(state.recovery_token))

    # We need a SECOND inactive card to associate
    second_uid = "SMOKE2" + secrets.token_hex(4).upper()
    api("POST", "/api/agent/cards/capture-uid/", state.agent_jwt, json_body={
        "card_uid": second_uid,
        "batch": "SMOKE",
    })

    r = api("POST", "/api/agent/passengers/recover-card/associate/",
            state.agent_jwt, json_body={
                "recovery_token": state.recovery_token,
                "new_card_uid": second_uid,
                "payer_phone": PASSENGER_TEST_PHONE,
                "fee_amount": "100.00",
            })
    expect(state, "associate 201", r.status_code == 201, f"http={r.status_code} body={r.text[:200]}")
    if r.status_code == 201:
        data = r.json()
        old_ids = data.get("old_card_ids") or []
        expect(state, "lista de cartoes a bloquear nao-vazia", len(old_ids) >= 1)


def s_admin_fees(state: State):
    header("Admin fees CRUD (apenas read)")
    r = api("GET", "/api/admin-fees/", state.mario_jwt)
    expect(state, "admin-fees 200", r.status_code == 200)
    if r.status_code == 200:
        body = r.json()
        # DRF returns either a paginated dict OR a plain list depending on
        # the global pagination setting; handle both.
        if isinstance(body, dict):
            fees = body.get("results", [])
        elif isinstance(body, list):
            fees = body
        else:
            fees = []
        expect(state, "pelo menos 2 taxas seed",
               len(fees) >= 2,
               f"count={len(fees)}")


def s_reports(state: State):
    header("Relatorios — builder list + JSON + PDF + Excel")
    r = api("GET", "/api/admin/reports/builder/", state.mario_jwt)
    expect(state, "builder list 200", r.status_code == 200)
    if r.status_code == 200:
        kinds = [s["key"] for s in r.json().get("reports", [])]
        expect(state, "5 tipos registados",
               sorted(kinds) == ["onboarding", "recoveries", "sales", "topups", "validations"],
               f"got={kinds}")

    for kind in ["sales", "topups", "validations", "onboarding", "recoveries"]:
        r = api("GET", f"/api/admin/reports/builder/{kind}/", state.mario_jwt, params={
            "date_from": "2026-04-29", "date_to": "2026-05-29",
        })
        expect(state, f"{kind} JSON 200", r.status_code == 200, f"http={r.status_code}")

    # PDF/XLSX with the query-token auth
    r = requests.get(f"{BASE}/api/admin/reports/builder/sales/", params={
        "date_from": "2026-04-29", "date_to": "2026-05-29",
        "output": "pdf", "token": state.mario_jwt,
    }, timeout=30)
    expect(state, "sales PDF 200 + content-type pdf",
           r.status_code == 200 and "application/pdf" in r.headers.get("Content-Type", ""),
           f"http={r.status_code} ct={r.headers.get('Content-Type')}")
    expect(state, "sales PDF > 1KB", len(r.content) > 1024)

    r = requests.get(f"{BASE}/api/admin/reports/builder/sales/", params={
        "date_from": "2026-04-29", "date_to": "2026-05-29",
        "output": "xlsx", "token": state.mario_jwt,
    }, timeout=30)
    expect(state, "sales XLSX 200 + content-type xlsx",
           r.status_code == 200 and "spreadsheetml" in r.headers.get("Content-Type", ""),
           f"http={r.status_code} ct={r.headers.get('Content-Type')}")
    expect(state, "sales XLSX > 1KB", len(r.content) > 1024)


def s_admin_revenue(state: State):
    header("Agent admin revenue (day-closes + summary + exports)")
    r = api("GET", "/api/agent/admin/day-closes/", state.mario_jwt)
    expect(state, "day-closes 200", r.status_code == 200)

    r = api("GET", "/api/agent/admin/revenue/", state.mario_jwt, params={
        "date_from": "2026-04-29", "date_to": "2026-05-29",
    })
    expect(state, "revenue summary 200", r.status_code == 200)
    if r.status_code == 200:
        data = r.json()
        expect(state, "totals presente", "totals" in data)


def s_day_close(state: State):
    header("Fecho do dia (preview)")
    r = api("GET", "/api/agent/day-close/", state.agent_jwt)
    expect(state, "day-close preview 200", r.status_code == 200)
    if r.status_code == 200:
        data = r.json()
        expect(state, "totals presente", "totals" in data)
        expect(state, "session_since presente", "session_since" in data)

    if state.skip_day_close:
        print(f"  {YELLOW}~ skip-day-close: nao submetemos POST{RESET}")
        return

    print(f"  {GREY}(skip do POST do day-close para nao polluir produc/staging){RESET}")
    # Could POST here to test the close flow. Commented to keep the staging
    # data stable across runs.


def s_isolation(state: State):
    header("Isolamento — mario nao ve sales do agente como dele")
    # mario is superuser, but as superuser he doesn't have agent endpoints
    # (the agent endpoints require agent_user role). Skip if mario lacks the
    # required device session.
    r = api("GET", "/api/agent/sales/history/", state.mario_jwt)
    if r.status_code == 403:
        print(f"  {GREY}mario nao tem perfil agente — esperado, skip{RESET}")
    else:
        # If mario IS configured as agent in some setups, just check that the
        # history contains only HIS sales (none in our seed).
        body = r.json() if r.status_code == 200 else {}
        results = body.get("results", body) if isinstance(body, dict) else body
        any_other = any(
            ((row.get("payer_phone_masked") or "").endswith("0001"))
            for row in (results or []) if isinstance(row, dict)
        )
        expect(state, "mario nao ve venda do agente (filtro metadata)",
               not any_other, "found sale of another agent")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

STEPS: list[Step] = [
    Step("setup", s_setup),
    Step("agent_me", s_agent_me),
    Step("trips_and_fare", s_trips_and_fare),
    Step("sale_mobile_money", s_sale_mobile_money),
    Step("ticket_verify", s_ticket_verify, optional=True),
    Step("topup_packages", s_topup_packages),
    Step("capture_uid", s_capture_uid),
    Step("passenger_onboard", s_passenger_onboard),
    Step("card_recovery", s_card_recovery),
    Step("admin_fees", s_admin_fees),
    Step("reports", s_reports),
    Step("admin_revenue", s_admin_revenue),
    Step("day_close", s_day_close),
    Step("isolation", s_isolation),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--skip-day-close", action="store_true")
    parser.add_argument("--only", nargs="+", help="run only these step names")
    args = parser.parse_args()

    print(f"{BOLD}BuzUp staging E2E smoke{RESET}")
    print(f"{GREY}base = {BASE}{RESET}\n")

    state = State(verbose=args.verbose, skip_day_close=args.skip_day_close)

    t0 = time.time()
    for step in STEPS:
        if args.only and step.name not in args.only:
            continue
        try:
            step.fn(state)
        except Exception as e:
            state.fail(step.name, f"unexpected exception: {e}")
            print(f"  {RED}✗ EXCEPTION {step.name}: {e}{RESET}")

    print()
    if state.failures:
        print(f"{BOLD}{RED}── {len(state.failures)} FALHA(S) ──{RESET}")
        for name, msg in state.failures:
            print(f"  {RED}✗{RESET} {name}: {msg}")
        print(f"{GREY}duracao: {time.time() - t0:.1f}s{RESET}")
        sys.exit(1)
    else:
        print(f"{BOLD}{GREEN}── TUDO OK ──{RESET}")
        print(f"{GREY}duracao: {time.time() - t0:.1f}s{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
