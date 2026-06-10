#!/usr/bin/env sh
# Helpers partilhados pelos scripts mobile-run-* / mobile-build-apk-* do app
# passageiro BuzUp. Espelha pos-common.sh mas usa o diretorio mobile_app/.
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MOBILE_DIR="$ROOT_DIR/mobile_app"
MOBILE_CONFIG_DIR="$MOBILE_DIR/config"
MOBILE_OUTPUT_DIR="$MOBILE_DIR/build/app/outputs/flutter-apk"

ensure_flutter() {
  if ! command -v flutter >/dev/null 2>&1; then
    echo "[mobile] flutter nao encontrado no PATH" >&2
    exit 1
  fi
}

ensure_adb() {
  if ! command -v adb >/dev/null 2>&1; then
    echo "[mobile] adb nao encontrado no PATH" >&2
    exit 1
  fi
}

port_in_use() {
  port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

find_available_port() {
  port="$1"
  while port_in_use "$port"; do
    port=$((port + 1))
  done
  printf '%s\n' "$port"
}

extract_url_host() {
  printf '%s\n' "$1" | sed -E 's#^[a-zA-Z]+://([^/:]+).*$#\1#'
}

extract_url_port() {
  port=$(printf '%s\n' "$1" | sed -nE 's#^[a-zA-Z]+://[^/:]+:([0-9]+).*$#\1#p')
  if [ -n "$port" ]; then
    printf '%s\n' "$port"
  else
    printf '80\n'
  fi
}

flutter_has_supported_android_device() {
  (
    cd "$MOBILE_DIR"
    flutter devices 2>/dev/null || true
  ) | awk '
    /unsupported/ {next}
    tolower($0) ~ /android/ {found=1}
    END {exit found ? 0 : 1}
  '
}

first_flutter_supported_android_device_id() {
  (
    cd "$MOBILE_DIR"
    flutter devices 2>/dev/null || true
  ) | awk -F '•' '
    /unsupported/ {next}
    tolower($0) ~ /android/ {
      device=$2
      gsub(/^[ \t]+|[ \t]+$/, "", device)
      if (length(device) > 0) {
        if (device !~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+$/ && preferred == "") {
          preferred = device
        }
        if (fallback == "") {
          fallback = device
        }
      }
    }
    END {
      if (preferred != "") {
        print preferred
      } else if (fallback != "") {
        print fallback
      }
    }
  '
}

first_flutter_ios_device_id() {
  (
    cd "$MOBILE_DIR"
    flutter devices 2>/dev/null || true
  ) | awk -F '•' '
    /unsupported/ {next}
    tolower($0) ~ /ios/ || tolower($0) ~ /iphone/ || tolower($0) ~ /ipad/ || tolower($0) ~ /simulator/ {
      device=$2
      gsub(/^[ \t]+|[ \t]+$/, "", device)
      if (length(device) > 0 && fallback == "") {
        fallback = device
      }
    }
    END {
      if (fallback != "") print fallback
    }
  '
}

first_adb_device_serial() {
  ensure_adb
  adb devices | awk '
    NR == 1 {next}
    $2 == "device" {
      serial = $1
      if (serial !~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+$/ && preferred == "") {
        preferred = serial
      }
      if (fallback == "") {
        fallback = serial
      }
    }
    END {
      if (preferred != "") {
        print preferred
      } else if (fallback != "") {
        print fallback
      }
    }
  '
}

adb_device_ready() {
  serial="$1"
  ensure_adb
  [ -n "$serial" ] || return 1
  adb -s "$serial" get-state >/dev/null 2>&1 || return 1
  adb -s "$serial" shell getprop ro.serialno >/dev/null 2>&1
}

prepare_local_api_reverse() {
  serial="${1:-}"
  api_host=$(extract_url_host "$BUZUP_API_BASE_URL")
  api_port=$(extract_url_port "$BUZUP_API_BASE_URL")

  case "$api_host" in
    127.0.0.1|localhost)
      reverse_ok="false"
      if [ -n "$serial" ]; then
        if adb -s "$serial" reverse "tcp:$api_port" "tcp:$api_port" >/dev/null 2>&1; then
          reverse_ok="true"
        fi
      else
        if adb reverse "tcp:$api_port" "tcp:$api_port" >/dev/null 2>&1; then
          reverse_ok="true"
        fi
      fi
      if [ "$reverse_ok" = "true" ]; then
        echo "[mobile] adb reverse activo: device tcp:$api_port -> host tcp:$api_port"
      else
        echo "[mobile] aviso: nao foi possivel activar adb reverse para tcp:$api_port; no device fisico use a rede/IP do backend ou reconecte o adb" >&2
      fi
      ;;
  esac
}

