# BuzUp

Plataforma cashless online para gestao de mobilidade em transporte publico.

## Stack

- **Backend:** Python 3.12, Django 4.2, DRF, PostgreSQL 16, Redis 7
- **Frontend:** React 18, Vite, TypeScript, Leaflet, PWA
- **Pagamentos:** MPESA + EMOLA via Payless (Bluteki)
- **SMS:** Bluteki SMS Hub + OTP
- **PDF:** ReportLab + QRCode (bilhetes + extractos)
- **Import:** OpenPyXL (Excel .xlsx)
- **Infra:** Docker Compose, Nginx, Gunicorn

## Desenvolvimento

```sh
cp backend/.env.example backend/.env
make dev-up
docker exec buzup_backend_dev python manage.py seed_roles
docker exec buzup_backend_dev python manage.py ensure_superadmin
```

- Portal: http://localhost:3008/app (admin/admin)
- Checkout: http://localhost:3008/checkout
- API Docs: http://localhost:8008/api/docs/

## Deploy Producao

```sh
cp backend/.env.prod.example backend/.env.prod
# Editar .env.prod com credenciais reais
make prod-deploy-shared
```

## Deploy Staging

```sh
cp backend/.env.staging.example backend/.env.staging
# Editar .env.staging com credenciais reais
make staging-deploy-shared
```

Staging/QA publico temporario: `https://updigital.co.mz`. Producao em `buzup.co.mz` fica para quando o dominio estiver activo.

## Apps Django (17)

| App | Funcao |
|-----|--------|
| core | BaseModel, RBAC, permissions, import Excel, health |
| users | User, Role, UserRole, OtpChallenge, JWT + OTP auth |
| passengers | PassengerAccount |
| wallets | Wallet, WalletTransaction (ledger + SMS notify) |
| cards | Card (fisico NFC / digital QR) |
| routes | Route, Stop, RouteStop |
| fares | FareProduct, FareRule, motor de tarifas |
| packages | Package, PackageRoute, PassengerPackage |
| trips | Vehicle, Driver, Trip, RouteSchedule |
| payments | PaymentIntent, PaymentCallback |
| guest_checkouts | GuestCheckout, DigitalTravelPass, PDF bilhete |
| validations | ValidationEvent (pacote > saldo > nega) |
| devices | Device, DeviceActivationRequest, GPS tracking |
| app_releases | AppRelease, DeviceAppUpdate |
| pos | PosSession (sessao agente + rota alocada) |
| sms | SmsMessage |
| audit | AuditLog |
| reports | Dashboard, receita, reconciliacao, exports |

## Features

- Login premium split-screen com logo BuzUp
- Checkout publico mobile-first com bilhete PDF/QR
- i18n PT/EN, dark/light theme com logos adaptados
- RBAC dinamico com checkboxes de 34 permissoes
- Cartoes fisicos (NFC) e digitais (QR) com import Excel
- Sidebar com dropdown expandivel (Cartoes Fisicos/Digitais)
- Pacotes de desconto (percentagem, valor fixo, viagens gratis)
- Motor de tarifas (preco fixo, origem/destino, distancia)
- Programacao de viagens com geracao automatica diaria
- Validacao: pacote especial > saldo normal > nega
- SMS automatico: recarga, debito, criacao conta, OTP, atribuicao cartao
- OTP auth para passageiros (6 digitos, 5min TTL, normalizacao MSISDN e rate limit)
- PWA instalavel com manifest, icons, apple touch icon e service worker offline-first para shell
- GPS tracking com mapa Leaflet/OpenStreetMap
- Extracto PDF por passageiro com periodo
- Profile popover + notificacoes no topbar
- Table sorting, search, paginacao, DetailDrawer
- Eye icon em todas as tabelas para visualizar detalhes
- Formularios com selects (sem IDs manuais)
- Integracoes MPESA/EMOLA + SMS Bluteki

## Documentacao

- [Arquitectura Enterprise](docs/buzup-enterprise-architecture.md)
- [Workflows Operacionais](docs/WORKFLOWS.md)
- [Deploy em Servidor Compartilhado](docs/DEPLOYMENT.md)
