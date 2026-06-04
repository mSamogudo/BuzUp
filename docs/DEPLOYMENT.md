# Deploy BuzUp em servidor compartilhado

Este projecto assume o mesmo modelo usado hoje por CONDOVISIT/Vura e ETICKETING: o CONDOVISIT recebe 80/443 como Nginx central, entra na rede Docker `shared_web`, e encaminha cada dominio para o gateway correcto.

## Topologia

| Ambiente | Compose | Rede interna | Gateway no `shared_web` | Volumes |
|---|---|---|---|---|
| Producao | `docker-compose.prod.yml` | `buzup_internal` | `buzup_gateway_prod:80` | `buzup_postgres_prod_data`, `buzup_static_data`, `buzup_media_data` |
| Staging | `docker-compose.staging.yml` | `buzup_staging_internal` | `buzup_gateway_staging:80` | `buzup_postgres_staging_data`, `buzup_static_staging_data`, `buzup_media_staging_data` |

O servico `gateway` e um Nginx interno do BuzUp. Ele serve `/static/` e `/media/`, encaminha `/api/` e `/admin/` para o backend, e encaminha o resto para o frontend. Assim o proxy central nao precisa montar volumes internos do Django.

## Preparacao no servidor

```sh
cp backend/.env.prod.example backend/.env.prod
cp backend/.env.staging.example backend/.env.staging
```

Editar os dois ficheiros com segredos reais. Nao guardar credenciais reais no Git.

Dominios esperados por defeito:

- QA/Staging actual: `updigital.co.mz`, `www.updigital.co.mz`
- QA por IP, opcional: `http://95.216.50.19:8083`
- Producao futura: `buzup.co.mz`, `www.buzup.co.mz`

## Deploy

```sh
make staging-deploy-shared
# Futuro, quando o dominio BuzUp estiver pronto:
# make prod-deploy-shared
```

Os scripts criam as redes e volumes externos se ainda nao existirem, validam o Compose, fazem build, sobem `db redis backend frontend gateway`, aplicam migrations, executam `check --deploy`, validam migrations pendentes e verificam healthchecks.

## Proxy central CONDOVISIT

O proxy central esta no projecto `CONDVISIT`, em `docker/prod/nginx.conf`, `docker/prod/nginx.http.conf` e `docker/prod/nginx.mixed.conf`. Esses ficheiros devem encaminhar:

- Agora: `updigital.co.mz` e `www.updigital.co.mz` para `buzup_gateway_staging:80`
- Futuro: `buzup.co.mz` e `www.buzup.co.mz` para `buzup_gateway_prod:80`

Os snippets abaixo sao equivalentes ao que deve existir no proxy central quando ele esta ligado a rede Docker `shared_web`.

### QA/Staging Actual

```nginx
server {
  listen 80;
  server_name updigital.co.mz www.updigital.co.mz;

  client_max_body_size 25m;
  resolver 127.0.0.11 valid=30s ipv6=off;
  set $buzup_gateway_upstream http://buzup_gateway_staging:80;

  location / {
    proxy_pass $buzup_gateway_upstream;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;
  }
}
```

### Producao Futura

```nginx
server {
  listen 80;
  server_name buzup.co.mz www.buzup.co.mz;

  client_max_body_size 25m;
  resolver 127.0.0.11 valid=30s ipv6=off;
  set $buzup_gateway_upstream http://buzup_gateway_prod:80;

  location / {
    proxy_pass $buzup_gateway_upstream;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;
  }
}
```

Com HTTPS activo para `updigital.co.mz`, manter `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True` e `CSRF_COOKIE_SECURE=True` no `.env.staging`.

## Sequencia recomendada no servidor

1. Subir BuzUp staging com `make staging-deploy-shared`.
2. No CONDOVISIT, aplicar os blocos de `updigital.co.mz` e `www.updigital.co.mz` e fazer reload/deploy.
3. Testar `/healthz`, `/api/health/`, checkout publico e login admin em `updigital.co.mz`.
4. Se for preciso QA por IP publico, mudar `BUZUP_STAGING_QA_HTTP_BIND=0.0.0.0:8083` em `backend/.env.staging`, redeployar staging, e testar `http://95.216.50.19:8083`.
5. Quando o dominio BuzUp estiver pronto, subir prod com `make prod-deploy-shared`, activar os blocos de `buzup.co.mz` e emitir certificados.

O bloco HTTPS de `updigital.co.mz` no CONDOVISIT usa o certificado `/etc/letsencrypt/live/updigital.co.mz`. Se ainda nao existir, usar primeiro `docker/prod/nginx.http.conf`, emitir o certificado e depois voltar ao `docker/prod/nginx.conf`.

Certificados actuais via webroot do CONDOVISIT:

```sh
certbot certonly --webroot -w /var/www/certbot -d updigital.co.mz -d www.updigital.co.mz
```

Certificados futuros via webroot do CONDOVISIT:

```sh
certbot certonly --webroot -w /var/www/certbot -d buzup.co.mz -d www.buzup.co.mz
```

Nao executar `docker compose --profile standalone` no servidor compartilhado, porque esse modo tenta publicar a porta 80 directamente e pode colidir com CONDOVISIT, ETICKETING ou o proxy central.
