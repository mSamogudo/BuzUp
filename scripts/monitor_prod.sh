#!/usr/bin/env sh
#
# Monitor on-host do BuzUp PRODUCAO: verifica os sites e a saude dos
# containers. Em falha, regista no log e (se MONITOR_WEBHOOK_URL estiver
# definido) faz POST de um alerta (Slack/Discord/healthchecks.io).
#
# Corre NO SERVIDOR via cron, ex. de 5 em 5 min:
#   cp scripts/monitor_prod.sh /opt/buzup-ops/monitor_prod.sh
#   chmod +x /opt/buzup-ops/monitor_prod.sh
#   printf '*/5 * * * * root MONITOR_WEBHOOK_URL=... /opt/buzup-ops/monitor_prod.sh >/dev/null 2>&1\n' \
#       > /etc/cron.d/buzup-monitor
#
# NOTA: isto e um monitor ON-HOST (deteta containers/gateway em baixo). Para
# um verdadeiro alerta de host-down, juntar um monitor EXTERNO (UptimeRobot /
# healthchecks.io) a apontar para https://buzup.updigital.co.mz/.
#
set -u

SITES="${BUZUP_MONITOR_SITES:-buzup.updigital.co.mz buzup-test.updigital.co.mz}"
CONTAINERS="${BUZUP_MONITOR_CONTAINERS:-buzup_backend_prod buzup_gateway_prod buzup_db_prod}"
LOG="${BUZUP_MONITOR_LOG:-/opt/backups/buzup/monitor.log}"
WEBHOOK="${MONITOR_WEBHOOK_URL:-}"

mkdir -p "$(dirname "$LOG")"
problems=""

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

# 1) Sites: esperar HTTP 200.
for site in $SITES; do
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 12 "https://$site/" 2>/dev/null)"
    if [ "$code" != "200" ]; then
        problems="$problems site:$site=$code"
    fi
done

# 2) Containers: esperar estado running + (se tiver healthcheck) healthy.
for c in $CONTAINERS; do
    state="$(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null || echo missing)"
    health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$c" 2>/dev/null || echo missing)"
    if [ "$state" != "running" ] || { [ "$health" != "none" ] && [ "$health" != "healthy" ]; }; then
        problems="$problems container:$c=$state/$health"
    fi
done

if [ -n "$problems" ]; then
    msg="BuzUp PROD ALERTA:$problems"
    log "$msg"
    if [ -n "$WEBHOOK" ]; then
        curl -s --max-time 10 -X POST "$WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{\"text\":\"$msg\",\"content\":\"$msg\"}" >/dev/null 2>&1 || true
    fi
    exit 1
fi

log "OK — todos os sites 200 e containers healthy"
exit 0
