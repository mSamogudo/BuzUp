# Testes de fumo do frontend

Rede de segurança para a migração do frontend para shadcn
(ver `docs/superpowers/specs/2026-09-19-frontend-shadcn-tpmtur-design.md`).

## Porque é que isto tem árvore de dependências própria

Estes testes não partilham `node_modules` com o `frontend/`, de propósito. Têm de
sobreviver **inalterados** à subida de React 18 para 19. Se partilhassem dependências,
a migração podia partir os testes e ninguém saberia distinguir "o teste partiu" de
"a aplicação partiu" — que é precisamente a pergunta a que eles existem para responder.

Pela mesma razão, **nenhum selector usa classes CSS**. Tudo por papel e por texto
(`getByRole`, `getByPlaceholder`). As classes `admin-table` e `admin-sidebar`
desaparecem na migração; o comportamento que elas suportam não pode desaparecer.

## Correr

```sh
# 1. Levantar o ambiente do projecto
make dev-up-d
docker exec buzup_backend_dev python manage.py seed_roles
docker exec buzup_backend_dev python manage.py ensure_superadmin

# 2. Dados (ver a secção seguinte — o seed de origem está desactualizado)

# 3. Testes
cd e2e && npm install && npx playwright test
```

Apontar a outro ambiente: `BUZUP_BASE_URL=https://… npx playwright test`.
Credenciais: `BUZUP_USER` e `BUZUP_PASS`, por omissão `admin`/`admin`.

## Dados de que os testes precisam

O ambiente limpo **não chega**. Duas coisas foram precisas:

**1. O `marketing/seed_demo.py` falha a meio.** Rebenta nos terminais com
`Device.assigned_agent must be a "User" instance` — o modelo mudou desde que o script
foi escrito. Falha depois de criar o essencial (7 rotas, 30 paragens, 12 veículos,
10 motoristas, 28 viagens, 45 passageiros, 425 validações, 111 pagamentos), por isso
serve. Correr assim:

```sh
docker cp marketing/seed_demo.py buzup_backend_dev:/tmp/seed_demo.py
docker exec buzup_backend_dev python manage.py shell -c "exec(open('/tmp/seed_demo.py').read())"
```

**2. O fluxo de compra pública fica sem paragens.** `/api/public/trips/?sellable=1`
só devolve paragens de rotas com partidas `SCHEDULED` **futuras** e com veículo
atribuído. O seed cria viagens nos últimos 7 dias — todas passadas — e a página
`/comprar` abre sem origens nem destinos. Criar partidas futuras:

```sh
docker exec buzup_backend_dev python manage.py shell -c "
from apps.trips.models import Trip, Vehicle
from apps.routes.models import Route
from django.utils import timezone
from datetime import timedelta
agora = timezone.now()
rotas, veics = list(Route.objects.filter(status='active')[:4]), list(Vehicle.objects.all()[:4])
for i, rota in enumerate(rotas):
    for d in (1, 2, 3):
        Trip.objects.create(route=rota, vehicle=veics[i % len(veics)], direction='outbound',
            status=Trip.Status.SCHEDULED,
            planned_departure_at=agora + timedelta(days=d, hours=7+i),
            planned_arrival_at=agora + timedelta(days=d, hours=11+i))
"
```

**3. A conta `admin` tem 2FA sem telemóvel** e não entra. Em desenvolvimento:

```sh
docker exec buzup_backend_dev python manage.py shell -c "
from apps.users.models import User
u = User.objects.get(username='admin'); u.is_2fa_enabled = False; u.save(update_fields=['is_2fa_enabled'])
"
```

## Capturas de ecrã

```sh
node capturar.mjs antes      # base, antes de tocar em nada
node capturar.mjs fase-1     # depois de cada fase
```

Guarda 53 imagens por execução — 5 páginas públicas mais 24 do portal, em claro e
escuro. Não são testes de regressão visual: o redesenho muda tudo de propósito e
uma asserção de imagem falharia sempre. São artefactos para comparar a olho.

`capturas/antes/` está versionado porque deixa de ser reproduzível assim que a
migração começar. As restantes pastas são ignoradas — regeneram-se.

## Aviso conhecido que deve desaparecer

`publicas.spec.ts` tolera o aviso `React does not recognize the fetchPriority prop`,
disparado por `ProductImg` em `LandingPage.tsx`. É real: o React 18 não reconhece a
prop em camelCase, o React 19 reconhece.

**Depois da fase 1 este aviso deve desaparecer.** Se continuar lá, a subida não foi
feita e vale a pena apertar o filtro.
