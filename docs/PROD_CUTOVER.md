# BuzUp — Cutover para produção (separar ambientes)

Objetivo:
- **buzup-test.updigital.co.mz** → ambiente de **teste/staging** (o stack atual `buzup_*_staging`, com hot-deploy).
- **buzup.updigital.co.mz** → **PRODUÇÃO** (stack novo `buzup_*_prod`, DB própria, settings endurecidas, credenciais de pagamento reais).

O TLS termina no **edge partilhado** `condvisit_nginx_prod` (NUNCA parar). O edge faz proxy de cada domínio para o gateway interno do respetivo stack via rede `shared_web`.

Servidor: `root@95.216.50.19` (chave `~/.ssh/condvisit_github_ed25519`). App em `/opt/buzup/app`.

---

## Pré-requisitos (antes de começar)
1. **DNS:** registo A `buzup-test.updigital.co.mz` → `95.216.50.19` (propagado).
2. **RAM:** o host (1.9 GB) não cabe um 2º stack completo — subir o VPS para ≥4 GB antes de levantar o prod.
3. **Credenciais de pagamento de produção** (M-Pesa / eMola / PayLess) e `SECRET_KEY` forte e `POSTGRES_PASSWORD` para a DB de prod.

---

## Passo 1 — Sincronizar o código mais recente
```sh
# do teu Mac (apenas código; NÃO toca em containers ainda)
bash scripts/staging-sync-backend.sh --no-restart   # rsync apps/ config/ etc. para /opt/buzup/app/backend
# (ou rsync manual de backend/config, docker-compose.prod.yml, docker/prod/nginx.conf)
```

## Passo 2 — Criar o `.env.prod` no servidor
```sh
ssh ... 'cd /opt/buzup/app && cp backend/.env.prod.example backend/.env.prod'
# editar backend/.env.prod e preencher:
#   SECRET_KEY=<forte>            POSTGRES_PASSWORD=<forte>
#   BLUTEKI_API_KEY=<chave UpDigital>   (sender ja = UpDigital)
#   PAYLESS_BEARER_TOKEN / MPESA_* / EMOLA_*  = credenciais de PRODUCAO
#   PAYMENT_GATEWAY_WEBHOOK_SECRET=<forte>
# (dominio/ALLOWED_HOSTS/PUBLIC_BASE_URL ja apontam para buzup.updigital.co.mz)
```
> O `prod.py` exige `SECRET_KEY` (falha no arranque se faltar) — propositado.

## Passo 3 — Criar rede e volumes externos do prod
```sh
ssh ... 'docker network create buzup_internal 2>/dev/null; \
  docker volume create buzup_postgres_prod_data; \
  docker volume create buzup_static_data; \
  docker volume create buzup_media_data'
# shared_web ja existe (o edge esta la).
```

## Passo 4 — Levantar o stack de produção (DB limpa)
```sh
ssh ... 'cd /opt/buzup/app && docker compose -f docker-compose.prod.yml up -d --build'
# AUTO_MIGRATE=true corre as migracoes numa DB vazia.
ssh ... 'docker ps --filter name=buzup_.*_prod --format "{{.Names}}: {{.Status}}"'
```
Seeds essenciais (DB limpa não tem superadmin nem roles):
```sh
ssh ... 'docker exec buzup_backend_prod python manage.py migrate --settings=config.settings.prod'   # confirmar
ssh ... 'docker exec -it buzup_backend_prod python manage.py createsuperuser --settings=config.settings.prod'
# + correr quaisquer comandos de seed de roles/capabilities que o projeto tenha (ver apps/users migracoes de seed).
```

## Passo 5 — TLS para buzup-test (e confirmar o de buzup)
```sh
# cert do buzup.updigital.co.mz ja existe. Emitir o de buzup-test via webroot do edge:
ssh ... 'docker exec condvisit_nginx_prod certbot certonly --webroot -w /var/www/certbot \
  -d buzup-test.updigital.co.mz --email <email> --agree-tos -n'   # ajustar ao setup de certbot do edge
```

## Passo 6 — Edge: re-apontar buzup → prod e adicionar buzup-test → staging
Editar `/etc/nginx/conf.d/default.conf` DENTRO do `condvisit_nginx_prod` (config do projeto condvisit, NÃO do BuzUp).
**Gotcha do inode do bind-mount:** editar com `cat ... > ficheiro` (NÃO `mv`/rsync que troca o inode), depois `nginx -s reload`.

1. No vhost existente `server_name buzup.updigital.co.mz;` trocar o upstream:
   ```
   set $buzup_gateway_upstream http://buzup_gateway_prod:80;   # era buzup_gateway_staging
   ```
2. Acrescentar um vhost novo (copiar o do buzup, trocar nome+cert+upstream):
   ```
   server {
     listen 443 ssl;
     server_name buzup-test.updigital.co.mz;
     client_max_body_size 60M;
     ssl_certificate     /etc/letsencrypt/live/buzup-test.updigital.co.mz/fullchain.pem;
     ssl_certificate_key /etc/letsencrypt/live/buzup-test.updigital.co.mz/privkey.pem;
     resolver 127.0.0.11 valid=10s;
     location / {
       set $buzup_test_upstream http://buzup_gateway_staging:80;
       proxy_pass $buzup_test_upstream;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto https;
     }
   }
   ```
3. `docker exec condvisit_nginx_prod nginx -t && docker exec condvisit_nginx_prod nginx -s reload`

## Passo 7 — Mudar o stack de teste para os settings de staging
O `docker-compose.staging.yml` já aponta `DJANGO_SETTINGS_MODULE=config.settings.staging`. Recriar para aplicar:
```sh
ssh ... 'cd /opt/buzup/app && docker compose -f docker-compose.staging.yml up -d --no-deps --force-recreate backend'
```
Ajustar `.env.staging` se quiseres separar o `PUBLIC_BASE_URL`/ALLOWED_HOSTS do teste para `buzup-test.updigital.co.mz` (e MPESA/EMOLA do teste em modo sandbox).

## Passo 8 — Apontar os builds das apps
- **Teste:** `pos_app/config/staging.env` e `mobile_app/config/staging.env` → `BUZUP_API_BASE_URL=https://buzup-test.updigital.co.mz`.
- **Produção:** `*/config/prod.env` → `https://buzup.updigital.co.mz` (já está). Builds de prod via `scripts/*-build-apk-prod.sh`.
- Publicar a APK de prod como release OTA no **portal de produção**.

## Passo 9 — Verificação
```sh
curl -s -o /dev/null -w "%{http_code}\n" https://buzup.updigital.co.mz/api/health/      # prod -> 200
curl -s -o /dev/null -w "%{http_code}\n" https://buzup-test.updigital.co.mz/api/health/ # teste -> 200
```
- Login + compra + pagamento real (valor pequeno) em prod.
- Confirmar OTP (sender UpDigital) em ambos.
- Confirmar que o prod usa a DB limpa (sem dados de teste).

## Rollback
- Edge: voltar o upstream de `buzup.updigital.co.mz` para `buzup_gateway_staging` e `nginx -s reload`.
- Parar o prod: `docker compose -f docker-compose.prod.yml down` (volumes externos persistem).
- O stack de teste mantém os dados atuais; nada é apagado.

## Notas
- NUNCA parar `condvisit_nginx_prod` (edge partilhado de buzup/updigital/condvisit).
- `buzup_nginx_prod` (no compose) está atrás do profile `standalone` — NÃO sobe por defeito (sem conflito de portas com o edge).
- mem_limits: backend prod 450m, db 256m, staging backend 400m.
