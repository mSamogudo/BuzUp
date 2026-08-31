/**
 * Conteudo PT/EN portado verbatim dos prototipos do handoff.
 *
 * Fonte: docs/design-handoff/design/{Acesso,Erros,Ecra Compra} BusUp.dc.html
 * (objectos PT e EN). Regra do plano: nenhum texto novo inventado.
 *
 * Estes ecras nao sao geridos pelo CMS — o CMS cobre o site de marketing
 * (landing, precos, contactos). Acesso, erros e compra sao produto.
 */
export const SCREEN_COPY = {
  "acesso": {
    "PT": {
      "badge": "Acesso seguro · portal BusUp",
      "h1": "Entre no portal da sua operação.",
      "lead": "Venda, validação, frota e receita no mesmo sítio. O acesso é por conta nominal — cada movimento fica registado com o nome de quem o fez.",
      "leadShort": "Venda, validação, frota e receita no mesmo sítio.",
      "facts": [
        "Sessão por conta nominal, com auditoria",
        "Acesso por SMS para passageiros",
        "Suporte local em Moçambique"
      ],
      "modes": [
        [
          "staff",
          "Equipa",
          "Equipa"
        ],
        [
          "otp",
          "Acesso por SMS",
          "SMS"
        ],
        [
          "register",
          "Nova conta",
          "Conta"
        ]
      ],
      "eyebrow": {
        "staff": "Acesso seguro",
        "otp": "Acesso por SMS",
        "register": "Nova conta"
      },
      "titles": {
        "staff": "Utilizador e senha",
        "otpPhone": "Receber código por SMS",
        "otpCode": "Introduza o código",
        "register": "Criar conta de passageiro"
      },
      "leads": {
        "staff": "Para pessoal do operador: direcção, tesouraria, agentes e motoristas.",
        "otpPhone": "Para passageiros. Enviamos um código de 6 dígitos para o seu número.",
        "otpCode": "Enviámos um código de 6 dígitos para o 84 123 4567.",
        "register": "Precisa apenas do nome e de um número de telemóvel activo."
      },
      "user": "Utilizador",
      "userPh": "nome de utilizador ou telefone",
      "password": "Senha",
      "keep": "Manter sessão iniciada",
      "forgot": "Esqueci a senha",
      "resetTitle": "Reposição de senha",
      "resetLead": "Indique o telefone associado à sua conta. Se existir, recebe uma SMS com a nova senha.",
      "resetSubmit": "Enviar",
      "enter": "Entrar",
      "phone": "Telemóvel",
      "otpNote": "Vai receber um código de 6 dígitos por SMS. Não partilhe o código com ninguém.",
      "sendCode": "Enviar código",
      "resendIn": "Reenviar código em 00:42",
      "changeNumber": "Mudar de número",
      "confirmCode": "Confirmar e entrar",
      "fullName": "Nome completo",
      "fullNamePh": "Como está no documento",
      "terms": "Aceito os termos de utilização e o tratamento dos meus dados para emissão de bilhetes.",
      "createAccount": "Criar conta",
      "help": "Problemas a entrar?",
      "poweredBy": "Desenvolvido por",
      "booting": "A preparar o portal…",
      "sessionTitle": "A validar a sua sessão",
      "sessionLead": "Estamos a confirmar as permissões da conta e a carregar a operação.",
      "sessionSteps": [
        "Credenciais confirmadas",
        "A carregar permissões",
        "A preparar o painel"
      ]
    },
    "EN": {
      "badge": "Secure access · BusUp portal",
      "h1": "Sign in to your operation.",
      "lead": "Sales, validation, fleet and revenue in one place. Access is by named account — every action is recorded with the name behind it.",
      "leadShort": "Sales, validation, fleet and revenue in one place.",
      "facts": [
        "Named accounts with full audit trail",
        "SMS access for passengers",
        "Local support in Mozambique"
      ],
      "modes": [
        [
          "staff",
          "Staff",
          "Staff"
        ],
        [
          "otp",
          "SMS access",
          "SMS"
        ],
        [
          "register",
          "New account",
          "Account"
        ]
      ],
      "eyebrow": {
        "staff": "Secure sign in",
        "otp": "SMS access",
        "register": "New account"
      },
      "titles": {
        "staff": "Username and password",
        "otpPhone": "Get a code by SMS",
        "otpCode": "Enter the code",
        "register": "Create a passenger account"
      },
      "leads": {
        "staff": "For operator staff: management, treasury, agents and drivers.",
        "otpPhone": "For passengers. We send a 6-digit code to your number.",
        "otpCode": "We sent a 6-digit code to 84 123 4567.",
        "register": "All you need is a name and an active mobile number."
      },
      "user": "Username",
      "userPh": "username or phone",
      "password": "Password",
      "keep": "Keep me signed in",
      "forgot": "Forgot password",
      "resetTitle": "Password reset",
      "resetLead": "Enter the phone linked to your account. If it exists, you get an SMS with the new password.",
      "resetSubmit": "Send",
      "enter": "Sign in",
      "phone": "Mobile",
      "otpNote": "You will get a 6-digit code by SMS. Never share the code with anyone.",
      "sendCode": "Send code",
      "resendIn": "Resend code in 00:42",
      "changeNumber": "Change number",
      "confirmCode": "Confirm and sign in",
      "fullName": "Full name",
      "fullNamePh": "As printed on the document",
      "terms": "I accept the terms of use and the processing of my data to issue tickets.",
      "createAccount": "Create account",
      "help": "Trouble signing in?",
      "poweredBy": "Powered by",
      "booting": "Preparing the portal…",
      "sessionTitle": "Checking your session",
      "sessionLead": "We are confirming the account permissions and loading the operation.",
      "sessionSteps": [
        "Credentials confirmed",
        "Loading permissions",
        "Preparing the dashboard"
      ]
    }
  },
  "erros": {
    "PT": {
      "help": "Ajuda",
      "statusPage": "Estado dos serviços",
      "poweredBy": "Desenvolvido por",
      "errors": [
        {
          "key": "404",
          "code": "404",
          "tone": "info",
          "pill": "Página não encontrada",
          "where": "Site público e portal",
          "title": "Esta página mudou de sítio.",
          "lead": "O endereço que abriu já não existe ou foi escrito com um erro. As páginas principais continuam todas disponíveis.",
          "cta1": "Voltar ao início",
          "cta2": "Comprar bilhete",
          "hints": [
            [
              "Percursos e horários",
              "Consulte as partidas do dia na página de compra."
            ],
            [
              "Preços",
              "A tabela por tipo de operação está na página de preços."
            ],
            [
              "Falar connosco",
              "sales@updigital.co.mz · dias úteis, 08h–17h."
            ]
          ],
          "ref": "ref. 404 · /rota-antiga · 04 Ago 2026, 10:12"
        },
        {
          "key": "401",
          "code": "401",
          "tone": "info",
          "pill": "Sessão terminada",
          "where": "Portal e app POS",
          "title": "A sua sessão expirou.",
          "lead": "Por segurança, terminamos a sessão depois de um período sem actividade. Volte a entrar para continuar de onde estava.",
          "cta1": "Entrar de novo",
          "cta2": "Ir para o início",
          "hints": [
            [
              "Nada se perdeu",
              "O trabalho por gravar fica no dispositivo até voltar a entrar."
            ],
            [
              "Acesso por SMS",
              "Passageiros entram com o código enviado por SMS."
            ],
            [
              "Senha esquecida",
              "Peça a reposição no ecrã de entrada."
            ]
          ],
          "ref": "ref. 401 · sessão 8f21c4 · 04 Ago 2026, 10:12"
        },
        {
          "key": "403",
          "code": "403",
          "tone": "warn",
          "pill": "Sem permissão",
          "where": "Portal",
          "title": "A sua conta não tem acesso a esta área.",
          "lead": "O acesso é definido pelo papel da conta. Se precisa desta área para o seu trabalho, peça ao administrador da operação.",
          "cta1": "Voltar ao painel",
          "cta2": "Pedir acesso",
          "hints": [
            [
              "O que vê",
              "Cada papel abre apenas as áreas do seu trabalho."
            ],
            [
              "Quem autoriza",
              "O administrador da operação altera papéis no portal."
            ],
            [
              "Registo",
              "Tentativas de acesso ficam na auditoria."
            ]
          ],
          "ref": "ref. 403 · conta agente-14 · /financeiro"
        },
        {
          "key": "500",
          "code": "500",
          "tone": "bad",
          "pill": "Erro do servidor",
          "where": "Site público e portal",
          "title": "Alguma coisa falhou do nosso lado.",
          "lead": "O pedido não chegou a ser concluído e nada foi cobrado. A equipa já recebeu o alerta com a referência abaixo.",
          "cta1": "Tentar de novo",
          "cta2": "Falar com o suporte",
          "hints": [
            [
              "Pagamentos",
              "Nenhum valor é cobrado quando o pedido falha."
            ],
            [
              "Bilhetes emitidos",
              "Continuam válidos e disponíveis no telemóvel."
            ],
            [
              "Referência",
              "Indique-a ao suporte para acelerar a resposta."
            ]
          ],
          "ref": "ref. 500 · incidente INC-2026-0804-17"
        },
        {
          "key": "503",
          "code": "503",
          "tone": "warn",
          "pill": "Manutenção programada",
          "where": "Portal",
          "title": "Estamos a actualizar a plataforma.",
          "lead": "A janela de manutenção termina às 06h00. A validação a bordo continua a funcionar sem ligação e sincroniza quando voltarmos.",
          "cta1": "Ver estado dos serviços",
          "cta2": "Avisar-me quando voltar",
          "hints": [
            [
              "Validação a bordo",
              "A app POS valida offline durante a janela."
            ],
            [
              "Venda online",
              "Fica indisponível até às 06h00."
            ],
            [
              "Duração prevista",
              "40 minutos · 05h20 às 06h00 (CAT)."
            ]
          ],
          "ref": "ref. 503 · janela 05h20–06h00 CAT"
        },
        {
          "key": "offline",
          "code": "⚡",
          "tone": "bad",
          "pill": "Sem ligação",
          "where": "App POS e telemóvel",
          "title": "O dispositivo está sem Internet.",
          "lead": "Continua a validar bilhetes offline: as leituras ficam guardadas no aparelho e sobem assim que houver rede.",
          "cta1": "Tentar ligar de novo",
          "cta2": "Continuar offline",
          "hints": [
            [
              "Validações guardadas",
              "18 leituras por sincronizar neste aparelho."
            ],
            [
              "Venda",
              "A venda de bilhetes precisa de rede."
            ],
            [
              "Última sincronização",
              "hoje, 09h41."
            ]
          ],
          "ref": "ref. net · 18 registos por sincronizar"
        }
      ]
    },
    "EN": {
      "help": "Help",
      "statusPage": "Service status",
      "poweredBy": "Powered by",
      "errors": [
        {
          "key": "404",
          "code": "404",
          "tone": "info",
          "pill": "Page not found",
          "where": "Public site and portal",
          "title": "This page has moved.",
          "lead": "The address you opened no longer exists or was mistyped. Every main page is still available.",
          "cta1": "Back to home",
          "cta2": "Buy a ticket",
          "hints": [
            [
              "Routes and times",
              "Check today's departures on the purchase page."
            ],
            [
              "Pricing",
              "The table by operation type is on the pricing page."
            ],
            [
              "Talk to us",
              "sales@updigital.co.mz · weekdays, 08:00–17:00."
            ]
          ],
          "ref": "ref. 404 · /old-route · 4 Aug 2026, 10:12"
        },
        {
          "key": "401",
          "code": "401",
          "tone": "info",
          "pill": "Session ended",
          "where": "Portal and POS app",
          "title": "Your session has expired.",
          "lead": "For safety we end the session after a period without activity. Sign in again to pick up where you were.",
          "cta1": "Sign in again",
          "cta2": "Go to home",
          "hints": [
            [
              "Nothing was lost",
              "Unsaved work stays on the device until you sign in."
            ],
            [
              "SMS access",
              "Passengers sign in with the code sent by SMS."
            ],
            [
              "Forgot password",
              "Request a reset on the sign-in screen."
            ]
          ],
          "ref": "ref. 401 · session 8f21c4 · 4 Aug 2026, 10:12"
        },
        {
          "key": "403",
          "code": "403",
          "tone": "warn",
          "pill": "No permission",
          "where": "Portal",
          "title": "Your account cannot open this area.",
          "lead": "Access follows the account role. If you need this area for your work, ask the operation's administrator.",
          "cta1": "Back to dashboard",
          "cta2": "Request access",
          "hints": [
            [
              "What you see",
              "Each role opens only the areas of its work."
            ],
            [
              "Who authorises",
              "The administrator changes roles in the portal."
            ],
            [
              "Record",
              "Access attempts are kept in the audit log."
            ]
          ],
          "ref": "ref. 403 · account agent-14 · /finance"
        },
        {
          "key": "500",
          "code": "500",
          "tone": "bad",
          "pill": "Server error",
          "where": "Public site and portal",
          "title": "Something failed on our side.",
          "lead": "The request never completed and nothing was charged. The team already has the alert with the reference below.",
          "cta1": "Try again",
          "cta2": "Contact support",
          "hints": [
            [
              "Payments",
              "No amount is charged when a request fails."
            ],
            [
              "Issued tickets",
              "Remain valid and available on the phone."
            ],
            [
              "Reference",
              "Give it to support to speed up the answer."
            ]
          ],
          "ref": "ref. 500 · incident INC-2026-0804-17"
        },
        {
          "key": "503",
          "code": "503",
          "tone": "warn",
          "pill": "Scheduled maintenance",
          "where": "Portal",
          "title": "We are updating the platform.",
          "lead": "The maintenance window ends at 06:00. Onboard validation keeps working offline and syncs when we are back.",
          "cta1": "See service status",
          "cta2": "Notify me when back",
          "hints": [
            [
              "Onboard validation",
              "The POS app validates offline during the window."
            ],
            [
              "Online sales",
              "Unavailable until 06:00."
            ],
            [
              "Expected duration",
              "40 minutes · 05:20 to 06:00 (CAT)."
            ]
          ],
          "ref": "ref. 503 · window 05:20–06:00 CAT"
        },
        {
          "key": "offline",
          "code": "⚡",
          "tone": "bad",
          "pill": "No connection",
          "where": "POS app and phone",
          "title": "This device has no Internet.",
          "lead": "Keep validating offline: scans are stored on the device and upload as soon as there is a network.",
          "cta1": "Try to reconnect",
          "cta2": "Continue offline",
          "hints": [
            [
              "Stored validations",
              "18 scans waiting to sync on this device."
            ],
            [
              "Sales",
              "Selling tickets needs a network."
            ],
            [
              "Last sync",
              "today, 09:41."
            ]
          ],
          "ref": "ref. net · 18 records waiting to sync"
        }
      ]
    }
  },
  "compra": {
    "PT": {
      "back": "Voltar ao site",
      "kicker": "Bilhetes interurbanos",
      "title": "Compre a sua viagem",
      "sub": "Escolha a data, o lugar e receba o bilhete no telemóvel.",
      "steps": [
        "Viagem",
        "Partida",
        "Lugares",
        "Passageiros",
        "Pagamento"
      ],
      "searchH": "Para onde vai?",
      "searchLead": "Indique o percurso, a data da viagem e quantos bilhetes precisa.",
      "origin": "Origem",
      "destination": "Destino",
      "date": "Data da viagem",
      "pax": "Passageiros",
      "paxTwo": "2 passageiros",
      "searchBtn": "Procurar partidas",
      "popular": "Percursos frequentes",
      "tripsH": "Partidas disponíveis",
      "twoTickets": "2 bilhetes",
      "perPerson": "por pessoa",
      "changeSearch": "Alterar pesquisa",
      "otherDay": "Escolher outro dia",
      "notifyMe": "Avisar-me se abrir lugar",
      "fullNotice": "Todas as partidas desta data estão esgotadas. Há lugares em 07 de Agosto a partir das 06:30.",
      "seatsH": "Escolha os 2 lugares",
      "busFront": "Frente do autocarro",
      "otherTrip": "Outra partida",
      "seatFree": "Livre",
      "seatPicked": "Seleccionado",
      "seatTaken": "Ocupado",
      "paxH": "Quem viaja?",
      "paxLead": "O bilhete é nominal. Em viagens internacionais o documento é conferido na fronteira.",
      "filled": "Preenchido",
      "passengerTwo": "Passageiro 2",
      "fullName": "Nome completo",
      "namePlaceholder": "Como está no documento",
      "document": "Documento",
      "number": "Número",
      "backBtn": "Voltar",
      "continueBtn": "Continuar",
      "payH": "Pagamento",
      "payLead": "Confirme os dados e escolha como quer pagar.",
      "totalDue": "Total a pagar",
      "method": "Forma de pagamento",
      "payPhone": "Telemóvel para pagamento",
      "emailOpt": "Email (opcional)",
      "emailPlaceholder": "para receber o bilhete",
      "payBtn": "Pagar 500,00 MZN",
      "errTitle": "Não foi possível concluir a compra",
      "errBody": "Não conseguimos falar com o serviço de pagamento. Nada foi cobrado. Tente de novo dentro de instantes.",
      "retry": "Tentar de novo",
      "changeMethod": "Mudar forma de pagamento",
      "doneH": "Bilhete emitido",
      "doneBody": "Pagamento confirmado. Enviámos o link do bilhete por SMS para o 84 123 4567 — guarde o PDF no telemóvel e apresente o QR ao embarcar.",
      "charged": "Valor cobrado",
      "qrSlot": "QR do bilhete\n(gerado no servidor)",
      "downloadTicket": "Descarregar bilhete",
      "newPurchase": "Nova compra",
      "help": "Precisa de ajuda?",
      "portalLogin": "Entrar no portal",
      "poweredBy": "Desenvolvido por",
      "soldOut": "Esgotado",
      "dateLong": "quinta-feira, 6 de Agosto de 2026",
      "walletNote": "Vamos cobrar via M-Pesa no 84 123 4567. Vai receber um pedido de PIN neste número.",
      "sumRoute": "Percurso",
      "sumDeparture": "Partida",
      "sumPax": "Passageiros",
      "sumUnit": "2 × 250,00 MZN",
      "tRef": "Referência",
      "tSeats": "Lugares",
      "tWhen": "Partida",
      "tRouteK": "Percurso"
    },
    "EN": {
      "back": "Back to site",
      "kicker": "Intercity tickets",
      "title": "Buy your trip",
      "sub": "Pick the date and seat, and get the ticket on your phone.",
      "steps": [
        "Trip",
        "Departure",
        "Seats",
        "Passengers",
        "Payment"
      ],
      "searchH": "Where are you going?",
      "searchLead": "Tell us the route, the travel date and how many tickets you need.",
      "origin": "From",
      "destination": "To",
      "date": "Travel date",
      "pax": "Passengers",
      "paxTwo": "2 passengers",
      "searchBtn": "Find departures",
      "popular": "Frequent routes",
      "tripsH": "Available departures",
      "twoTickets": "2 tickets",
      "perPerson": "per person",
      "changeSearch": "Change search",
      "otherDay": "Pick another day",
      "notifyMe": "Notify me if a seat opens",
      "fullNotice": "Every departure on this date is sold out. Seats are available on 7 August from 06:30.",
      "seatsH": "Choose your 2 seats",
      "busFront": "Front of the bus",
      "otherTrip": "Another departure",
      "seatFree": "Free",
      "seatPicked": "Selected",
      "seatTaken": "Taken",
      "paxH": "Who is travelling?",
      "paxLead": "Tickets are personal. On international trips the document is checked at the border.",
      "filled": "Complete",
      "passengerTwo": "Passenger 2",
      "fullName": "Full name",
      "namePlaceholder": "As printed on the document",
      "document": "Document",
      "number": "Number",
      "backBtn": "Back",
      "continueBtn": "Continue",
      "payH": "Payment",
      "payLead": "Check the details and choose how you want to pay.",
      "totalDue": "Total due",
      "method": "Payment method",
      "payPhone": "Phone for payment",
      "emailOpt": "Email (optional)",
      "emailPlaceholder": "to receive the ticket",
      "payBtn": "Pay 500.00 MZN",
      "errTitle": "We could not complete the purchase",
      "errBody": "We could not reach the payment service. Nothing was charged. Please try again in a moment.",
      "retry": "Try again",
      "changeMethod": "Change payment method",
      "doneH": "Ticket issued",
      "doneBody": "Payment confirmed. We sent the ticket link by SMS to 84 123 4567 — keep the PDF on your phone and show the QR when boarding.",
      "charged": "Amount charged",
      "qrSlot": "Ticket QR\n(generated server-side)",
      "downloadTicket": "Download ticket",
      "newPurchase": "New purchase",
      "help": "Need help?",
      "portalLogin": "Sign in to the portal",
      "poweredBy": "Powered by",
      "soldOut": "Sold out",
      "dateLong": "Thursday, 6 August 2026",
      "walletNote": "We will charge M-Pesa on 84 123 4567. You will get a PIN request on this number.",
      "sumRoute": "Route",
      "sumDeparture": "Departure",
      "sumPax": "Passengers",
      "sumUnit": "2 × 250.00 MZN",
      "tRef": "Reference",
      "tSeats": "Seats",
      "tWhen": "Departure",
      "tRouteK": "Route"
    }
  }
} as const;

export type ScreenLocale = "PT" | "EN";
