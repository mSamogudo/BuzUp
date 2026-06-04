# BuzUp - Arquitectura Enterprise Cashless Online

## 1. Resumo Executivo

O BuzUp e uma plataforma cashless para gestao de mobilidade em transporte publico, baseada na arquitectura, estrutura de repositorio e stack do projecto ETICKETING.

O sistema sera single-client, totalmente online e sem dependencia de bilhetes fisicos impressos. O passageiro podera comprar bilhete digital sem criar conta, usar uma conta digital na app mobile ou usar um cartao fisico NFC recarregavel. O cartao fisico nao representa um bilhete; ele e apenas um meio de identificacao, recarga, validacao e pagamento associado a uma carteira de transporte ou a uma conta tecnica interna.

Superficies principais:

- Portal Administrativo Web: Django, DRF, React e Vite.
- App Mobile Passageiro: Flutter.
- App POS UROVO I9100 e SUNMI V2s: Flutter com SDK nativo via Android platform channels.
- Backend Core: Django/DRF, seguindo padroes do ETICKETING.
- Integracoes: SMS API e API de pagamentos ja usadas no ETICKETING.

Principios fixos:

- Sem multi-tenant.
- Sem bilhetes em papel.
- Sem vendas em dinheiro.
- Sem operacao offline.
- Compra de bilhete digital sem obrigar o cliente a criar conta.
- Conta digital apenas como canal de conveniencia, fidelizacao e historico.
- Cartoes fisicos baseados em NFC.
- Todas as recargas, validacoes, compras e debitos sao online.
- Todo movimento financeiro e feito por ledger auditavel.
- Padrao enterprise: idempotencia, RBAC, device binding, auditoria, reconciliacao, observabilidade, backups e controlo de releases desde a primeira versao.

## 2. Objectivos do Produto

O BuzUp deve resolver cinco problemas principais:

1. Permitir compra de bilhete digital sem conta obrigatoria.
2. Permitir recarregamento de saldo por carteira movel ou API de pagamento.
3. Permitir que passageiros tenham uma conta digital opcional de transporte.
4. Permitir pagamento de viagens usando bilhete digital, saldo da conta, cartao NFC ou app mobile.
5. Permitir controlo operacional e financeiro centralizado para o operador.

Resultados esperados:

- Reducao de manuseio de dinheiro.
- Melhor controlo de receitas.
- Rastreabilidade completa de recargas, viagens e validacoes.
- Visibilidade operacional por rota, veiculo, agente, paragem e periodo.
- Experiencia simples para passageiros com e sem smartphone.
- Compra assistida ou autonoma sem friccao de registo.

## 3. Fora do Escopo Inicial

Estes pontos ficam fora do MVP:

- Multi-tenant.
- Bilhete fisico impresso.
- Operacao offline.
- Pagamento em numerario.
- Impressao de recibos em papel.
- App mobile separada por cliente.
- Marketplace de operadores.
- Integracao com multiplos operadores de transporte.

Podem ser considerados em fases futuras:

- Passes mensais e produtos recorrentes.
- Tarifa social, estudante, idoso e subsidios.
- Controlo de lotacao em tempo real.
- Integracao com sistemas municipais.
- Cartoes bancarios contactless.
- Validadores dedicados alem de UROVO I9100 e SUNMI V2s.

## 4. Arquitectura Geral

```text
                         +--------------------------+
                         | Portal Administrativo    |
                         | React + Vite             |
                         +------------+-------------+
                                      |
                                      | DRF API
                                      |
+-------------------+     +-----------v------------+     +-------------------+
| App Passageiro    |     | Backend Core Django    |     | App POS           |
| Flutter           +-----> DRF + PostgreSQL       <-----+ UROVO/SUNMI SDK   |
+-------------------+     +-----------+------------+     +-------------------+
                                      |
                       +--------------+---------------+
                       |                              |
                +------v-------+              +-------v------+
                | SMS API      |              | Payment API  |
                +--------------+              +--------------+
```

Backend e responsavel por:

- Autenticacao.
- Checkout convidado.
- Carteiras e ledger.
- Pagamentos.
- Cartoes fisicos NFC.
- Rotas, paragens, tarifas e viagens.
- Validacoes.
- Relatorios.
- Auditoria.
- Integracao SMS.
- Integracao API de pagamentos.

Apps nunca devem calcular saldo de forma autoritativa. Elas apenas solicitam operacoes ao backend.

## 5. Stack Tecnica

Backend:

- Python.
- Django.
- Django REST Framework.
- PostgreSQL.
- Redis e Celery, se mantivermos o padrao ETICKETING para tarefas assincronas.
- JWT/session auth conforme arquitectura ETICKETING.

Frontend administrativo:

- React.
- Vite.
- TypeScript, se ja estiver no padrao ETICKETING ou se decidirmos elevar a qualidade do portal.
- UI baseada em componentes reutilizaveis.

Mobile:

