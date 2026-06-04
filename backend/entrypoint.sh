#!/bin/sh
set -eu

log() {
  printf '%s %s\n' "[backend-entrypoint]" "$*"
}

is_true() {
  value="$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')"
  case "$value" in
    1|true|yes|on)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

run_manage() {
  log "python manage.py $*"
  python manage.py "$@"
}

wait_for_database() {
  if ! is_true "${WAIT_FOR_DB:-true}"; then
    return 0
  fi

  host="${POSTGRES_HOST:-db}"
  port="${POSTGRES_PORT:-5432}"
  timeout="${WAIT_FOR_DB_TIMEOUT:-60}"
  elapsed=0

  log "Waiting for PostgreSQL at ${host}:${port}"
  until nc -z "$host" "$port" >/dev/null 2>&1; do
    elapsed=$((elapsed + 1))
    if [ "$elapsed" -ge "$timeout" ]; then
      log "Timed out after ${timeout}s waiting for PostgreSQL."
      exit 1
    fi
    sleep 1
  done

  log "PostgreSQL is reachable."
}

main() {
  cd /app
  wait_for_database

  if is_true "${AUTO_MIGRATE:-true}"; then
    run_manage migrate --noinput
  fi

  if is_true "${AUTO_COLLECTSTATIC:-false}"; then
    run_manage collectstatic --noinput
  fi

  log "Starting application command: $*"
  exec "$@"
}

main "$@"