#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd "$SCRIPT_DIR/.." && pwd)

cd "$REPO_ROOT"

: "${PROJECT_LABEL:=buzup}"
: "${COMPOSE_FILE:=docker-compose.prod.yml}"
: "${ENV_FILE:=backend/.env.prod}"
: "${BACKEND_ENV_FILE:=$ENV_FILE}"
: "${SHARED_WEB_NETWORK:=shared_web}"
: "${INTERNAL_NETWORK:=buzup_internal}"
: "${COMPOSE_PROJECT_NAME:=buzup}"
: "${VOLUMES:=buzup_postgres_prod_data buzup_static_data buzup_media_data}"
: "${SERVICES:=db redis backend frontend gateway}"

if [ ! -f "$ENV_FILE" ]; then
  echo "[$PROJECT_LABEL] missing env file: $ENV_FILE" >&2
  echo "[$PROJECT_LABEL] copy the matching .env example and fill production secrets before deploying" >&2
  exit 1
fi

export BACKEND_ENV_FILE

compose() {
  docker compose -p "$COMPOSE_PROJECT_NAME" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

echo "[$PROJECT_LABEL] ensuring Docker networks"
docker network inspect "$SHARED_WEB_NETWORK" >/dev/null 2>&1 || docker network create "$SHARED_WEB_NETWORK" >/dev/null
docker network inspect "$INTERNAL_NETWORK" >/dev/null 2>&1 || docker network create "$INTERNAL_NETWORK" >/dev/null

echo "[$PROJECT_LABEL] ensuring Docker volumes"
for volume in $VOLUMES; do
  docker volume inspect "$volume" >/dev/null 2>&1 || docker volume create "$volume" >/dev/null
done

echo "[$PROJECT_LABEL] validating compose configuration"
compose config >/dev/null

echo "[$PROJECT_LABEL] building and starting services"
compose up --build -d $SERVICES

echo "[$PROJECT_LABEL] applying database migrations"
compose exec -T backend python manage.py migrate --noinput --settings=config.settings.prod

echo "[$PROJECT_LABEL] running backend production checks"
compose exec -T backend python manage.py check --deploy --settings=config.settings.prod
compose exec -T backend python manage.py makemigrations --check --dry-run

echo "[$PROJECT_LABEL] checking internal API health"
attempt=1
until compose exec -T backend python - <<'PY'
import sys
import urllib.request

request = urllib.request.Request(
    "http://127.0.0.1:8000/api/health/",
    headers={"X-Forwarded-Proto": "https"},
)
response = urllib.request.urlopen(request, timeout=8)
sys.exit(0 if response.status == 200 else 1)
PY
do
  if [ "$attempt" -ge 60 ]; then
    echo "[$PROJECT_LABEL] internal API healthcheck failed after 120 seconds" >&2
    exit 1
  fi
  attempt=$((attempt + 1))
  sleep 2
done

echo "[$PROJECT_LABEL] checking shared gateway health"
attempt=1
until compose exec -T gateway wget -q -O /dev/null http://127.0.0.1/healthz
do
  if [ "$attempt" -ge 60 ]; then
    echo "[$PROJECT_LABEL] gateway healthcheck failed after 120 seconds" >&2
    exit 1
  fi
  attempt=$((attempt + 1))
  sleep 2
done

echo "[$PROJECT_LABEL] deployment completed successfully"