- Flutter para app passageiro.
- Flutter para POS UROVO I9100.
- Flutter para POS SUNMI V2s.
- Android platform channels para SDK UROVO e SDK SUNMI.
- Plugin interno por fabricante para leitura NFC, scanner/QR quando disponivel, impressora quando aplicavel, device info e outros recursos do hardware.

Integracoes:

- SMS API do ETICKETING.
- API de pagamentos do ETICKETING.
- Webhooks/callbacks de pagamento.
- Servico interno de notificacoes.

Infraestrutura:

- Ambientes: local, staging e production.
- Deploy com padrao ETICKETING.
- Logs estruturados.
- Backups PostgreSQL.
- Monitoria de callbacks, pagamentos pendentes e falhas de validacao.

### 5.1 Estrutura Base Herdada do ETICKETING

O BuzUp deve nascer com a estrutura completa do ETICKETING, adaptada ao dominio de transporte:

```text
BuzUp/
- backend/
  - apps/
  - config/
  - manage.py
  - requirements.txt
  - Dockerfile
  - entrypoint.sh
- frontend/
  - src/
  - public/
  - package.json
  - vite.config.ts
  - Dockerfile
- pos-app/
  - lib/
  - android/
  - assets/
  - config/
  - scripts/
  - pubspec.yaml
- docker/
  - prod/
- scripts/
- docs/
- docker-compose.dev.yml
- docker-compose.prod.yml
- Makefile
```

Padroes ETICKETING a manter:

- Monolito modular Django em `backend/apps`.
- Separacao clara entre API, modelos, servicos, permissoes e integracoes.
- Portal React + Vite com modulos por capacidade operacional.
- POS Flutter com bridge nativa Kotlin/Android para hardware.
- Scripts padronizados para desenvolvimento, build, logs, APK e deploy.
- Configuracao por ambiente com `.env.example`, `dev`, `staging` e `prod`.
- Device management, activacao de dispositivo, controlo de releases/APKs e auditoria.
- Idempotency keys em pagamentos, recargas, validacoes e callbacks.
- Logs estruturados, reconciliacao financeira e trilha de auditoria transversal.

## 6. Canais do Ecossistema

### 6.1 Portal Administrativo

O portal e o centro operacional e financeiro.

Modulos:

- Dashboard.
- Compras convidado.
- Passageiros.
- Contas e carteiras.
- Cartoes fisicos NFC.
- Rotas e paragens.
- Tarifas.
- Viagens.
- Veiculos.
- Motoristas.
- Agentes POS.
- Dispositivos POS UROVO I9100.
- Dispositivos POS SUNMI V2s.
- Pedidos de activacao de POS.
- Controlo de APKs e versoes das apps.
- Pagamentos.
- Recargas.
- Validacoes.
- Relatorios.
- Reconciliacao.
- Auditoria.
- Configuracoes da organizacao.

### 6.2 Compra de Bilhete Sem Conta

O cliente nao deve depender de conta para comprar bilhete. A conta e uma opcao, nao uma barreira.

Funcionalidades:

- Comprar bilhete digital como convidado.
- Informar apenas dados minimos: telefone pagador, origem, destino, rota/viagem e quantidade.
- Criar `PaymentIntent` sem exigir `PassengerAccount`.
- Confirmar pagamento por callback.
- Emitir `DigitalTravelPass` ou `GuestTravelPass` com token/QR assinado.
- Enviar comprovativo e token por SMS, link seguro ou app quando existir.
- Permitir consulta do bilhete por referencia e telefone, sem login completo.
- Permitir associar a compra a uma conta depois, se o cliente criar conta no futuro.

Regras:

- Compra convidado nao cria conta de utilizador automaticamente.
- Dados pessoais devem ser minimos e proporcionais ao risco.
- O bilhete digital tem ciclo de vida proprio: emitido, activo, usado, expirado, cancelado ou reembolsado.
- Reemissao de link/QR exige validacao por OTP ou comprovativo equivalente.
- O backend deve aplicar rate limiting e deteccao de abuso no checkout convidado.

### 6.3 App Mobile Passageiro

Funcionalidades:

- Criar conta opcional.
- Login por telefone, OTP ou credenciais conforme padrao escolhido.
- Ver saldo.
- Recarregar conta via carteira movel.
- Ver transacoes.
- Ver historico de viagens.
- Pesquisar origem e destino.
- Consultar preco.
- Comprar direito digital de viagem com ou sem saldo em carteira.
- Pagar viagem com saldo.
- Apresentar QR Code/token para validacao.
- Associar cartao fisico a conta, se permitido.
- Bloquear cartao fisico perdido, se associado.

### 6.4 App POS UROVO I9100 e SUNMI V2s

Funcionalidades principais:

- Self-onboarding do dispositivo apos instalacao da app.
- Estado "aguardando aprovacao/configuracao" antes de operar.
- Login do agente.
- Vinculo do dispositivo ao backend.
- Consulta de cartao fisico NFC.
- Recarga de cartao fisico NFC.
- Activacao de cartao NFC anonimo ou associado.
- Associacao de cartao fisico NFC a conta, quando o cliente quiser.
- Substituicao de cartao fisico NFC.
- Bloqueio de cartao NFC.
- Consulta de saldo.
- Consulta de historico resumido.
- Venda assistida de bilhete digital sem conta.
- Validacao de QR Code/cartao, se o modelo do POS tambem operar como validador.

