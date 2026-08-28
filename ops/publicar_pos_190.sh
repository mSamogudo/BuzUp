#!/bin/bash
# Publica a POS 1.9.0 em producao e so a torna OBRIGATORIA depois de provar,
# de fora, que a descarga funciona e que o ficheiro chega igual.
#
# A ordem importa: uma versao obrigatoria cuja descarga falhe deixa o dialogo
# de actualizacao aberto e sem saida em todos os terminais do terreno. Por
# isso publica-se primeiro sem obrigar, prova-se, e so entao se obriga.
#
# Correr no goup-vps:  bash /tmp/publicar_190.sh
set -euo pipefail

APK=/tmp/buzup-pos-1.9.0.apk
SHA=44bf66a6682110e32f7809c1448aea0d41a5a04dd71a6b2c5952cba120cb6697
BASE=https://tpm-tur.updigital.co.mz

echo "== 1. conferir o ficheiro =="
test -f "$APK" || { echo "FALTA $APK"; exit 1; }
local_sha=$(sha256sum "$APK" | cut -d' ' -f1)
[ "$local_sha" = "$SHA" ] || { echo "checksum diferente: $local_sha"; exit 1; }
echo "   ok — 1.9.0+37, $(stat -c%s "$APK") bytes"

echo "== 2. por o APK na media de producao =="
docker exec buzup_backend_prod mkdir -p /app/media/app-releases
docker cp "$APK" buzup_backend_prod:/app/media/app-releases/buzup-pos-1.9.0.apk
docker exec buzup_backend_prod sha256sum /app/media/app-releases/buzup-pos-1.9.0.apk

echo "== 3. criar a versao: PUBLICADA, ainda NAO obrigatoria =="
docker exec buzup_backend_prod python manage.py shell -c "
from django.utils import timezone
from apps.app_releases.models import AppRelease

r, novo = AppRelease.objects.get_or_create(
    app_type='pos', version_code=37, defaults=dict(version_name='1.9.0'))
r.version_name = '1.9.0'
r.apk_file = 'app-releases/buzup-pos-1.9.0.apk'
r.checksum = '$SHA'
r.release_notes = (
    'Nome e documento do passageiro nas rotas internacionais.\n'
    'Cada motorista ve so as viagens que lhe estao alocadas.\n'
    'Venda a numerario com o bilhete entregue por SMS.\n'
    'Validar o bilhete no proprio ecra da venda.\n'
    'A primeira venda abre o embarque.\n'
    'Ecras mais rapidos: a ligacao deixa de ser refeita a cada pedido.'
)
r.is_mandatory = False
r.status = AppRelease.Status.PUBLISHED
r.published_at = r.published_at or timezone.now()
r.save()
print('   release', r.id, 'criada' if novo else 'actualizada')
"

echo "== 4. provar a descarga a partir de fora =="
ID=$(docker exec buzup_backend_prod python manage.py shell -c "
from apps.app_releases.models import AppRelease
print(AppRelease.objects.get(app_type='pos', version_code=37).id)" 2>/dev/null | tail -1 | tr -d '\r')

tmp=$(mktemp)
code=$(curl -sS -w '%{http_code}' -o "$tmp" -L "$BASE/api/app-releases/$ID/download/")
baixado=$(sha256sum "$tmp" | cut -d' ' -f1)
tam=$(stat -c%s "$tmp")
rm -f "$tmp"
echo "   HTTP $code · $tam bytes"
echo "   $baixado"
if [ "$code" != "200" ] || [ "$baixado" != "$SHA" ]; then
  echo
  echo "   DESCARGA MA. Fica publicada mas NAO obrigatoria — nada fica partido."
  echo "   Os terminais veem o aviso e podem dispensa-lo."
  exit 1
fi
echo "   identica ao original"

echo "== 5. so agora: obrigatoria =="
docker exec buzup_backend_prod python manage.py shell -c "
from apps.app_releases.models import AppRelease
r = AppRelease.objects.get(app_type='pos', version_code=37)
r.is_mandatory = True
r.min_supported_version_code = 37
r.save(update_fields=['is_mandatory', 'min_supported_version_code', 'updated_at'])
print('   obrigatoria:', r.is_mandatory, '| minimo suportado:', r.min_supported_version_code)
"

echo "== 6. o que cada terminal vai receber =="
docker exec buzup_backend_prod python manage.py shell -c "
from apps.devices.models import Device
# A app reporta o numero logico de build (tira o desvio de ABI com % 1000).
build = {'1.0.0': 1, '1.7.1': 24, '1.7.2': 25, '1.7.3': 26,
         '1.8.7': 34, '1.8.9': 36, '1.9.0': 37}
for d in Device.objects.order_by('serial_number'):
    c = build.get(d.app_version or '', 0)
    print('   actualiza  ' if c < 37 else '   ja esta  ', d.serial_number, d.app_version or '?')
"
echo
echo "FEITO."