load_profile_config() {
  profile="$1"
  config_file="$MOBILE_CONFIG_DIR/$profile.env"

  if [ -f "$config_file" ]; then
    # shellcheck disable=SC1090
    . "$config_file"
  fi

  if [ "$profile" = "dev" ]; then
    : "${BUZUP_API_BASE_URL:=http://127.0.0.1:3008}"
    : "${MOBILE_FLUTTER_DEVICE:=auto}"
    : "${MOBILE_WEB_HOST:=127.0.0.1}"
    : "${MOBILE_WEB_PORT:=3015}"
    : "${MOBILE_BUILD_MODE:=debug}"
    : "${BUZUP_MOBILE_APPLICATION_ID:=mz.coupdigital.buzup_mobile}"
  elif [ "$profile" = "staging" ]; then
    : "${BUZUP_API_BASE_URL:=https://buzup-test.updigital.co.mz}"
    : "${MOBILE_FLUTTER_DEVICE:=auto}"
    : "${MOBILE_WEB_HOST:=127.0.0.1}"
    : "${MOBILE_WEB_PORT:=3016}"
    : "${MOBILE_BUILD_MODE:=release}"
    : "${MOBILE_SPLIT_PER_ABI:=true}"
    : "${MOBILE_RELEASE_ABI:=armeabi-v7a}"
    : "${BUZUP_MOBILE_APPLICATION_ID:=mz.coupdigital.buzup_mobile}"
  else
    : "${BUZUP_API_BASE_URL:=https://buzup.updigital.co.mz}"
    : "${MOBILE_FLUTTER_DEVICE:=auto}"
    : "${MOBILE_WEB_HOST:=127.0.0.1}"
    : "${MOBILE_WEB_PORT:=3017}"
    : "${MOBILE_BUILD_MODE:=release}"
    : "${MOBILE_SPLIT_PER_ABI:=true}"
    : "${MOBILE_RELEASE_ABI:=armeabi-v7a}"
    : "${BUZUP_MOBILE_APPLICATION_ID:=mz.coupdigital.buzup_mobile}"
  fi

  if [ -z "${BUZUP_API_BASE_URL:-}" ]; then
    echo "[mobile] defina BUZUP_API_BASE_URL em $config_file ou no ambiente" >&2
    exit 1
  fi

  # Fail-safe de ambiente: cada perfil de build TEM de apontar para o seu
  # proprio ambiente. Impede que um build prod saia a apontar para o dominio
  # de TESTE (ou um build staging para o dominio de PRODUCAO) por engano.
  api_host=$(extract_url_host "$BUZUP_API_BASE_URL")
  if [ "$profile" = "prod" ]; then
    case "$api_host" in
      127.0.0.1|localhost|buzup-test.updigital.co.mz)
        echo "[mobile] build PROD nao pode apontar para $api_host (esperado: buzup.updigital.co.mz)" >&2
        exit 1
        ;;
    esac
  elif [ "$profile" = "staging" ]; then
    case "$api_host" in
      buzup.updigital.co.mz)
        echo "[mobile] build STAGING nao pode apontar para o dominio de PRODUCAO $api_host (esperado: buzup-test.updigital.co.mz)" >&2
        exit 1
        ;;
    esac
  fi
}

ensure_flutter_dependencies() {
  ensure_flutter
  (
    cd "$MOBILE_DIR"
    flutter pub get
  )
}

flutter_build_apk_internal() {
  profile="$1"

  if [ "$profile" = "prod" ] || [ "$profile" = "staging" ]; then
    build_mode_flag="--release"
    split_per_abi_flag=""
    if [ "${MOBILE_SPLIT_PER_ABI:-true}" = "true" ]; then
      split_per_abi_flag="--split-per-abi"
    fi
  else
    build_mode_flag="--debug"
    split_per_abi_flag=""
  fi

  (
    cd "$MOBILE_DIR"
    flutter build apk "$build_mode_flag" $split_per_abi_flag \
      --dart-define=BUZUP_API_BASE="$BUZUP_API_BASE_URL"
  )
}

copy_named_apk() {
  profile="$1"
  mkdir -p "$MOBILE_OUTPUT_DIR"

  if [ "$profile" = "prod" ] || [ "$profile" = "staging" ]; then
    if [ "${MOBILE_SPLIT_PER_ABI:-true}" = "true" ]; then
      selected_abi="${MOBILE_RELEASE_ABI:-armeabi-v7a}"
      source_apk="$MOBILE_OUTPUT_DIR/app-$selected_abi-release.apk"
      output_apk="$MOBILE_OUTPUT_DIR/buzup-mobile-$profile-$selected_abi-release.apk"
      if [ ! -f "$source_apk" ]; then
        echo "[mobile] APK para ABI $selected_abi nao encontrada em $source_apk" >&2
        echo "[mobile] defina MOBILE_RELEASE_ABI para uma das ABIs geradas ou MOBILE_SPLIT_PER_ABI=false para APK universal" >&2
        ls -1 "$MOBILE_OUTPUT_DIR"/app-*-release.apk 2>/dev/null >&2 || true
        exit 1
      fi
    else
      source_apk="$MOBILE_OUTPUT_DIR/app-release.apk"
      output_apk="$MOBILE_OUTPUT_DIR/buzup-mobile-$profile-release.apk"
    fi
    cp "$source_apk" "$output_apk"
    printf '%s\n' "$output_apk"
  else
    cp "$MOBILE_OUTPUT_DIR/app-debug.apk" "$MOBILE_OUTPUT_DIR/buzup-mobile-dev-debug.apk"
    printf '%s\n' "$MOBILE_OUTPUT_DIR/buzup-mobile-dev-debug.apk"
  fi
}

