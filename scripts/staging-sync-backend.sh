#!/usr/bin/env bash
#
# Sync the local backend code into the staging container via the bind mount
# configured in `docker-compose.staging.yml`. Restarts gunicorn so Django
# picks up the changes.
#
# Usage:
#   bash scripts/staging-sync-backend.sh                  # rsync + restart
#   bash scripts/staging-sync-backend.sh --no-restart     # rsync only
#   bash scripts/staging-sync-backend.sh --migrate <app>  # rsync + migrate
#
# Why this script: before the bind mount, every backend code change required
# a sequence of `tar | scp | docker cp | docker restart`. The bind mount
# (./backend/apps, ./backend/config, ./backend/manage.py → /app/...) lets a
# plain rsync push code; we only need to restart the container so gunicorn
# re-imports the modules. No image rebuild needed for day-to-day work.
#
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_HOST="${BUZUP_STAGING_HOST:-95.216.50.19}"
SERVER_USER="${BUZUP_STAGING_USER:-root}"
SERVER_PASS="${BUZUP_STAGING_PASS:-zPbA95HTXf48dseEpnag}"
REMOTE_ROOT="/opt/staging/buzup/app/backend"
CONTAINER="buzup_backend_staging"

NO_RESTART=false
MIGRATE_APP=""
ALSO_FRONTEND=false
ONLY_FRONTEND=false

while [ $# -gt 0 ]; do
    case "$1" in
        --no-restart) NO_RESTART=true ;;
        --frontend) ALSO_FRONTEND=true ;;
        --only-frontend) ONLY_FRONTEND=true; ALSO_FRONTEND=true ;;
        --migrate)
            MIGRATE_APP="${2:-}"
            shift
            ;;
        --help|-h)
            grep -E '^#( |$)' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "[staging-sync] unknown flag: $1" >&2
            exit 2
            ;;
    esac
    shift
done

if ! command -v sshpass >/dev/null 2>&1; then
    echo "[staging-sync] sshpass not installed (brew install hudochenkov/sshpass/sshpass)" >&2
    exit 3
fi

rsync_to_server() {
    local src="$1"
    local dst="$2"
    sshpass -p "$SERVER_PASS" rsync -avz \
        --no-times --no-perms \
        --delete \
        "$src" "$SERVER_USER@$SERVER_HOST:$dst" >/dev/null
}

if [ "$ONLY_FRONTEND" = false ]; then
    echo "[staging-sync] rsync apps/ → $REMOTE_ROOT/apps/"
    rsync_to_server "$PROJECT_ROOT/backend/apps/" "$REMOTE_ROOT/apps/"

    echo "[staging-sync] rsync config/ → $REMOTE_ROOT/config/"
    rsync_to_server "$PROJECT_ROOT/backend/config/" "$REMOTE_ROOT/config/"

    echo "[staging-sync] rsync manage.py + requirements.txt"
    sshpass -p "$SERVER_PASS" rsync -avz --no-times --no-perms \
        "$PROJECT_ROOT/backend/manage.py" \
        "$PROJECT_ROOT/backend/requirements.txt" \
        "$SERVER_USER@$SERVER_HOST:$REMOTE_ROOT/" >/dev/null
fi

if [ "$ALSO_FRONTEND" = true ]; then
    if [ ! -d "$PROJECT_ROOT/frontend/dist" ]; then
        echo "[staging-sync] building frontend (npm run build) first..."
        (cd "$PROJECT_ROOT/frontend" && npm run build >/dev/null 2>&1)
    fi
    echo "[staging-sync] rsync frontend/dist/ → /opt/staging/buzup/app/frontend/dist/"
    sshpass -p "$SERVER_PASS" rsync -avz --no-times --no-perms --delete \
        "$PROJECT_ROOT/frontend/dist/" \
        "$SERVER_USER@$SERVER_HOST:/opt/staging/buzup/app/frontend/dist/" >/dev/null
fi

if [ -n "$MIGRATE_APP" ]; then
    echo "[staging-sync] running migrate $MIGRATE_APP"
    sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no \
        "$SERVER_USER@$SERVER_HOST" \
        "docker exec $CONTAINER python manage.py migrate $MIGRATE_APP --settings=config.settings.prod 2>&1 | tail -5"
fi

if [ "$NO_RESTART" = false ]; then
    if [ "$ONLY_FRONTEND" = false ]; then
        echo "[staging-sync] restarting $CONTAINER"
        sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no \
            "$SERVER_USER@$SERVER_HOST" \
            "docker restart $CONTAINER >/dev/null && sleep 4 && docker ps --filter name=$CONTAINER --format '{{.Status}}'"
    fi
    if [ "$ALSO_FRONTEND" = true ]; then
        echo "[staging-sync] reloading nginx in buzup_frontend_staging"
        sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no \
            "$SERVER_USER@$SERVER_HOST" \
            "docker exec buzup_frontend_staging nginx -s reload 2>&1 | head -1"
    fi
fi

echo "[staging-sync] done."
