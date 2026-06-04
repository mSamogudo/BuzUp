#!/usr/bin/env sh
set -eu

. "$(dirname "$0")/mobile-common.sh"

build_mobile_apk staging
