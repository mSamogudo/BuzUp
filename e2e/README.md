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

## A base envelhece

As viagens de demonstração são criadas com datas relativas (`agora + 1 dia`).
Ao fim de alguns dias deixam de ser futuras, e então:

- `/app/trips` mostra menos linhas e a captura fica mais curta;
- o dashboard muda os agregados;
- `/comprar` pode ficar sem paragens, porque a API só oferece as de rotas com
  partidas agendadas futuras.

Comparar `capturas/antes/` com uma captura tirada dias depois mostra
diferenças que **não** são regressões — são o calendário. Antes de comparar,
recriar as partidas futuras (ver secção anterior) e, se possível, capturar as
duas pontas no mesmo dia.

## Aviso conhecido que deve desaparecer

`publicas.spec.ts` tolera o aviso `React does not recognize the fetchPriority prop`,
disparado por `ProductImg` em `LandingPage.tsx`. É real: o React 18 não reconhece a
prop em camelCase, o React 19 reconhece.

**Depois da fase 1 este aviso deve desaparecer.** Se continuar lá, a subida não foi
feita e vale a pena apertar o filtro.


## O teste das paragens depende de partidas futuras

`publicas.spec.ts › a compra de bilhete sugere paragens vindas do backend`
falha com "Nenhuma paragem com esse nome" quando **todas** as viagens semeadas
já partiram. Não é regressão: `/api/public/trips/?sellable=1` devolve as
paragens das viagens vendáveis, e se não houver viagens futuras a lista vem
vazia. Foi o que aconteceu a 23/09 — as 40 viagens do seed tinham partido
todas.

Recriar (só na base de dados de desenvolvimento):

```bash
docker exec buzup_backend_dev python manage.py shell -c "
from datetime import timedelta
from django.apps import apps
from django.utils import timezone
Trip = apps.get_model('trips','Trip'); Route = apps.get_model('routes','Route')
RouteStop = apps.get_model('routes','RouteStop'); Vehicle = apps.get_model('trips','Vehicle')
agora = timezone.now()
rotas = [r for r in Route.objects.all() if RouteStop.objects.filter(route=r).count() >= 2]
veic = list(Vehicle.objects.all()[:4])
for d in range(1, 8):
    for i, r in enumerate(rotas):
        p = agora + timedelta(days=d, hours=6 + (i % 6) * 2)
        Trip.objects.create(route=r, vehicle=veic[i % len(veic)], direction='outbound',
                            planned_departure_at=p, planned_arrival_at=p + timedelta(hours=2),
                            status='scheduled')
print('futuras:', Trip.objects.filter(planned_departure_at__gte=agora).count())
"
```

Os nomes dos modelos não são óbvios: `Trip` e `Vehicle` vivem os dois em
`trips`, e o campo é `planned_departure_at`, não `departure_datetime`.

## Auditoria de contraste

`node contraste.mjs` percorre 32 rotas nos dois temas, apanha cada texto
visível e compara-o com o fundo **real** — sobe a árvore até encontrar um
opaco, compondo o que for translúcido pelo caminho. Não é uma tabela de
tokens: é o que o browser desenhou.

Sai com código 1 se encontrar algum par abaixo do mínimo WCAG AA que se
aplica àquele tamanho de letra (4,5:1, ou 3:1 em texto grande).

Duas armadilhas que a ferramenta já conhece, e que davam falsos positivos:
um fundo pintado por degradé ou imagem deixa `backgroundColor` transparente,
e um pintado por `::before`/`::after` não aparece de todo no elemento. Nos
dois casos a medição é abandonada em vez de subir até à página e inventar um
"branco sobre branco".
