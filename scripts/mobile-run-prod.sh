#!/usr/bin/env sh
set -eu

. "$(dirname "$0")/mobile-common.sh"

run_mobile_app prod "${1:-}"
