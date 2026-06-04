# BuzUp — Workflows Operacionais

## C1. Workflow de Tarifas

### Conceito
O motor de tarifas calcula o preco de uma viagem com base em regras configuradas. Cada regra tem um metodo de calculo e uma prioridade — a primeira regra que faz match ganha.

### Metodos de Calculo
- **Preco Fixo**: valor unico para toda a rota (ex: R01 = 25,00 MZN)
- **Origem/Destino**: valor especifico para um par de paragens (ex: Museu→Matola = 15,00 MZN)
- **Distancia**: valor por km multiplicado pela distancia entre paragens, com min/max

### Fluxo
1. Admin cria **Produto Tarifario** (ex: "Viagem Avulsa", tipo single_trip)
2. Admin cria **Regra de Tarifa** associada ao produto:
   - Selecciona metodo (fixo / origem-destino / distancia)
   - Selecciona rota (ou todas)
   - Se origem-destino: selecciona paragens
   - Se distancia: define valor/km + min + max
   - Define classe de passageiro (normal/estudante/idoso/crianca)
3. Motor resolve tarifa (funcao `quote_fare`):
   - Filtra regras activas por prioridade descendente
   - Procura match por origem/destino especifico + classe → fallback para standard
   - Fallback para preco fixo da rota + classe → fallback para standard
   - Se nenhuma regra: erro NO_FARE_FOUND

### Ficheiros
- `backend/apps/fares/models.py` — FareProduct, FareRule
- `backend/apps/fares/services.py` — quote_fare()

---

## C2. Workflow de Pacotes

### Conceito
Pacotes permitem descontos em viagens. Um passageiro subscreve um pacote que lhe da beneficios durante um periodo.

### Tipos de Desconto
- **Percentagem**: desconto % sobre o valor da tarifa (ex: 50% na R01)
- **Valor Fixo**: saldo especial que cobre viagens ate esgotar (ex: 500 MZN de saldo especial)
- **Viagens Gratis**: numero fixo de viagens sem custo (ex: 10 viagens)

### Fluxo de Subscricao
1. Admin cria **Pacote** com tipo de desconto, valor, preco, validade e rotas
2. Passageiro subscreve (portal admin ou POS):
   - Sistema debita preco do pacote da wallet normal do passageiro
   - Cria PassengerPackage com saldo especial / viagens restantes
   - Define data de expiracao (activacao + validity_days)

### Fluxo de Consumo (na Validacao)
1. Passageiro apresenta cartao/QR no autocarro
2. Sistema verifica se tem pacote activo para a rota (`find_active_package_for_route`)
3. Se tem pacote:
   - PERCENTAGE: calcula tarifa com desconto, cobra resto da wallet normal
   - FIXED_AMOUNT: desconta do saldo especial, cobra resto da wallet normal
   - FREE_TRIPS: viagem gratis, decrementa trips_remaining
4. Se pacote esgotado (saldo=0 ou trips=0): marca como EXHAUSTED
5. Se sem pacote: cobra tarifa completa da wallet normal
6. Se sem saldo: nega validacao

### Expiracao
- Management command ou servico `expire_subscriptions()` marca pacotes expirados

### Ficheiros
- `backend/apps/packages/models.py` — Package, PackageRoute, PassengerPackage
- `backend/apps/packages/services.py` — subscribe, consume, find, expire

---

## C3. Workflow de Cartoes NFC

### Conceito
Cartoes fisicos NFC sao meios de identificacao e pagamento. O saldo pertence a carteira, nao ao plastico.

### Ciclo de Vida
```
STOCK → ACTIVE → BLOCKED/LOST → REPLACED → RETIRED
```

### Fluxo de Carregamento
1. Admin faz **upload CSV** com lote de cartoes (card_uid, card_number, batch)
2. Cartoes ficam em estado **STOCK** no sistema
3. No POS ou portal, agente **activa** o cartao:
   - Sistema cria conta tecnica (PassengerAccount anonimo)
   - Cria wallet associada
   - Cartao passa a ACTIVE