Suporte de hardware:

- UROVO I9100: integracao por SDK UROVO via platform channels.
- SUNMI V2s: integracao por SDK SUNMI via platform channels.
- A app deve isolar as capacidades por `DeviceCapability`, porque NFC, scanner, impressora e leitores podem variar por lote/modelo.
- O backend deve conhecer fabricante, modelo e capacidades activas de cada POS.

Regra cashless:

- O POS nao aceita numerario.
- O POS cria uma intencao de pagamento na API de pagamentos.
- O passageiro paga pela carteira movel.
- O backend confirma o pagamento por callback.
- O backend credita a carteira associada ao cartao.
- Quando a operacao for venda de bilhete sem conta, o backend emite o bilhete digital apos callback confirmado.

Regra de activacao:

- POS instalado nao opera automaticamente.
- Na primeira abertura, a app faz self-onboarding enviando dados do dispositivo.
- O portal recebe o pedido e fica responsavel pela configuracao e aprovacao.
- Enquanto nao for aprovado, o POS mostra apenas o estado de activacao.
- Depois de aprovado, o POS recebe configuracoes e permite login/operacao do agente.

### 6.5 Validacao

O validador pode ser o proprio POS UROVO I9100, o POS SUNMI V2s ou uma app dedicada no futuro.

Meios de validacao:

- QR Code/token da app mobile.
- QR Code/token emitido em compra convidado.
- Cartao fisico NFC lido por POS ou validador autorizado.
- Identificador de conta, em casos assistidos.

Todas as validacoes sao online:

- Sem rede, nao ha validacao.
- Sem resposta do backend, nao ha debito nem consumo de passe.
- Sem debito ou passe confirmado, nao ha autorizacao de embarque.

## 7. Modelo de Cliente, Conta e Carteira

### 7.1 Passageiro e Comprador

Tipos praticos:

- Comprador convidado sem conta, comprando bilhete digital avulso.
- Passageiro com app mobile.
- Passageiro sem smartphone, usando cartao fisico NFC.
- Passageiro com app e cartao fisico NFC associado.

Regras:

- Conta de passageiro nao e obrigatoria para comprar bilhete.
- Compra avulsa sem conta cria uma ordem/passe digital e nao exige carteira.
- Mesmo quando o passageiro usa apenas cartao fisico NFC, o sistema deve criar uma conta tecnica interna para manter ledger, saldo e historico.
- O cliente pode associar uma compra convidado ou cartao a uma conta depois, mediante verificacao.
- Dados de convidado devem ser suficientes para pagamento, entrega do bilhete, antifraude e suporte, sem forcar cadastro completo.

### 7.2 Conta

Entidade conceitual:

```text
PassengerAccount
- id
- full_name
- phone_number
- email
- document_number
- status
- created_at
- updated_at
```

Estados:

- active
- blocked
- suspended
- closed

### 7.3 Compra Convidado

Entidade conceitual:

```text
GuestCheckout
- id
- reference
- payer_phone
- buyer_name
- route
- trip
- origin_stop
- destination_stop
- quantity
- total_amount
- payment_intent
- status
- expires_at
- created_at
```

Estados:

- draft
- payment_pending
- paid
- issued
- expired
- cancelled
- refunded

Regras:

- `buyer_name` pode ser opcional no MVP, dependendo da politica operacional.
- `payer_phone` e obrigatorio quando a API de pagamento exigir telefone.
- O checkout convidado nunca depende de login.
- Bilhetes emitidos por checkout convidado devem ter token assinado e referencia consultavel.

### 7.4 Carteira

Entidade conceitual:

```text
Wallet
- id
- passenger_account
- balance_cached
- currency
- status
- created_at
- updated_at
```

O saldo em `balance_cached` e apenas uma optimizacao. A verdade financeira vem do ledger.

### 7.5 Ledger

Entidade conceitual:

```text
WalletTransaction
- id
- wallet
- type
- direction
- amount
- balance_before
- balance_after
- reference
- source
- status
- metadata
- created_at
```

Tipos:

- topup
- fare_debit
- refund
- reversal
- adjustment
- card_transfer
- fee

Regras:

- Transacoes financeiras sao imutaveis.
- Estornos geram novas transacoes, nao alteram a transacao original.
- Cada transacao tem referencia unica.
- Callbacks de pagamento sao idempotentes.
- Operacoes administrativas de saldo exigem permissao forte e motivo.

## 8. Cartao Fisico NFC

O cartao fisico NFC e um instrumento de acesso a carteira. Em producao, o desenho deve evitar depender apenas de UID publico quando o risco operacional exigir maior seguranca.

Entidade conceitual:

```text
PhysicalCard
- id
- card_uid
- card_token_hash
- card_number
- card_technology
- wallet
- passenger_account
- status
- issued_batch
- issued_at
- activated_at
- blocked_at
- replaced_by
```

