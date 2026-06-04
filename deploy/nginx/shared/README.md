# BuzUp shared Nginx snippets

Estes ficheiros sao para o proxy central do servidor compartilhado. No servidor actual, esse papel esta no Nginx do projecto CONDOVISIT, que tambem esta ligado a rede Docker `shared_web`.

Ordem esperada:

1. Subir o ambiente BuzUp desejado com `make staging-deploy-shared`.
2. Confirmar que o proxy central esta na rede `shared_web`.
3. Instalar o snippet correspondente no proxy central.
4. Recarregar Nginx.
5. Emitir ou renovar TLS se o certificado actual nao cobrir o dominio.

Aliases Docker usados:

- QA/Staging actual: `updigital.co.mz`, `www.updigital.co.mz` -> `buzup_gateway_staging:80`
- Producao futura: `buzup.co.mz` -> `buzup_gateway_prod:80`
