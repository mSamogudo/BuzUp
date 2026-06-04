#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
docker compose -f docker-compose.dev.yml down "$@"
