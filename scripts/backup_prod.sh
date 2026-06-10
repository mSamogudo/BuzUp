#!/usr/bin/env sh
#
# Backup diario do BuzUp PRODUCAO: dump da base de dados + tar da media
# (que inclui as APKs/releases distribuidas aos clientes).
#
# Corre NO SERVIDOR (usa docker exec). Instalar via cron, ex.:
#   cp scripts/backup_prod.sh /opt/buzup-ops/backup_prod.sh
#   chmod +x /opt/buzup-ops/backup_prod.sh
#   printf '30 2 * * * root /opt/buzup-ops/backup_prod.sh >/dev/null 2>&1\n' \
#       > /etc/cron.d/buzup-backup
#
# Retencao: BUZUP_BACKUP_RETENTION_DAYS dias (default 14). Os ficheiros ficam
# em BUZUP_BACKUP_ROOT (default /opt/backups/buzup). Para resiliencia real,
# copiar tambem para fora do host (S3/rsync remoto) — TODO.
#
set -eu

BACKUP_ROOT="${BUZUP_BACKUP_ROOT:-/opt/backups/buzup}"
DB_CONTAINER="${BUZUP_DB_CONTAINER:-buzup_db_prod}"
MEDIA_VOLUME="${BUZUP_MEDIA_VOLUME:-buzup_media_data}"
RETENTION_DAYS="${BUZUP_BACKUP_RETENTION_DAYS:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_ROOT"
LOG="$BACKUP_ROOT/backup.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

# 1) Dump da DB (gzip). As credenciais vivem no env do proprio container.
DB_FILE="$BACKUP_ROOT/db-$STAMP.sql.gz"
log "dump DB ($DB_CONTAINER) -> $DB_FILE"
docker exec "$DB_CONTAINER" sh -c \
    'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' \
    | gzip > "$DB_FILE"
if [ ! -s "$DB_FILE" ]; then
    log "ERRO: dump da DB ficou vazio — a abortar."
    rm -f "$DB_FILE"
    exit 1
fi

# 2) Tar da media (APKs/releases, uploads).
MEDIA_SRC="/var/lib/docker/volumes/$MEDIA_VOLUME/_data"
MEDIA_FILE="$BACKUP_ROOT/media-$STAMP.tar.gz"
if [ -d "$MEDIA_SRC" ]; then
    log "tar media ($MEDIA_SRC) -> $MEDIA_FILE"
    tar -czf "$MEDIA_FILE" -C "$MEDIA_SRC" . 2>/dev/null || log "AVISO: tar da media com avisos."
else
    log "AVISO: volume de media nao encontrado em $MEDIA_SRC (saltado)."
fi

# 3) Retencao: apagar backups mais velhos que RETENTION_DAYS.
log "retencao: a apagar backups com mais de $RETENTION_DAYS dias"
find "$BACKUP_ROOT" -maxdepth 1 -name 'db-*.sql.gz' -mtime +"$RETENTION_DAYS" -delete 2>/dev/null || true
find "$BACKUP_ROOT" -maxdepth 1 -name 'media-*.tar.gz' -mtime +"$RETENTION_DAYS" -delete 2>/dev/null || true

DB_SZ="$(du -h "$DB_FILE" 2>/dev/null | cut -f1)"
MEDIA_SZ="n/a"
[ -f "$MEDIA_FILE" ] && MEDIA_SZ="$(du -h "$MEDIA_FILE" 2>/dev/null | cut -f1)"
log "OK — db=$DB_SZ media=$MEDIA_SZ"