Estados:

- stock
- active
- blocked
- lost
- replaced
- retired

Fluxos:

- Registar lote de cartoes.
- Activar cartao.
- Criar conta tecnica para cartao anonimo.
- Associar cartao a passageiro com app.
- Recarregar cartao via POS.
- Validar cartao em POS/validador autorizado.
- Bloquear cartao.
- Substituir cartao.
- Transferir saldo para novo cartao.

Regra importante:

- O saldo pertence a carteira, nao ao plastico.
- O cartao so identifica a carteira.
- Tecnologia recomendada para producao: NFC seguro com token interno e binding server-side.
- NFC UID simples pode servir para prototipo ou ambientes controlados, mas nao deve ser tratado como segredo.
- MIFARE/DESFire ou alternativa equivalente deve ser avaliada para resistencia a clonagem.

## 9. Pagamentos e Recargas

### 9.1 Payment Intent

Toda recarga, compra convidado, compra na app ou pagamento directo de viagem comeca com uma intencao de pagamento.

```text
PaymentIntent
- id
- reference
- purpose
- amount
- currency
- payer_phone
- provider
- channel
- status
- wallet
- guest_checkout
- travel_pass
- created_by
- expires_at
- created_at
```

Finalidades:

- mobile_wallet_topup
- pos_card_topup
- guest_travel_pass_purchase
- app_travel_pass_purchase
- direct_trip_payment
- refund

Estados:

- created
- pending
- confirmed
- failed
- expired
- reversed

### 9.2 Callback de Pagamento

```text
PaymentCallback
- id
- payment_intent
- provider_reference
- raw_payload
- signature_valid
- processing_status
- received_at
```

Regras:

- Validar assinatura ou autenticidade do callback.
- Confirmar valor, referencia, telefone e estado.
- Processar callback uma unica vez.
- Guardar payload bruto para auditoria.
- Nunca creditar carteira nem emitir bilhete sem confirmacao confiavel.

### 9.3 Recarga pela App Mobile

Fluxo:

1. Passageiro escolhe valor.
2. Passageiro escolhe carteira movel/provedor.
3. App envia pedido ao backend.
4. Backend cria `PaymentIntent`.
5. Backend chama API de pagamento.
6. Provedor confirma via callback.
7. Backend credita carteira via `WalletTransaction`.
8. Backend envia SMS/notificacao.
9. App actualiza saldo.

### 9.4 Recarga de Cartao no POS

Fluxo:

1. Agente faz login no POS.
2. POS le cartao fisico.
3. Backend retorna dados permitidos do cartao e saldo.
4. Agente insere valor e telefone pagador.
5. Backend cria `PaymentIntent` de recarga POS.
6. API de pagamento solicita pagamento ao passageiro.
7. Callback confirma pagamento.
8. Backend credita carteira do cartao.
9. POS mostra sucesso.
10. SMS confirma a recarga.

### 9.5 Compra de Bilhete Sem Conta

Fluxo:

1. Cliente escolhe rota, origem, destino, viagem e quantidade.
2. Cliente informa telefone pagador e dados minimos exigidos.
3. Backend calcula tarifa e cria `GuestCheckout`.
4. Backend cria `PaymentIntent` com finalidade `guest_travel_pass_purchase`.
5. API de pagamento solicita pagamento ao cliente.
6. Callback confirma pagamento.
7. Backend emite `DigitalTravelPass` sem exigir `PassengerAccount`.
8. Backend envia SMS/link seguro com referencia e token de acesso ao bilhete.
9. Validador consome o token uma unica vez no embarque.

Regras:

- Falha de pagamento nao emite passe.
- Passe convidado nao exige wallet.
- Reenvio do link deve exigir OTP no telefone usado na compra.
- A compra pode ser associada posteriormente a uma conta, mas isso nao altera o historico financeiro original.

## 10. Rotas, Paragens, Viagens e Tarifas

### 10.1 Rotas

```text
Route
- id
- code
- name
- status
- created_at
```

### 10.2 Paragens

```text
Stop
- id
- code
- name
- latitude
- longitude
- status
```

### 10.3 Paragens da Rota

```text
RouteStop
- id
- route
- stop
- sequence
- distance_from_start_km
- direction
```

### 10.4 Viagens

```text
Trip
- id
- route
- vehicle
- driver
- planned_departure_at
- actual_departure_at
- planned_arrival_at
- actual_arrival_at
- status
```

Estados:

- scheduled
- boarding
- departed
- completed
- cancelled

### 10.5 Motor de Tarifas

O motor de tarifas deve suportar evolucao sem reescrita.

Modelos de tarifa:

- Preco fixo por rota.
- Preco por origem e destino.
- Preco por zona.
- Preco por distancia.
- Preco por classe de passageiro.
- Produtos temporais como passe diario, semanal e mensal.

Entidades conceituais:

```text
FareProduct
- id
- name
- product_type
- status

FareRule
- id
- fare_product
- route
- origin_stop
- destination_stop
- zone
- passenger_class
- calculation_method
- fixed_amount
- amount_per_km
- min_amount
- max_amount
- valid_from
- valid_until
```

