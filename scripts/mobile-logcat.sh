#!/usr/bin/env sh
# Segue logs do app passageiro BuzUp via adb logcat, filtrando pelo tag
# BuzUpMobile (developer.log) + flutter. Usar: ./scripts/mobile-logcat.sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# shellcheck disable=SC1091
. "$ROOT_DIR/scripts/mobile-common.sh"

: "${BUZUP_MOBILE_APPLICATION_ID:=mz.coupdigital.buzup_mobile}"

ensure_adb

adb_serial=$(first_adb_device_serial)
if ! adb_device_ready "$adb_serial"; then
  echo "[mobile] nenhum device adb pronto para leitura de logs" >&2
  exit 1
fi

pid=$(adb -s "$adb_serial" shell pidof -s "$BUZUP_MOBILE_APPLICATION_ID" 2>/dev/null | tr -d '\r')

if [ -n "$pid" ]; then
  echo "[mobile] a seguir logs do processo $BUZUP_MOBILE_APPLICATION_ID (pid $pid) no device $adb_serial"
  exec adb -s "$adb_serial" logcat --pid="$pid" -v color BuzUpMobile:V flutter:I "*:S"
fi

echo "[mobile] app sem pid activo; a seguir logs globais filtrados por BuzUpMobile e Flutter"
exec adb -s "$adb_serial" logcat -v color BuzUpMobile:V flutter:I "*:S"
