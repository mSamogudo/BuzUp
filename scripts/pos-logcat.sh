#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# shellcheck disable=SC1091
. "$ROOT_DIR/scripts/pos-common.sh"

: "${BUZUP_POS_APPLICATION_ID:=mz.coupdigital.pos_app}"

ensure_adb

adb_serial=$(first_adb_device_serial)
if ! adb_device_ready "$adb_serial"; then
  echo "[pos] nenhum device adb pronto para leitura de logs" >&2
  exit 1
fi

pid=$(adb -s "$adb_serial" shell pidof -s "$BUZUP_POS_APPLICATION_ID" 2>/dev/null | tr -d '\r')

if [ -n "$pid" ]; then
  echo "[pos] a seguir logs do processo $BUZUP_POS_APPLICATION_ID (pid $pid) no device $adb_serial"
  exec adb -s "$adb_serial" logcat --pid="$pid" -v color BUZUP_POS:I flutter:I "*:S"
fi

echo "[pos] app sem pid activo; a seguir logs globais filtrados por BUZUP_POS e Flutter"
exec adb -s "$adb_serial" logcat -v color BUZUP_POS:I flutter:I "*:S"