Regra inicial recomendada para MVP:

- Preco por origem/destino dentro de uma rota.
- Fallback por preco fixo da rota.
- Depois evoluir para distancia e zonas.

## 11. Pagamento de Viagem

O sistema nao depende de bilhete fisico impresso. Ele cria um direito digital de viagem, com ou sem conta, ou faz debito no momento da validacao.

### 11.1 Pre-compra na App ou Checkout Convidado

Fluxo:

1. Cliente escolhe origem e destino.
2. App, web/checkout ou POS consulta rotas/viagens disponiveis.
3. Backend calcula tarifa.
4. Cliente confirma compra.
5. Backend debita carteira, se houver conta, ou confirma pagamento directo por `PaymentIntent`.
6. Backend cria `DigitalTravelPass`.
7. App, SMS ou link seguro disponibiliza QR Code/token.
8. Validador consome o passe uma unica vez.

```text
DigitalTravelPass
- id
- passenger_account
- guest_checkout
- wallet
- payer_phone
- route
- trip
- origin_stop
- destination_stop
- fare_amount
- status
- token_hash
- delivery_channel
- valid_from
- valid_until
- used_at
```

Estados:

- active
- used
- expired
- cancelled
- refunded

### 11.2 Pay-as-you-go

Fluxo:

1. Passageiro apresenta cartao fisico NFC ou QR da conta.
2. Validador informa rota, viagem, origem e destino.
3. Backend calcula tarifa.
4. Backend verifica saldo.
5. Backend debita carteira.
6. Backend cria `ValidationEvent`.
7. Validador autoriza embarque.

Este modelo e recomendado para operacao rapida em autocarros.

## 12. Validacao

Entidade conceitual:

```text
ValidationEvent
- id
- validation_type
- passenger_account
- wallet
- physical_card
- digital_travel_pass
- route
- trip
- origin_stop
- destination_stop
- device
- amount_debited
- status
- failure_reason
- created_at
```

Tipos:

- card_pay_as_you_go
- qr_pay_as_you_go
- digital_travel_pass
- guest_digital_travel_pass

Falhas:

- insufficient_balance
- card_blocked
- account_blocked
- pass_already_used
- pass_expired
- invalid_token
- route_not_allowed
- device_blocked
- payment_error
- backend_unavailable

Regras:

- A validacao so aprova depois de resposta positiva do backend.
- Um `DigitalTravelPass` so pode ser usado uma vez.
- Debitos duplicados devem ser evitados por chave idempotente.
- Cada validacao tem referencia unica do dispositivo.

## 13. Dispositivos e POS UROVO/SUNMI

Entidade conceitual:

```text
Device
- id
- serial_number
- device_type
- model
- manufacturer
- imei
- android_id
- capabilities
- status
- assigned_agent
- activation_code
- activated_at
- last_seen_at
- app_version
```

Tipos:

- urovo_i9100_pos
- sunmi_v2s_pos
- mobile_app
- admin_browser
- future_validator

Estados:

- self_onboarded
- pending_activation
- pending_configuration
- active
- rejected
- blocked
- retired

Regras:

- POS precisa fazer self-onboarding apos instalacao da app.
- POS precisa ser configurado e aprovado no portal antes de operar.
- POS deve enviar serial/device id em todas as operacoes sensiveis.
- POS em estado pendente so pode consultar o estado da propria activacao.
- Dispositivo bloqueado nao pode recarregar nem validar.
- Permissoes devem considerar fabricante, modelo e capacidades reais do dispositivo.
- App POS deve suportar controlo de APKs, popup de nova versao, adiamento e actualizacao obrigatoria.

Capacidades rastreadas por dispositivo:

- nfc_reader
- qr_scanner
- thermal_printer
- camera
- secure_storage
- kiosk_mode
- apk_silent_install
- device_serial_access

### 13.1 Fluxo de Self-Onboarding do POS

O fluxo de activacao do POS deve seguir o mesmo padrao do ETICKETING:

1. Tecnico ou agente instala a app no UROVO I9100 ou SUNMI V2s.
2. Na primeira abertura, a app recolhe dados do dispositivo: serial, modelo, fabricante, IMEI/Android ID, versao da app e outros identificadores disponiveis no SDK.
3. A app envia um pedido de self-onboarding ao backend.
4. O backend cria ou actualiza o `Device` em estado `self_onboarded` ou `pending_activation`.
5. O backend devolve um codigo de activacao visivel no POS.
6. O POS entra em modo "aguardando configuracao/aprovacao".
7. No portal, o administrador ve o pedido de activacao pendente.
8. O administrador valida o dispositivo, configura permissao, agente responsavel, tipo de operacao e parametros permitidos.
9. O administrador aprova ou rejeita o pedido.
10. O POS consulta periodicamente o estado de activacao.
11. Quando aprovado, o POS recebe a configuracao autorizada e libera login/operacao.

Entidade conceitual complementar:

