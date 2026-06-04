#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)

export PROJECT_LABEL="${PROJECT_LABEL:-buzup-prod}"
export COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
export ENV_FILE="${ENV_FILE:-backend/.env.prod}"
export BACKEND_ENV_FILE="${BACKEND_ENV_FILE:-$ENV_FILE}"
export SHARED_WEB_NETWORK="${SHARED_WEB_NETWORK:-shared_web}"
export INTERNAL_NETWORK="${INTERNAL_NETWORK:-buzup_internal}"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-buzup-prod}"
export VOLUMES="${VOLUMES:-buzup_postgres_prod_data buzup_static_data buzup_media_data}"
export SERVICES="${SERVICES:-db redis backend frontend gateway}"

exec "$SCRIPT_DIR/deploy_shared.sh"
