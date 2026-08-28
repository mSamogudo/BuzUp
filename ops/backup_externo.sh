#!/bin/bash
# Manda os dumps de todos os produtos para fora do goup-vps.
#
# Porque e preciso: os backups correm todos os dias e estao bons — mas ficam
# em /opt/backups, no MESMO disco da base de dados. Se a maquina se perder,
# perdem-se as duas coisas ao mesmo tempo. Um backup que so existe onde estao
# os dados que protege nao e um backup: e uma copia.
#
# Serve qualquer destino que fale SSH: uma Storage Box da Hetzner (a mais
# barata, e na mesma rede), outro servidor, um NAS. Nao precisa de rclone nem
# de credenciais de nuvem nenhuma.
#
# --- POR ANTES DE CORRER --------------------------------------------------
#   1. Criar a chave (SEM palavra-passe, para o cron a poder usar):
#        ssh-keygen -t ed25519 -f /root/.ssh/backup_externo -N "" -C backups-goup-vps
#   2. Autorizar a chave no destino (a forma depende do destino; numa Storage
#      Box da Hetzner e por `ssh-copy-id -p 23 -s uXXXXX@uXXXXX.your-storagebox.de`).
#   3. Preencher DESTINO aqui em baixo.
#   4. Provar a mao:  bash /opt/backups/ops/backup_externo.sh
#   5. So depois por no cron, a seguir aos dumps (que acabam pelas 03:50):
#        10 4 * * * /opt/backups/ops/backup_externo.sh >> /var/log/backup_externo.log 2>&1
# ---------------------------------------------------------------------------
set -uo pipefail

DESTINO="${DESTINO:-}"          # ex.: u123456@u123456.your-storagebox.de:backups/goup-vps
PORTA="${PORTA:-22}"            # a Storage Box da Hetzner usa 23
CHAVE="${CHAVE:-/root/.ssh/backup_externo}"
ORIGEM=/opt/backups
# Numeros de quem leva o SMS quando isto falhar. O vigia ja os tem.
CONF=/etc/buzup-vigia.conf

if [ -z "$DESTINO" ]; then
  echo "DESTINO por preencher — leia o cabecalho deste ficheiro." >&2
  exit 2
fi

avisar() {
  # Mesma cadeia de emissores do vigia: se um contentor estiver em baixo,
  # tenta o seguinte. Um aviso que depende do que esta a falhar nao serve.
  local texto="$1"
  [ -f "$CONF" ] || return 0
  # shellcheck disable=SC1090
  . "$CONF"
  for c in buzup_backend_staging goup_backend_staging cashup_backend_staging; do
    docker exec "$c" python -c "
from apps.sms.services.sender import send_sms
for n in '${NUMEROS:-}'.split(','):
    n = n.strip()
    if n: send_sms(n, '''$texto''', purpose='OPS_BACKUP')
" 2>/dev/null && return 0
  done
}

echo "== $(date '+%F %T') — a enviar backups para $DESTINO =="

# --delete NAO: o destino guarda mais historico do que a origem, que so tem
# 14 dias. Se um apagamento acidental aqui apagasse tambem la, o destino
# deixava de proteger contra apagamentos.
rsync -az --partial --stats \
  -e "ssh -p $PORTA -i $CHAVE -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30" \
  --include='*/' --include='*.sql.gz' --include='*.dump' --exclude='*' \
  "$ORIGEM/" "$DESTINO/"
codigo=$?

if [ $codigo -ne 0 ]; then
  echo "FALHOU (rsync $codigo)"
  avisar "BuzUp/ops: backup externo FALHOU (rsync $codigo) em $(hostname)."
  exit $codigo
fi

# Enviar sem conferir e ficar a pensar que se esta protegido. Compara-se o
# dump de HOJE de cada produto, byte a byte, pelo sha256.
echo "== a conferir o que chegou =="
falhas=0
for produto in buzup payup cashup fena; do
  ultimo=$(ls -1t "$ORIGEM/$produto"/*.sql.gz 2>/dev/null | head -1) || continue
  [ -n "$ultimo" ] || continue
  nome=$(basename "$ultimo")
  aqui=$(sha256sum "$ultimo" | cut -d' ' -f1)
  la=$(ssh -p "$PORTA" -i "$CHAVE" -o StrictHostKeyChecking=accept-new \
        "${DESTINO%%:*}" "sha256sum '${DESTINO#*:}/$produto/$nome'" 2>/dev/null | cut -d' ' -f1)
  if [ "$aqui" = "$la" ] && [ -n "$la" ]; then
    echo "   ok  $produto/$nome"
  else
    echo "   MAU $produto/$nome (aqui $aqui / la ${la:-nada})"
    falhas=$((falhas + 1))
  fi
done

if [ $falhas -gt 0 ]; then
  avisar "BuzUp/ops: $falhas backup(s) chegaram diferentes ao destino externo."
  exit 1
fi

echo "== $(date '+%F %T') — tudo conferido =="
