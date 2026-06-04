#!/usr/bin/env sh
# Helpers partilhados pelos scripts pos-run-* e pos-build-apk-* do BuzUp.
# Padrao adaptado do projecto ETICKETING.
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
POS_DIR="$ROOT_DIR/pos_app"
POS_CONFIG_DIR="$POS_DIR/config"
POS_OUTPUT_DIR="$POS_DIR/build/app/outputs/flutter-apk"

ensure_flutter() {
  if ! command -v flutter >/dev/null 2>&1; then
    echo "[pos] flutter nao encontrado no PATH" >&2
    exit 1
  fi
}

ensure_adb() {
  if ! command -v adb >/dev/null 2>&1; then
    echo "[pos] adb nao encontrado no PATH" >&2
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
    cd "$POS_DIR"
    flutter devices 2>/dev/null || true
  ) | awk '
    /unsupported/ {next}
    tolower($0) ~ /android/ {found=1}
    END {exit found ? 0 : 1}
  '
}

first_flutter_supported_android_device_id() {
  (
    cd "$POS_DIR"
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

adb_current_user() {
  serial="$1"
  ensure_adb
  adb -s "$serial" shell am get-current-user 2>/dev/null | tr -d '\r'
}

adb_list_user_ids() {
  serial="$1"
  ensure_adb
  adb -s "$serial" shell pm list users 2>/dev/null |
    tr -d '\r' |
    sed -n 's/.*UserInfo{\([0-9][0-9]*\):.*/\1/p'
}

adb_package_installed_for_user() {
  serial="$1"
  user_id="$2"
  package_name="$3"
  ensure_adb
  adb -s "$serial" shell cmd package list packages --user "$user_id" "$package_name" 2>/dev/null |
    tr -d '\r' |
    grep -Fx "package:$package_name" >/dev/null 2>&1
}

repair_android_package_user_state() {
  serial="$1"
  package_name="$2"
  ensure_adb
  [ -n "$serial" ] || return 0
  [ -n "$package_name" ] || return 0

  current_user=$(adb_current_user "$serial")
  [ -n "$current_user" ] || return 0

  if adb_package_installed_for_user "$serial" "$current_user" "$package_name"; then
    return 0
  fi

  found_other_user_install="false"
  for user_id in $(adb_list_user_ids "$serial"); do
    [ "$user_id" = "$current_user" ] && continue
    if adb_package_installed_for_user "$serial" "$user_id" "$package_name"; then
      found_other_user_install="true"
      break
    fi
  done

  if [ "$found_other_user_install" = "true" ]; then
    echo "[pos] package $package_name encontrado noutros utilizadores Android mas nao no utilizador actual ($current_user); a limpar estado do package manager"
    adb -s "$serial" uninstall "$package_name" >/dev/null 2>&1 || true
  fi
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
        echo "[pos] adb reverse activo: device tcp:$api_port -> host tcp:$api_port"
      else
        echo "[pos] aviso: nao foi possivel activar adb reverse para tcp:$api_port; no device fisico use a rede/IP do backend ou reconecte o adb" >&2
      fi
      ;;
  esac
}

load_profile_config() {
  profile="$1"
  config_file="$POS_CONFIG_DIR/$profile.env"

  if [ -f "$config_file" ]; then
    # shellcheck disable=SC1090
    . "$config_file"
  fi

  if [ "$profile" = "dev" ]; then
    : "${BUZUP_API_BASE_URL:=http://127.0.0.1:3008}"
    : "${POS_FLUTTER_DEVICE:=auto}"
    : "${POS_WEB_HOST:=127.0.0.1}"
    : "${POS_WEB_PORT:=3010}"
    : "${POS_BUILD_MODE:=debug}"
    : "${BUZUP_POS_APPLICATION_ID:=mz.coupdigital.pos_app.dev}"
  elif [ "$profile" = "staging" ]; then
    : "${BUZUP_API_BASE_URL:=https://buzup.updigital.co.mz}"
    : "${POS_FLUTTER_DEVICE:=android}"
    : "${POS_WEB_HOST:=127.0.0.1}"
    : "${POS_WEB_PORT:=3011}"
    : "${POS_BUILD_MODE:=release}"
    : "${POS_SPLIT_PER_ABI:=true}"
    : "${POS_RELEASE_ABI:=armeabi-v7a}"
    : "${BUZUP_POS_APPLICATION_ID:=mz.coupdigital.pos_app}"
  else
    : "${POS_FLUTTER_DEVICE:=android}"
    : "${POS_WEB_HOST:=127.0.0.1}"
    : "${POS_WEB_PORT:=3012}"
    : "${POS_BUILD_MODE:=release}"
    : "${POS_SPLIT_PER_ABI:=true}"
    : "${POS_RELEASE_ABI:=armeabi-v7a}"
    : "${BUZUP_POS_APPLICATION_ID:=mz.coupdigital.pos_app}"
  fi

  if [ -z "${BUZUP_API_BASE_URL:-}" ]; then
    echo "[pos] defina BUZUP_API_BASE_URL em $config_file ou no ambiente" >&2
    exit 1
  fi

  if [ "$profile" = "prod" ] && [ "$BUZUP_API_BASE_URL" = "https://api.example.com" ]; then
    echo "[pos] BUZUP_API_BASE_URL ainda esta no placeholder de producao" >&2
    exit 1
  fi

  if [ "$profile" = "prod" ]; then
    api_host=$(extract_url_host "$BUZUP_API_BASE_URL")
    case "$api_host" in
      127.0.0.1|localhost)
        echo "[pos] BUZUP_API_BASE_URL de producao nao pode apontar para $api_host" >&2
        exit 1
        ;;
    esac
  fi
}

ensure_flutter_dependencies() {
  ensure_flutter
  (
    cd "$POS_DIR"
    flutter pub get
  )
}

assert_release_signing_configured() {
  key_properties_file="$POS_DIR/android/key.properties"
  if [ -f "$key_properties_file" ]; then
    return 0
  fi

  if [ -n "${BUZUP_POS_STORE_FILE:-}" ] &&
    [ -n "${BUZUP_POS_STORE_PASSWORD:-}" ] &&
    [ -n "${BUZUP_POS_KEY_ALIAS:-}" ] &&
    [ -n "${BUZUP_POS_KEY_PASSWORD:-}" ]; then
    return 0
  fi

  # Para staging/release nao bloqueamos: assinatura debug e aceitavel em terreno
  if [ "${BUZUP_REQUIRE_SIGNING:-false}" = "true" ]; then
    echo "[pos] assinatura release nao configurada" >&2
    echo "[pos] use pos_app/android/key.properties baseado em key.properties.example" >&2
    echo "[pos] ou exporte BUZUP_POS_STORE_FILE, BUZUP_POS_STORE_PASSWORD, BUZUP_POS_KEY_ALIAS, BUZUP_POS_KEY_PASSWORD" >&2
    exit 1
  fi
  return 0
}

flutter_build_apk_internal() {
  profile="$1"

  if [ "$profile" = "prod" ] || [ "$profile" = "staging" ]; then
    build_mode_flag="--release"
    split_per_abi_flag=""
    if [ "${POS_SPLIT_PER_ABI:-true}" = "true" ]; then
      split_per_abi_flag="--split-per-abi"
    fi
  else
    build_mode_flag="--debug"
    split_per_abi_flag=""
  fi

  (
    cd "$POS_DIR"
    flutter build apk "$build_mode_flag" $split_per_abi_flag \
      --dart-define=BUZUP_API_BASE="$BUZUP_API_BASE_URL"
  )
}

copy_named_apk() {
  profile="$1"
  mkdir -p "$POS_OUTPUT_DIR"

  if [ "$profile" = "prod" ] || [ "$profile" = "staging" ]; then
    if [ "${POS_SPLIT_PER_ABI:-true}" = "true" ]; then
      selected_abi="${POS_RELEASE_ABI:-armeabi-v7a}"
      source_apk="$POS_OUTPUT_DIR/app-$selected_abi-release.apk"
      output_apk="$POS_OUTPUT_DIR/buzup-pos-$profile-$selected_abi-release.apk"
      if [ ! -f "$source_apk" ]; then
        echo "[pos] APK para ABI $selected_abi nao encontrada em $source_apk" >&2
        echo "[pos] defina POS_RELEASE_ABI para uma das ABIs geradas ou POS_SPLIT_PER_ABI=false para APK universal" >&2
        ls -1 "$POS_OUTPUT_DIR"/app-*-release.apk 2>/dev/null >&2 || true
        exit 1
      fi
    else
      source_apk="$POS_OUTPUT_DIR/app-release.apk"
      output_apk="$POS_OUTPUT_DIR/buzup-pos-$profile-release.apk"
    fi
    cp "$source_apk" "$output_apk"
    printf '%s\n' "$output_apk"
  else
    cp "$POS_OUTPUT_DIR/app-debug.apk" "$POS_OUTPUT_DIR/buzup-pos-dev-debug.apk"
    printf '%s\n' "$POS_OUTPUT_DIR/buzup-pos-dev-debug.apk"
  fi
}

publish_pos_release_artifacts() {
  profile="$1"
  apk_path="$2"
  [ "$profile" = "prod" ] || return 0
  [ -f "$apk_path" ] || return 0

  release_dir="$ROOT_DIR/backend/media/pos-app"
  release_apk="$release_dir/buzup-pos.apk"
  release_manifest="$release_dir/release.json"
  pubspec_version=$(sed -n 's/^version:[[:space:]]*//p' "$POS_DIR/pubspec.yaml" | sed -n '1p')
  version_name="${BUZUP_POS_VERSION_NAME:-${pubspec_version%%+*}}"
  version_code="${BUZUP_POS_VERSION_CODE:-${pubspec_version#*+}}"
  if [ "$version_code" = "$pubspec_version" ] || [ -z "$version_code" ]; then
    version_code="1"
  fi
  release_abi="${POS_RELEASE_ABI:-universal}"
  if [ "${POS_SPLIT_PER_ABI:-true}" != "true" ]; then
    release_abi="universal"
  fi
  release_notes="${BUZUP_POS_RELEASE_NOTES:-Nova versao BuzUp POS disponivel.}"

  mkdir -p "$release_dir"
  cp "$apk_path" "$release_apk"
  python3 - "$release_manifest" "$version_name" "$version_code" "$release_notes" "$release_abi" <<'PY'
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
payload = {
    "version_name": sys.argv[2],
    "version_code": int(sys.argv[3]),
    "filename": "buzup-pos.apk",
    "release_notes": sys.argv[4],
    "abi": sys.argv[5],
    "required": False,
}
manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
PY
  echo "[pos] release publicado localmente: $release_apk"

  if command -v docker >/dev/null 2>&1; then
    compose_file="${COMPOSE_FILE:-docker-compose.prod.yml}"
    env_file="${ENV_FILE:-backend/.env.prod}"
    compose_project_name="${COMPOSE_PROJECT_NAME:-buzup}"
    backend_container=$(docker compose -p "$compose_project_name" --env-file "$env_file" -f "$compose_file" ps -q backend 2>/dev/null || true)
    if [ -n "$backend_container" ]; then
      docker compose -p "$compose_project_name" --env-file "$env_file" -f "$compose_file" exec -T backend mkdir -p /app/media/pos-app >/dev/null 2>&1 || true
      docker compose -p "$compose_project_name" --env-file "$env_file" -f "$compose_file" cp "$release_apk" backend:/app/media/pos-app/buzup-pos.apk >/dev/null 2>&1 || true
      docker compose -p "$compose_project_name" --env-file "$env_file" -f "$compose_file" cp "$release_manifest" backend:/app/media/pos-app/release.json >/dev/null 2>&1 || true
      echo "[pos] release sincronizado com o backend de producao quando disponivel"
    fi
  fi
}

adb_install_and_launch() {
  profile="$1"
  ensure_flutter_dependencies
  ensure_adb

  adb_serial=$(first_adb_device_serial)
  if ! adb_device_ready "$adb_serial"; then
    echo "[pos] nenhum device adb pronto para instalar a app" >&2
    exit 1
  fi

  if [ "$profile" = "prod" ]; then
    assert_release_signing_configured
  fi

  repair_android_package_user_state "$adb_serial" "$BUZUP_POS_APPLICATION_ID"
  prepare_local_api_reverse "$adb_serial"
  flutter_build_apk_internal "$profile"
  apk_path=$(copy_named_apk "$profile")
  remote_apk="/data/local/tmp/$(basename "$apk_path")"
  adb -s "$adb_serial" push "$apk_path" "$remote_apk" >/dev/null
  adb -s "$adb_serial" shell pm install -r "$remote_apk"
  adb -s "$adb_serial" shell rm -f "$remote_apk" >/dev/null 2>&1 || true
  adb -s "$adb_serial" shell am start -n "$BUZUP_POS_APPLICATION_ID/mz.coupdigital.pos_app.MainActivity" || \
    adb -s "$adb_serial" shell monkey -p "$BUZUP_POS_APPLICATION_ID" -c android.intent.category.LAUNCHER 1 >/dev/null

  echo "[pos] app instalada e aberta no device adb ($adb_serial)"
}

run_pos_app() {
  profile="$1"
  requested_device="${2:-}"
  load_profile_config "$profile"
  ensure_flutter_dependencies

  run_mode_flag="--${POS_BUILD_MODE}"
  device="${requested_device:-$POS_FLUTTER_DEVICE}"

  if [ "$device" = "auto" ]; then
    supported_android_id=$(first_flutter_supported_android_device_id)
    adb_serial=$(first_adb_device_serial)
    if [ -n "$supported_android_id" ]; then
      device="$supported_android_id"
    elif adb_device_ready "$adb_serial"; then
      device="android"
    else
      device="web-server"
    fi
  fi

  if [ "$device" = "android" ]; then
    supported_android_id=$(first_flutter_supported_android_device_id)
    if [ -n "$supported_android_id" ]; then
      echo "[pos] a usar device flutter: $supported_android_id"
      device="$supported_android_id"
    fi
  fi

  if [ "$device" = "android" ] && ! flutter_has_supported_android_device; then
    echo "[pos] flutter nao reconheceu um device android suportado; a usar fallback adb install + launch"
    adb_install_and_launch "$profile"
    return 0
  fi

  if [ "$device" = "web-server" ]; then
    selected_port=$(find_available_port "$POS_WEB_PORT")
    if [ "$selected_port" != "$POS_WEB_PORT" ]; then
      echo "[pos] porta $POS_WEB_PORT ocupada; a usar $selected_port"
    fi
    exec sh -c "
      cd \"$POS_DIR\" &&
      flutter run \"$run_mode_flag\" \
        -d web-server \
        --web-hostname \"$POS_WEB_HOST\" \
        --web-port \"$selected_port\" \
        --dart-define=BUZUP_API_BASE=\"$BUZUP_API_BASE_URL\"
    "
  fi

  adb_serial="$device"
  if ! adb_device_ready "$adb_serial"; then
    adb_serial=$(first_adb_device_serial)
  fi
  if adb_device_ready "$adb_serial"; then
    repair_android_package_user_state "$adb_serial" "$BUZUP_POS_APPLICATION_ID"
    prepare_local_api_reverse "$adb_serial"
  fi

  exec sh -c "
    cd \"$POS_DIR\" &&
    flutter run \"$run_mode_flag\" \
      -d \"$device\" \
      --dart-define=BUZUP_API_BASE=\"$BUZUP_API_BASE_URL\"
  "
}

build_pos_apk() {
  profile="$1"
  load_profile_config "$profile"
  ensure_flutter_dependencies

  if [ "$profile" = "prod" ]; then
    assert_release_signing_configured
  fi

  flutter_build_apk_internal "$profile"
  apk_path=$(copy_named_apk "$profile")
  output_name=$(basename "$apk_path")
  publish_pos_release_artifacts "$profile" "$apk_path"

  echo "[pos] apk gerado: $POS_OUTPUT_DIR/$output_name"
}