```text
DeviceActivationRequest
- id
- device
- activation_code
- requested_serial_number
- requested_model
- requested_manufacturer
- requested_imei
- requested_android_id
- requested_capabilities
- app_version
- status
- requested_at
- reviewed_by
- reviewed_at
- rejection_reason
```

Estados do pedido:

- pending
- approved
- rejected
- expired

Configuracoes aplicadas na aprovacao:

- agente ou grupo operacional associado.
- permissoes: recarga, consulta, validacao, associacao de cartao NFC e venda assistida.
- limites operacionais, se existirem.
- versao minima obrigatoria da app.
- estado inicial do dispositivo como `active`.

Regras de seguranca:

- O codigo de activacao nao substitui autenticacao do agente.
- Aprovacao do dispositivo e login do agente sao controlos separados.
- Um dispositivo rejeitado ou bloqueado nao pode criar novo pedido sem intervencao administrativa.
- Mudanca de serial/IMEI/Android ID deve gerar alerta ou exigir nova aprovacao.
- Activacao e aprovacao devem gerar `AuditLog`.

### 13.2 Controlo de APKs e Actualizacao do POS

O BuzUp deve seguir o mesmo padrao do ETICKETING para controlo de APKs.

O portal administrativo deve permitir:

- Registar nova versao da app POS.
- Fazer upload ou referenciar o APK.
- Definir numero da versao e `version_code`.
- Definir se a actualizacao e obrigatoria ou opcional.
- Definir notas da versao.
- Definir data de publicacao.
- Definir versao minima suportada.
- Definir publico-alvo: todos os POS, POS especificos, grupos ou modelos.
- Definir publico-alvo por fabricante: UROVO, SUNMI ou ambos.
- Consultar dispositivos actualizados, pendentes, adiados e com falha.

Entidade conceitual:

```text
AppRelease
- id
- app_type
- version_name
- version_code
- apk_file
- apk_url
- checksum
- release_notes
- is_mandatory
- min_supported_version_code
- target_device_type
- target_manufacturer
- target_model
- status
- published_at
- created_by
- created_at
```

Estados:

- draft
- published
- suspended
- retired

Entidade conceitual para acompanhamento:

```text
DeviceAppUpdate
- id
- device
- app_release
- current_version_code
- target_version_code
- status
- prompted_at
- deferred_until
- downloaded_at
- installed_at
- failed_reason
- created_at
```

Estados:

- pending
- prompted
- deferred
- downloading
- installed
- failed
- forced

Fluxo no POS:

1. POS faz login ou heartbeat periodico com `app_version` e `version_code`.
2. Backend verifica se existe `AppRelease` aplicavel ao dispositivo.
3. Se houver nova versao opcional, POS mostra popup com opcoes "Actualizar agora" e "Adiar".
4. Se o agente adiar, o POS grava `deferred_until` e volta a alertar depois do periodo definido.
5. Se a versao for obrigatoria, POS bloqueia operacoes sensiveis ate actualizar.
6. POS baixa o APK pelo link autorizado.
7. POS valida checksum antes de instalar.
8. POS dispara instalacao usando capacidades permitidas pelo Android e pelo fabricante do dispositivo.
9. Depois da instalacao, POS reporta nova versao no proximo heartbeat.

Regras:

- Actualizacao opcional permite adiar para outra hora.
- Actualizacao obrigatoria nao permite recarga nem validacao antes de instalar.
- O portal deve mostrar quem adiou, quando adiou e por quanto tempo.
- APK precisa ter checksum para evitar ficheiro corrompido ou adulterado.
- Rollout pode ser gradual por dispositivo, grupo ou versao.
- Publicacao, suspensao e retirada de APK devem gerar `AuditLog`.
- A app passageiro tambem pode usar o mesmo modelo de `AppRelease`, mas o foco inicial e o POS UROVO I9100 e SUNMI V2s.

## 14. SMS e Notificacoes

Usos da SMS API:

- OTP de criacao/login.
- Entrega de link/token de bilhete comprado sem conta.
- Confirmacao de recarga.
- Confirmacao de debito de viagem, se aplicavel.
- Alerta de bloqueio de cartao.
- Aviso de substituicao de cartao.
- Mensagens administrativas.

Entidade conceitual:

```text
SmsMessage
- id
- phone_number
- template
- body
- provider_reference
- status
- sent_at
- created_at
```

Regras:

- SMS de OTP tem validade curta.
- SMS financeira deve referenciar valor, data e saldo, quando permitido.
- Falha de SMS nao deve reverter pagamento confirmado.

## 15. Seguranca

Camadas obrigatorias:

- Autenticacao forte para portal.
- OTP para passageiro.
- OTP para reenvio ou consulta sensivel de bilhete comprado sem conta.
- RBAC para utilizadores administrativos.
- Permissoes separadas para financeiro, operacao e suporte.
- Device binding para POS.
- QR Codes assinados ou tokens opacos.
- Idempotencia em pagamentos, recargas, emissao de bilhetes e validacoes.
- Auditoria de operacoes administrativas.
- Bloqueio de conta, cartao e dispositivo.
- Bloqueio/revogacao de bilhete digital.
- Proteccao contra replay de tokens.
- Expiracao de tokens de viagem.
- Logs de callback de pagamento.
- Rate limiting em checkout convidado, OTP, consulta de bilhete e validacao.

