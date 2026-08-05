#!/bin/sh
# Vigia dos dominios do goup-vps.
#
# PORQUE EXISTE. Um monitor externo (UptimeRobot e afins) exige uma conta que
# nao esta criada. Este vigia usa o que a casa ja tem: o gateway de SMS do
# BuzUp. Nao substitui um monitor de fora — se a maquina inteira cair, ninguem
# manda o SMS — mas apanha o caso comum e mais frequente: um contentor que
# morre, um certificado que expira, um dominio que passa a servir outra coisa.
#
# Corre pelo cron de 10 em 10 minutos. So avisa na MUDANCA de estado: um
# dominio em baixo durante duas horas manda um SMS, nao doze.
#
# Estado anterior em /var/lib/buzup-vigia/.

set -u
ESTADO_DIR=/var/lib/buzup-vigia
mkdir -p "$ESTADO_DIR"

# dominio:texto que TEM de aparecer no titulo
ALVOS="
payup.updigital.co.mz:PayUp
buzup-test.updigital.co.mz:BusUp
maputo-test.ferroviario.co.mz:Ferroviário
goup-test.updigital.co.mz:GOUP
test.vura.co.mz:VURA
"

avisar() {
    mensagem="$1"
    logger -t buzup-vigia "$mensagem"
    # O SMS sai pelo backend do BuzUp, que ja tem o gateway configurado.
    docker exec buzup_backend_staging python manage.py shell -c "
from django.conf import settings
from apps.sms.services.sender import send_sms
for numero in str(getattr(settings, 'ALERT_SMS_NUMBERS', '') or '').split(','):
    numero = numero.strip()
    if numero:
        send_sms(numero, '''$mensagem''', purpose='INFRA_ALERT')
" >/dev/null 2>&1 || logger -t buzup-vigia "falhou o envio do SMS"
}

mudou() {
    # $1 chave, $2 estado novo ("ok" ou "mau"), $3 mensagem
    ficheiro="$ESTADO_DIR/$1"
    anterior=$(cat "$ficheiro" 2>/dev/null || echo "ok")
    printf '%s' "$2" > "$ficheiro"
    [ "$anterior" != "$2" ] || return 1
    return 0
}

problemas=0

for par in $ALVOS; do
    dominio=${par%%:*}
    esperado=${par#*:}
    titulo=$(curl -sk --max-time 10 "https://$dominio/" 2>/dev/null | grep -oE '<title>[^<]*' | head -1)
    case "$titulo" in
        *"$esperado"*) estado=ok ;;
        *) estado=mau ;;
    esac
    if [ "$estado" = "mau" ]; then
        problemas=$((problemas + 1))
        if mudou "dom_$dominio" mau; then
            avisar "BuzUp: $dominio nao responde como esperado. Verificar o servidor."
        fi
    else
        if mudou "dom_$dominio" ok; then
            avisar "BuzUp: $dominio voltou ao normal."
        fi
    fi
done

# Contentores doentes
maus=$(docker ps --filter health=unhealthy --format '{{.Names}}' | tr '\n' ' ')
if [ -n "$maus" ]; then
    problemas=$((problemas + 1))
    if mudou containers mau; then
        avisar "BuzUp: contentores nao saudaveis: $maus"
    fi
else
    if mudou containers ok; then
        avisar "BuzUp: todos os contentores voltaram ao normal."
    fi
fi

# Certificados a menos de 10 dias de expirar. Um certificado expirado deixa o
# site inacessivel sem nada ter mudado no codigo — e o aviso do Let's Encrypt
# vai para um email que ninguem le.
for cert in /etc/letsencrypt/live/*/fullchain.pem; do
    [ -f "$cert" ] || continue
    nome=$(basename "$(dirname "$cert")")
    if ! openssl x509 -checkend 864000 -noout -in "$cert" >/dev/null 2>&1; then
        problemas=$((problemas + 1))
        if mudou "cert_$nome" mau; then
            avisar "BuzUp: certificado de $nome expira em menos de 10 dias."
        fi
    else
        mudou "cert_$nome" ok >/dev/null
    fi
done

# Disco acima de 85%
uso=$(df -P / | awk 'NR==2{gsub("%","",$5); print $5}')
if [ "${uso:-0}" -ge 85 ]; then
    problemas=$((problemas + 1))
    if mudou disco mau; then
        avisar "BuzUp: disco do servidor a ${uso}%."
    fi
else
    mudou disco ok >/dev/null
fi

exit $([ "$problemas" -eq 0 ] && echo 0 || echo 1)
