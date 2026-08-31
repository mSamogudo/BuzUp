# Lacunas entre backend e front-end

Comparação entre `design/api-paths.txt` / `api-enums.txt` / `api-schemas.txt` e o
desenho. Duas listas: o que a API já dá e o desenho ainda não usa, e o que o
desenho pede e a API não tem.

---

## 1. Já existe na API, ainda sem ecrã (implementar no front-end)

### Tarifação
- **Matriz de tarifas por rota**: `routes/{id}/fare-matrix/` com `fill`, `import`,
  `template` e `return-direction`. É o ecrã A1.8 "Tabela de preços": grelha
  origem–destino, preenchimento em massa, importação por modelo e espelho para a
  volta.
- **Simulador de tarifa**: `fares/quote/` e `travel-passes/quote/`. Permite testar
  que regra ganha (prioridade, classe, zona) antes de publicar. Acrescentar como
  painel lateral do módulo Tarifas.

### Operação
- **Localização em tempo real**: `devices/location/`,
  `mobile/vehicles/locations/`, `mobile/routes/{id}/geometry/`. O módulo Mapa hoje
  mostra sete terminais estáticos; deve mostrar viaturas e o traçado das rotas.
- **Lugares**: `vehicles/seat-preview/`, `public/trips/{id}/seats/`,
  `trips/search/`. Existe `requires_seat_selection` e `SeatLayoutEnum`; falta o
  mapa de lugares e a ocupação por viagem no portal.

### Terminais
- `devices/heartbeat/` e `agent/devices/status/{serial_number}/`: mostrar último
  contacto e online/offline na tabela de Terminais, além do estado administrativo.
- `self-onboard` e `devices/activation-status/{code}`: falta o ecrã do lado do
  instalador.

### Cartões
- **Recuperação de cartão**: `recover-card/request-otp | verify-otp | associate`,
  `cards/capture-uid`, `cards/lookup`. A taxa `card_recovery` já está nas Taxas
  administrativas, mas o processo que a gera não tem lista nem histórico.
- `cards/{card_id}/qr.png`: falta ver e imprimir o QR.

### Financeiro
- `payments/webhooks/{provider}/` e `callbacks/{provider}/`: a acção "Ver
  callbacks" não tem ecrã. Criar registo de webhooks por provedor (M-Pesa,
  e-Mola) — é o primeiro sítio onde se olha quando um pagamento fica pendente.
- `admin/reports/builder/{kind}`: o catálogo existe, o construtor não.
- `admin/analytics/` e `admin/dashboard/charts/`: o Painel só mostra os números;
  faltam os gráficos servidos por estes endpoints.

### Público e distribuição
- `public/bus/{vehicle_uuid}/`, `public/ticket/{token}/`, `apps/latest/`,
  `apps/{slug}/download/`, `baixar/`, `{slug}/`: nenhum ecrã do portal gere estas
  páginas públicas nem os QR e links curtos que as alimentam.

### Conta e sistema
- `auth/2fa/verify/`, `change-password`, `password-reset`: as Definições têm
  preferências e notificações, falta segurança da conta.
- `health/`: sem indicador de estado do sistema.

---

## 2. O desenho pede, a API não tem (backend a construir)

### 2.1 CMS completo
Ver `03-cms-especificacao.md`. Nenhuma tabela nem endpoint existe hoje.
É o maior bloco de trabalho de backend deste handoff.

### 2.2 Turnos de agente (`shifts`)
Um turno prende um agente a uma viatura durante um período e fecha caixa: fundo de
maneio, apurado esperado, contado e diferença.
Precisa de: `/shifts` (listar, abrir, fechar, conferir, reabrir) e do campo
`shift_id` em bilhetes e validações, para o apurado ser calculado no servidor.

### 2.3 Complementos menores
- Campo de "último contacto" agregado por dispositivo (hoje só heartbeat cru).
- Endpoint de comparação de versões (faz parte do CMS).
- Estado agregado do sistema para o portal (`health` alargado com filas e workers).

---

## 3. Enums

Bem cobertos. `PassengerClassEnum`, `InterestEnum`, `FailureReasonEnum` e os de
dispositivo já aparecem traduzidos no desenho. Regra: valor vem da API, rótulo PT e
tom da pílula vêm da tabela `EN` de `Portal BusUp v2.dc.html`.
Quando o backend acrescentar um valor de enum sem tradução, o front-end mostra o
valor cru com pílula `mute` — nunca deve rebentar.
