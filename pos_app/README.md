# BuzUp POS — Flutter app para agentes

App Flutter para terminais POS SUNMI/Urovo. Comunica com o backend BuzUp via endpoints `/api/agent/*`.

## Requisitos
- Flutter 3.11+
- Android SDK + NDK
- Java 17+

## Correr a app
```bash
./scripts/run.sh local       # backend em http://10.0.2.2:3008
./scripts/run.sh staging     # https://updigital.co.mz (default)
./scripts/run.sh prod        # https://buzup.co.mz
```

Para escolher dispositivo: `./scripts/run.sh staging -d emulator-5554`

## Gerar APK
```bash
./scripts/build.sh staging         # APK release contra staging
./scripts/build.sh prod            # APK release contra producao
./scripts/build.sh staging --debug # APK debug
```
APKs em `build/app/outputs/flutter-apk/` com sufixo timestamp.

## Instalar via USB
```bash
adb devices
./scripts/install.sh staging              # build + install
./scripts/install.sh staging --no-build    # so install
```

## Estrutura
```
lib/
├── app.dart                   # router + theme
├── main.dart
├── core/
│   ├── config.dart            # baseUrl injectado via --dart-define
│   ├── storage.dart           # secure storage (Android Keystore)
│   ├── api_client.dart        # Dio + JWT interceptor + 401 handler
│   ├── agent_api.dart         # endpoints /api/agent/*
│   ├── device_info.dart       # detecta SUNMI/Urovo + serial
│   └── providers.dart         # Riverpod providers
└── features/
    ├── auth/login_screen.dart
    ├── home/home_screen.dart            # registo auto + heartbeat 60s
    ├── sale/sale_flow_screen.dart       # trip→stops→fare→tel→pagamento→QR
    ├── verify/verify_screen.dart        # QR scanner + mark-used
    ├── history/history_screen.dart
    └── summary/summary_screen.dart
```

## Configuração de backend
Base URL injectada em compile time via `--dart-define=BUZUP_API_BASE=...`.
Override: `BUZUP_API_BASE=https://x.mz ./scripts/run.sh staging`.

## Fluxo de venda
1. Login agente (username/password)
2. Registo automático do device (serial via device_info_plus)
3. Heartbeat 60s com lat/lng
4. Listar viagens em circulação
5. Origem/destino → backend calcula tarifa
6. Telefone (9 dígitos) + quantidade (1-10)
7. Solicitação M-Pesa/E-Mola
8. Polling 3s do estado (timeout 3 min)
9. Bilhetes emitidos APENAS após confirmed
10. QR scanner para validar bilhetes + mark-used

## Regras de segurança
- Backend sempre calcula tarifa
- Bilhete só após PaymentIntent confirmed
- Telefones mascarados (***1234)
- Tokens em flutter_secure_storage
- 401 → clear tokens + redirect /login
