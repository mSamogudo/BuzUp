"""Ambitos de bilhete de descarga, num sitio so.

Cada vista que serve ficheiros declara o seu `download_scope`, e o endpoint que
emite bilhetes so aceita valores desta lista. Um bilhete emitido para um QR nao
pode ser usado para puxar um relatorio financeiro.
"""

from __future__ import annotations

PASSENGER_EXTRACT = "passenger_extract"
CARD_QR = "card_qr"
REPORT_BUILDER = "report_builder"
AGENT_DAY_CLOSE = "agent_day_close"
TRIP_MANIFEST = "trip_manifest"

DOWNLOAD_SCOPES = frozenset({
    PASSENGER_EXTRACT,
    CARD_QR,
    REPORT_BUILDER,
    AGENT_DAY_CLOSE,
    TRIP_MANIFEST,
})