Perfis administrativos:

- Admin geral.
- Gestor financeiro.
- Gestor operacional.
- Suporte.
- Agente POS.
- Auditor.

Operacoes sensiveis:

- Ajuste manual de saldo.
- Estorno.
- Bloqueio/desbloqueio de cartao.
- Substituicao de cartao.
- Activacao de dispositivo.
- Aprovacao/rejeicao de self-onboarding POS.
- Publicacao/suspensao de APK.
- Forcar actualizacao obrigatoria.
- Alteracao de tarifa.
- Cancelamento de viagem.
- Reenvio administrativo de bilhete sem conta.
- Associacao manual de compra convidado a uma conta.

Todas exigem auditoria.

## 16. Reconciliacao Financeira

O sistema precisa reconciliar:

- API de pagamentos vs `PaymentIntent`.
- `PaymentIntent` confirmado vs `WalletTransaction`.
- `PaymentIntent` confirmado vs `DigitalTravelPass` emitido.
- `GuestCheckout` pago vs bilhetes emitidos.
- Recargas POS vs agente/dispositivo.
- Debitos de viagens vs validacoes.
- Estornos vs transacoes originais.
- Saldo total em circulacao.

Relatorios financeiros:

- Recargas por dia.
- Recargas por canal.
- Recargas por provedor.
- Recargas por agente POS.
- Debitos por rota.
- Debitos por viagem.
- Falhas de pagamento.
- Pagamentos pendentes.
- Carteiras com saldo negativo, que idealmente devem ser zero.
- Ledger por passageiro/cartao.
- Vendas convidado por rota, viagem, canal e provedor.
- Passes pagos nao usados, expirados e reembolsados.

## 17. Auditoria

Entidade conceitual:

```text
AuditLog
- id
- actor
- action
- entity_type
- entity_id
- before
- after
- ip_address
- device
- created_at
```

Eventos auditaveis:

- Login administrativo.
- Activacao/bloqueio de POS.
- Criacao/edicao de tarifa.
- Criacao/cancelamento de viagem.
- Bloqueio de conta.
- Bloqueio/substituicao de cartao.
- Ajuste financeiro.
- Estorno.
- Reprocessamento de callback.
- Emissao, reenvio, cancelamento e consumo de bilhete convidado.

## 18. Apps Django Recomendadas

Organizacao inicial:

```text
config
core
accounts
users
passengers
guest_checkouts
wallets
cards
payments
sms
routes
fares
trips
devices
app_releases
pos
validations
reports
audit
organization
integrations
```

Notas:

- `wallets` deve conter o ledger.
- `payments` deve conter integracao com gateway e callbacks.
- `guest_checkouts` deve conter compras sem conta e emissao de bilhetes convidados.
- `validations` deve conter eventos de validacao e consumo de passes.
- `reports` deve preferir queries optimizadas e views/materialized views quando necessario.
- `audit` deve ser transversal.

## 19. API Inicial

Exemplos de endpoints:

```text
POST   /api/auth/login/
POST   /api/auth/otp/request/
POST   /api/auth/otp/verify/

GET    /api/passenger/me/
PATCH  /api/passenger/me/

POST   /api/guest-checkouts/
GET    /api/guest-checkouts/{reference}/
POST   /api/guest-checkouts/{reference}/resend/
POST   /api/guest-checkouts/{reference}/attach-to-account/

GET    /api/wallet/
GET    /api/wallet/transactions/
POST   /api/wallet/topups/

POST   /api/payments/intents/
POST   /api/payments/callbacks/{provider}/
GET    /api/payments/intents/{reference}/

GET    /api/routes/
GET    /api/stops/
GET    /api/trips/search/
POST   /api/fares/quote/

POST   /api/travel-passes/
GET    /api/travel-passes/
GET    /api/travel-passes/{id}/qr/
GET    /api/travel-passes/public/{token}/

POST   /api/cards/lookup/
POST   /api/cards/activate/
POST   /api/cards/link/
POST   /api/cards/block/
POST   /api/cards/replace/

POST   /api/devices/self-onboard/
GET    /api/devices/activation-status/{activation_code}/
POST   /api/admin/devices/{id}/approve/
POST   /api/admin/devices/{id}/reject/
PATCH  /api/admin/devices/{id}/configuration/

GET    /api/app-releases/check/
POST   /api/app-releases/{id}/defer/
POST   /api/app-releases/{id}/download-started/
POST   /api/app-releases/{id}/installed/
POST   /api/admin/app-releases/
PATCH  /api/admin/app-releases/{id}/publish/
PATCH  /api/admin/app-releases/{id}/suspend/

POST   /api/pos/sessions/
POST   /api/pos/card-topups/
POST   /api/pos/guest-ticket-sales/

POST   /api/validations/card/
POST   /api/validations/qr/
POST   /api/validations/guest-pass/

GET    /api/admin/reports/revenue/
GET    /api/admin/reports/validations/
GET    /api/admin/reconciliation/payments/
```