### Fluxo de Associacao
1. Cliente vai ao balcao ou POS com cartao activo
2. Agente **associa** cartao a uma conta de passageiro existente:
   - Sistema transfere o cartao para a wallet do passageiro
   - Saldo fica na wallet do passageiro (nao no plastico)

### Fluxo de Recarga
1. No POS: agente le cartao NFC → insere valor + telefone pagador
2. Sistema cria PaymentIntent → gateway MPESA/EMOLA
3. Mock: credita imediatamente | Real: aguarda callback
4. Wallet do cartao creditada com o valor

### Fluxo de Substituicao
1. Cartao perdido/danificado → agente bloqueia cartao antigo
2. Novo cartao em STOCK → agente executa **replace**
3. Wallet e conta transferidos do antigo para o novo
4. Antigo fica em REPLACED com referencia ao novo

### Ficheiros
- `backend/apps/cards/models.py` — PhysicalCard
- `backend/apps/cards/services.py` — activate, block, replace, link
- `backend/apps/core/import_csv.py` — import_cards

---

## C4. Workflow de Validacao (Autocarro)

### Conceito
A validacao acontece no autocarro quando o passageiro embarca. O validador (POS UROVO/SUNMI) tem uma rota alocada fixa.

### Pre-Requisitos
1. POS faz self-onboarding → admin aprova no portal
2. Agente abre sessao no POS com rota alocada (ex: R01)
3. Rota tem tarifa configurada no motor de tarifas

### Fluxo NFC (Pay-as-you-go)
```
Scan NFC → Cartao existe? → Activo? → Tem wallet?
  → Calcular tarifa para a rota da sessao
  → Tem pacote activo para a rota?
    SIM → Consumir do pacote (gratis / desconto / saldo especial)
      → Se pacote nao cobre tudo → Cobrar resto da wallet normal
    NAO → Cobrar tarifa completa da wallet normal
  → Saldo suficiente?
    SIM → Criar ValidationEvent(APPROVED) + WalletTransaction
    NAO → Criar ValidationEvent(DENIED, INSUFFICIENT_BALANCE)
```

### Fluxo QR (Bilhete Digital)
```
Scan QR → Token valido? → Passe existe?
  → Estado ACTIVE? → Nao expirado?
    SIM → Consumir passe (marcar USED, uma unica vez)
      → Criar ValidationEvent(APPROVED)
    NAO → Criar ValidationEvent(DENIED, PASS_ALREADY_USED/PASS_EXPIRED)
```

### Falhas Possiveis
| Codigo | Descricao |
|--------|-----------|
| DEVICE_BLOCKED | Dispositivo bloqueado pelo admin |
| INVALID_TOKEN | Cartao/QR nao encontrado |
| CARD_BLOCKED | Cartao em estado bloqueado |
| INSUFFICIENT_BALANCE | Sem saldo na wallet |
| ACCOUNT_BLOCKED | Conta do passageiro bloqueada |
| PASS_ALREADY_USED | Passe digital ja consumido |
| PASS_EXPIRED | Passe digital expirado |
| ROUTE_NOT_ALLOWED | Rota nao existe |
| NO_FARE_FOUND | Sem tarifa configurada para a rota |

### Idempotencia
Cada validacao tem um `idempotency_key` unico. Se o mesmo key for enviado novamente, retorna o evento existente sem criar duplicado.

### GPS
O POS envia posicao GPS a cada heartbeat. O sistema regista lat/lng/speed/heading no Device para tracking em tempo real dos autocarros.

### Ficheiros
- `backend/apps/validations/services.py` — validate_card, validate_qr_pass, _charge_with_package_fallback
- `backend/apps/pos/api/views.py` — PosCardValidateView, PosQrValidateView
- `backend/apps/pos/models.py` — PosSession
