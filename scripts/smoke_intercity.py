#!/usr/bin/env python3
"""Smoke test dos fluxos novos: venda interurbana, lugares e pedidos de contacto.

Caixa-preta contra um ambiente a correr, sem gastar dinheiro: exercita as
recusas (lugar ocupado, lotação, janela de venda fechada) e os endpoints
públicos de leitura.

  BUZUP_BASE=https://buzup-test.updigital.co.mz python3 scripts/smoke_intercity.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

BASE = os.environ.get("BUZUP_BASE", "https://buzup-test.updigital.co.mz").rstrip("/")
G, R, Y, B, X = "\033[92m", "\033[91m", "\033[93m", "\033[1m", "\033[0m"

passed = failed = 0


def check(label: str, ok: bool, detail: str = "") -> bool:
    global passed, failed
    if ok:
        passed += 1
        print(f"  {G}✓{X} {label}")
    else:
        failed += 1
        print(f"  {R}✗{X} {label} {detail}")
    return ok


def section(title: str) -> None:
    print(f"\n{B}── {title} ──{X}")


def call(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw.strip().startswith(("{", "[")) else {"_raw": raw})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"_raw": raw[:200]}
    except Exception as e:  # rede
        return 0, {"_error": str(e)}


def main() -> int:
    print(f"{B}Smoke interurbano — {BASE}{X}")

    section("Catálogo público")
    st, cat = call("GET", "/api/public/trips/?sellable=1")
    check("catálogo 200", st == 200, f"(http={st})")
    stops = cat.get("stops", [])
    check("só paragens vendáveis", 0 < len(stops) <= 20, f"({len(stops)} paragens)")
    by_name = {s["name"]: s["id"] for s in stops}
    o_name = next((k for k in by_name if "Maputo" in k), "")
    d_name = next((k for k in by_name if "Nelspruit" in k), "")
    origin = by_name.get(o_name)
    dest = by_name.get(d_name)
    if not check("percurso de demonstração presente", bool(origin and dest)):
        return 1

    section("Pesquisa por data futura")
    day = (date.today() + timedelta(days=7)).isoformat()
    st, res = call("GET", f"/api/public/trips/?origin={origin}&destination={dest}&date={day}")
    check("pesquisa 200", st == 200, f"(http={st})")
    trips = res.get("trips", [])
    check("devolve partidas futuras", len(trips) > 0, f"({len(trips)})")
    if not trips:
        return 1
    trip = trips[0]
    for field in ("seats_available", "on_sale", "sale_unavailable_reason", "fare_amount"):
        check(f"campo {field} presente", field in trip)
    check("tarifa calculada", bool(trip.get("fare_amount")), f"({trip.get('fare_amount')})")

    section("Planta de lugares")
    st, sm = call("GET", f"/api/public/trips/{trip['trip_id']}/seats/")
    check("planta 200", st == 200, f"(http={st})")
    check("tem planta", sm.get("has_seat_map") is True)
    rows = sm.get("rows", [])
    labels = [s["label"] for r in rows for s in r["seats"]]
    check("nº de lugares = capacidade", len(labels) == sm.get("capacity"), f"({len(labels)} vs {sm.get('capacity')})")
    check("etiquetas únicas", len(set(labels)) == len(labels))
    occupied = set(sm.get("occupied", []))
    free = sm.get("available")
    check("livres = capacidade - ocupados", free == sm.get("capacity", 0) - len(occupied),
          f"({free} vs {sm.get('capacity', 0) - len(occupied)})")

    section("Recusas de compra (sem gastar dinheiro)")
    base_payload = {
        "payer_phone": "840000000",
        "route_code": trip["route_code"],
        "origin_stop_id": origin,
        "destination_stop_id": dest,
        "origin_stop": o_name, "destination_stop": d_name,
        "trip_id": trip["trip_id"],
    }

    # a) mais lugares do que existem
    st, body = call("POST", "/api/guest-checkouts/", {**base_payload, "quantity": 999})
    check("lotação recusa quantidade impossível", st in (400, 409),
          f"(http={st} {body.get('detail', '')[:60]})")

    # b) lugar já ocupado
    if occupied:
        taken = sorted(occupied)[0]
        st, body = call("POST", "/api/guest-checkouts/", {
            **base_payload, "quantity": 1,
            "passengers": [{"name": "Teste Smoke", "document_type": "bi",
                            "document_number": "000000000", "seat": taken}],
        })
        check("lugar ocupado é recusado", st == 409, f"(http={st} {body.get('detail', '')[:60]})")
    else:
        print(f"  {Y}~ sem lugares ocupados nesta partida — salta teste de conflito{X}")

    # c) passageiros a menos do que os bilhetes
    st, body = call("POST", "/api/guest-checkouts/", {
        **base_payload, "quantity": 2,
        "passengers": [{"name": "Só Um", "document_type": "bi", "document_number": "1"}],
    })
    check("exige dados de cada passageiro", st == 400, f"(http={st} {body.get('detail', '')[:60]})")

    section("Janela de venda")
    st, past = call("GET", f"/api/public/trips/?origin={origin}&destination={dest}"
                           f"&date={date.today().isoformat()}")
    closed = [t for t in past.get("trips", []) if not t.get("on_sale")]
    if closed:
        check("partida fechada traz motivo legível", bool(closed[0].get("sale_unavailable_reason")),
              f"({closed[0].get('sale_unavailable_reason')})")
        st, body = call("POST", "/api/guest-checkouts/", {**base_payload, "quantity": 1,
                                                          "trip_id": closed[0]["trip_id"]})
        check("compra fora da janela é recusada", st in (400, 409),
              f"(http={st} {body.get('detail', '')[:60]})")
    else:
        print(f"  {Y}~ nenhuma partida fechada hoje — salta{X}")

    section("Pedido de contacto (landing)")
    st, body = call("POST", "/api/public/service-requests/", {
        "name": "Smoke Test", "organization": "QA", "phone": "840000000",
        "interest": "operator", "message": "smoke",
    })
    check("pedido aceite", st == 201, f"(http={st})")
    st, body = call("POST", "/api/public/service-requests/", {"name": "X", "phone": "123"})
    check("telefone inválido é recusado", st == 400, f"(http={st})")

    print(f"\n{B}{G if not failed else R}── {passed} ok, {failed} falhas ──{X}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