## 20. Backlog MVP

### Fase 1 - Fundacao

- Criar projecto Django/DRF.
- Criar projecto React + Vite.
- Criar base Flutter para app passageiro.
- Criar base Flutter para POS UROVO/SUNMI a partir do padrao ETICKETING.
- Replicar/adaptar `docker`, `scripts`, `Makefile`, `.env.example` e padrao de ambientes do ETICKETING.
- Configurar autenticacao.
- Configurar perfis e permissoes.
- Configurar PostgreSQL.
- Configurar padrao de ambientes.

### Fase 2 - Core Financeiro

- Criar passageiros.
- Criar checkout convidado para compra sem conta.
- Criar carteiras.
- Criar ledger.
- Criar emissao de `DigitalTravelPass` sem conta.
- Criar recargas.
- Integrar API de pagamentos.
- Implementar callbacks idempotentes.
- Integrar SMS API.
- Criar relatorio basico de transacoes.

### Fase 3 - Cartoes NFC e POS

- Registar cartoes NFC.
- Activar cartoes NFC.
- Implementar self-onboarding do POS UROVO I9100 e SUNMI V2s.
- Criar fila de aprovacoes de POS no portal.
- Configurar e aprovar POS no portal.
- Bloquear/rejeitar POS no portal.
- Implementar controlo de APKs do POS no portal.
- Implementar popup de nova versao no POS.
- Implementar opcao de adiar actualizacao opcional.
- Bloquear operacoes quando actualizacao obrigatoria estiver pendente.
- Consultar cartao no POS.
- Recarregar cartao no POS.
- Associar cartao a conta, quando o cliente quiser.
- Bloquear cartao.
- Criar device binding para UROVO/SUNMI.
- Integrar SDK UROVO e SDK SUNMI via platform channels.
- Mapear capacidades por modelo: NFC, QR, impressora, camera e instalacao de APK.

### Fase 4 - Rotas, Tarifas e Viagens

- CRUD de rotas.
- CRUD de paragens.
- Sequencia de paragens por rota.
- CRUD de tarifas.
- Quote de tarifa por origem/destino.
- CRUD de viagens.
- Pesquisa de viagens na app.

### Fase 5 - Pagamento de Viagem e Validacao

- Compra de `DigitalTravelPass`.
- Compra de bilhete sem conta via checkout convidado.
- QR Code/token na app.
- QR Code/token por SMS ou link seguro para convidado.
- Validacao online por QR.
- Validacao online por cartao.
- Pay-as-you-go com debito de saldo.
- Eventos de validacao.
- Relatorio de validacoes.

### Fase 6 - Portal Enterprise

- Dashboard financeiro.
- Dashboard operacional.
- Gestao de releases/APKs das apps.
- Relatorio de versoes instaladas nos POS.
- Reconciliacao de pagamentos.
- Relatorio por rota.
- Relatorio por agente.
- Relatorio por dispositivo.
- Auditoria.
- Exportacoes CSV/Excel.

## 21. Decisoes Tecnicas a Fechar

1. Tecnologia exacta do cartao fisico NFC: UID simples, MIFARE, DESFire ou outro.
2. Se o saldo fica apenas no servidor ou tambem gravado no cartao.
3. Provedor de pagamento inicial e formato exacto dos callbacks.
4. Provedor SMS e formato dos templates.
5. Se UROVO I9100 e SUNMI V2s farao apenas recarga/venda assistida ou tambem validacao.
6. Se havera viagem programada obrigatoria ou apenas rota/origem/destino.
7. Se o embarque sera cobrado na entrada, na saida ou por origem/destino pre-seleccionado.
8. Quais campos minimos serao obrigatorios para compra sem conta.
9. Politica de estornos e cancelamentos.
10. Politica de expiracao de passes digitais.
11. Se o POS sera associado a um agente fixo na aprovacao ou se qualquer agente autorizado podera fazer login em POS activo.
12. Politica de adiamento de actualizacoes opcionais: tempo maximo, numero maximo de adiamentos e horario recomendado.
13. Capacidades reais por lote/modelo de POS: NFC, scanner QR, impressora, camera, instalacao silenciosa e serial access.

## 22. Recomendacao de Implementacao

Para reduzir risco, a ordem recomendada e:

1. Implementar ledger e pagamentos antes de UI complexa.
2. Implementar checkout convidado para compra de bilhete sem conta.
3. Implementar recarga de carteira na app mobile.
4. Implementar cartao NFC e recarga no POS.
5. Implementar rotas/tarifas simples.
6. Implementar validacao online.
7. Expandir relatorios e reconciliacao.

O core financeiro deve ser tratado como parte mais critica do sistema. A UI pode evoluir, mas ledger, idempotencia, callbacks e auditoria precisam nascer correctos desde a primeira versao.