adb_install_and_launch() {
  profile="$1"
  ensure_flutter_dependencies
  ensure_adb

  adb_serial=$(first_adb_device_serial)
  if ! adb_device_ready "$adb_serial"; then
    echo "[mobile] nenhum device adb pronto para instalar a app" >&2
    exit 1
  fi

  prepare_local_api_reverse "$adb_serial"
  flutter_build_apk_internal "$profile"
  apk_path=$(copy_named_apk "$profile")
  remote_apk="/data/local/tmp/$(basename "$apk_path")"
  adb -s "$adb_serial" push "$apk_path" "$remote_apk" >/dev/null
  adb -s "$adb_serial" shell pm install -r "$remote_apk"
  adb -s "$adb_serial" shell rm -f "$remote_apk" >/dev/null 2>&1 || true
  adb -s "$adb_serial" shell monkey -p "$BUZUP_MOBILE_APPLICATION_ID" -c android.intent.category.LAUNCHER 1 >/dev/null

  echo "[mobile] app instalada e aberta no device adb ($adb_serial)"
}

run_mobile_app() {
  profile="$1"
  requested_device="${2:-}"
  load_profile_config "$profile"
  ensure_flutter_dependencies

  run_mode_flag="--${MOBILE_BUILD_MODE}"
  device="${requested_device:-$MOBILE_FLUTTER_DEVICE}"

  if [ "$device" = "auto" ]; then
    supported_android_id=$(first_flutter_supported_android_device_id)
    ios_id=$(first_flutter_ios_device_id)
    adb_serial=$(first_adb_device_serial)
    if [ -n "$supported_android_id" ]; then
      device="$supported_android_id"
    elif [ -n "$ios_id" ]; then
      device="$ios_id"
    elif adb_device_ready "$adb_serial"; then
      device="android"
    else
      device="web-server"
    fi
  fi

  if [ "$device" = "android" ]; then
    supported_android_id=$(first_flutter_supported_android_device_id)
    if [ -n "$supported_android_id" ]; then
      echo "[mobile] a usar device flutter: $supported_android_id"
      device="$supported_android_id"
    fi
  fi

  if [ "$device" = "ios" ]; then
    ios_id=$(first_flutter_ios_device_id)
    if [ -n "$ios_id" ]; then
      echo "[mobile] a usar simulador/device iOS: $ios_id"
      device="$ios_id"
    fi
  fi

  if [ "$device" = "android" ] && ! flutter_has_supported_android_device; then
    echo "[mobile] flutter nao reconheceu um device android suportado; a usar fallback adb install + launch"
    adb_install_and_launch "$profile"
    return 0
  fi

  if [ "$device" = "web-server" ]; then
    selected_port=$(find_available_port "$MOBILE_WEB_PORT")
    if [ "$selected_port" != "$MOBILE_WEB_PORT" ]; then
      echo "[mobile] porta $MOBILE_WEB_PORT ocupada; a usar $selected_port"
    fi
    exec sh -c "
      cd \"$MOBILE_DIR\" &&
      flutter run \"$run_mode_flag\" \
        -d web-server \
        --web-hostname \"$MOBILE_WEB_HOST\" \
        --web-port \"$selected_port\" \
        --dart-define=BUZUP_API_BASE=\"$BUZUP_API_BASE_URL\"
    "
  fi

  adb_serial="$device"
  if adb_device_ready "$adb_serial"; then
    prepare_local_api_reverse "$adb_serial"
  fi

  exec sh -c "
    cd \"$MOBILE_DIR\" &&
    flutter run \"$run_mode_flag\" \
      -d \"$device\" \
      --dart-define=BUZUP_API_BASE=\"$BUZUP_API_BASE_URL\"
  "
}

build_mobile_apk() {
  profile="$1"
  load_profile_config "$profile"
  ensure_flutter_dependencies

  flutter_build_apk_internal "$profile"
  apk_path=$(copy_named_apk "$profile")
  output_name=$(basename "$apk_path")

  echo "[mobile] apk gerado: $MOBILE_OUTPUT_DIR/$output_name"
}
