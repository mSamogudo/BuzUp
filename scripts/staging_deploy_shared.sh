#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)

export PROJECT_LABEL="${PROJECT_LABEL:-buzup-staging}"
export COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.staging.yml}"
export ENV_FILE="${ENV_FILE:-backend/.env.staging}"
export BACKEND_ENV_FILE="${BACKEND_ENV_FILE:-$ENV_FILE}"
export SHARED_WEB_NETWORK="${SHARED_WEB_NETWORK:-shared_web}"
export INTERNAL_NETWORK="${INTERNAL_NETWORK:-buzup_staging_internal}"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-buzup-staging}"
export VOLUMES="${VOLUMES:-buzup_postgres_staging_data buzup_static_staging_data buzup_media_staging_data}"
export SERVICES="${SERVICES:-db redis backend frontend gateway}"

exec "$SCRIPT_DIR/deploy_shared.sh"
