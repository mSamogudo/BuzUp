#!/usr/bin/env sh
set -eu

. "$(dirname "$0")/pos-common.sh"

run_pos_app staging "${1:-}"
