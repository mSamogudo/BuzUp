#!/bin/sh
# Vigia do goup-vps — TODOS os produtos, staging e producao.
#
# PORQUE EXISTE. Um monitor externo (UptimeRobot e afins) exige uma conta que
# nao esta criada. Este usa o que a casa ja tem: o gateway de SMS. Nao
# substitui um monitor de fora — se a maquina inteira cair, ninguem manda o
# SMS — mas apanha o que de facto nos mordeu: um contentor que morre, um
# certificado que expira, um dominio que passa a servir OUTRO produto.
#
# Corre pelo cron de 10 em 10 minutos e so avisa na MUDANCA de estado: um
# dominio em baixo duas horas manda um SMS, nao doze.
#
# Configuracao em /etc/buzup-vigia.conf (numeros de alerta). Fica no HOST e nao
# no ambiente de um contentor: o vigia tem de saber para quem ligar mesmo
# quando o contentor que costuma enviar e precisamente o que morreu.

set -u
ESTADO_DIR=/var/lib/buzup-vigia
CONF=/etc/buzup-vigia.conf
mkdir -p "$ESTADO_DIR"

NUMEROS=""
[ -f "$CONF" ] && . "$CONF"

# dominio:texto que TEM de aparecer no titulo.
# Inclui PRODUCAO (payup) e todas as stagings — um dominio a servir o produto
# errado e o problema que ja aconteceu, e nao da erro nenhum nos logs.
ALVOS="
payup.updigital.co.mz:PayUp
payup-test.updigital.co.mz:PayUp
buzup-test.updigital.co.mz:BusUp
maputo-test.ferroviario.co.mz:Ferroviário
goup-test.updigital.co.mz:GOUP
gestup-test.updigital.co.mz:GESTUP
cashup-test.updigital.co.mz:CashUp
taxup-test.updigital.co.mz:TaxUp
ossoma-test.updigital.co.mz:OSSOMA
test.vura.co.mz:VURA
"

# Contentores que sabem enviar SMS. Tenta-se por ordem: se o do BuzUp for o
# que caiu, outro qualquer manda o aviso.
EMISSORES="buzup_backend_staging goup_backend_staging cashup_backend_staging"

avisar() {
    mensagem="$1"
    logger -t buzup-vigia "$mensagem"
    [ -n "$NUMEROS" ] || { logger -t buzup-vigia "sem numeros configurados"; return; }
    for emissor in $EMISSORES; do
        docker exec "$emissor" python manage.py shell -c "
from apps.sms.services.sender import send_sms
for numero in '''$NUMEROS'''.split(','):
    numero = numero.strip()
    if numero:
        send_sms(numero, '''$mensagem''', purpose='INFRA_ALERT')
" >/dev/null 2>&1 && return
    done
    logger -t buzup-vigia "NENHUM emissor conseguiu mandar o SMS"
}

mudou() {
    ficheiro="$ESTADO_DIR/$1"
    anterior=$(cat "$ficheiro" 2>/dev/null || echo "ok")
    printf '%s' "$2" > "$ficheiro"
    [ "$anterior" != "$2" ]
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
        mudou "dom_$dominio" mau && avisar "BuzUp/infra: $dominio nao responde como esperado."
    else
        mudou "dom_$dominio" ok && avisar "BuzUp/infra: $dominio voltou ao normal."
    fi
done

maus=$(docker ps --filter health=unhealthy --format '{{.Names}}' | tr '\n' ' ')
if [ -n "$maus" ]; then
    problemas=$((problemas + 1))
    mudou containers mau && avisar "BuzUp/infra: contentores doentes: $maus"
else
    mudou containers ok && avisar "BuzUp/infra: contentores todos saudaveis outra vez."
fi

# Um contentor que morreu de vez nao aparece como "unhealthy": DESAPARECE.
# Conta-se quantos ha e avisa-se se o numero cair — foi assim que o gateway do
# UpDigital ficou em baixo depois de um reboot sem ninguem dar por isso.
atuais=$(docker ps --format '{{.Names}}' | wc -l)
esperados=$(cat "$ESTADO_DIR/contagem" 2>/dev/null || echo "$atuais")
if [ "$atuais" -lt "$esperados" ]; then
    problemas=$((problemas + 1))
    mudou contagem_baixa mau && avisar "BuzUp/infra: so $atuais contentores a correr (eram $esperados)."
else
    printf '%s' "$atuais" > "$ESTADO_DIR/contagem"
    mudou contagem_baixa ok >/dev/null
fi

# Certificados a menos de 10 dias. Um certificado expirado deixa o site
# inacessivel sem nada ter mudado no codigo, e o aviso do Let's Encrypt vai
# para um email que ninguem le.
for cert in /etc/letsencrypt/live/*/fullchain.pem; do
    [ -f "$cert" ] || continue
    nome=$(basename "$(dirname "$cert")")
    if openssl x509 -checkend 864000 -noout -in "$cert" >/dev/null 2>&1; then
        mudou "cert_$nome" ok >/dev/null
    else
        problemas=$((problemas + 1))
        mudou "cert_$nome" mau && avisar "BuzUp/infra: certificado de $nome expira em menos de 10 dias."
    fi
done

uso=$(df -P / | awk 'NR==2{gsub("%","",$5); print $5}')
if [ "${uso:-0}" -ge 85 ]; then
    problemas=$((problemas + 1))
    mudou disco mau && avisar "BuzUp/infra: disco do servidor a ${uso}%."
else
    mudou disco ok >/dev/null
fi

exit $([ "$problemas" -eq 0 ] && echo 0 || echo 1)
