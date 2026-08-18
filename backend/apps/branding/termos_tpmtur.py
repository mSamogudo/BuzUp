"""Termos e condicoes da TPM-TUR, transcritos do bilhete de embarque.

Fonte: `docs/Termos Condições .pdf` — o verso do bilhete impresso (Nº 001651),
que traz o texto em portugues e uma versao resumida em ingles. Transcreveu-se o
texto PORTUGUES, que e o mais completo dos dois: a versao inglesa condensa a
seccao da bagagem em cinco linhas onde a portuguesa tem doze, e e a portuguesa
que descreve o que acontece na fronteira.

Nao se corrigiu o sentido de nenhuma clausula. Foram corrigidas apenas gralhas
evidentes da digitalizacao ("hoa" -> "hora", "atrelado" mantido, "1.5 minutos"
-> "15 minutos", que o texto ingles confirma). Onde o original tem um ponto de
interrogacao a mais ("uma taxa de servico?"), retirou-se a pontuacao solta.

Isto e a semente. A partir daqui os termos vivem na base de dados e o cliente
edita-os no portal — sem isso, cada mudanca de politica passava por nos.
"""

VERSAO = "2026-08"

INTRO = (
    "Os passageiros embarcam sujeitos a certos requerimentos das nossas "
    "condições de embarque."
)

FECHO = "A TPM-TUR deseja-lhe uma viagem segura e confortável."

SECCOES = [
    {
        "title": "Bilhetes",
        "items": [
            "Os bilhetes não são transferíveis e são válidos para a pessoa a quem "
            "foram registados, na data e hora em que foram impressos.",
            "É da responsabilidade do passageiro que a informação correcta apareça "
            "no bilhete de embarque.",
            "Não é permitido aos passageiros interromper a sua viagem, a não ser que "
            "os bilhetes de embarque sejam impressos na tarifa apropriada para cada "
            "viagem individual.",
        ],
    },
    {
        "title": "Alterações",
        "items": [
            "Qualquer alteração do bilhete será considerada inválida.",
            "Qualquer alteração requer a impressão de um novo bilhete e uma taxa de serviço.",
        ],
    },
    {
        "title": "Cancelamentos",
        "items": [
            "Os cancelamentos devem ser feitos na agência onde o bilhete foi impresso.",
            "Se um cancelamento é feito 24 horas antes da partida, uma taxa de 20% "
            "irá ser cobrada.",
            "Se um cancelamento não é feito 24 horas antes da partida, o dinheiro do "
            "bilhete não será reembolsado.",
        ],
    },
    {
        "title": "Hora de partida",
        "items": [
            "Os passageiros terão de se apresentar no local de partida 15 minutos "
            "antes da hora apresentada no bilhete de embarque.",
            "Qualquer lugar livre 3 minutos antes da hora marcada de embarque será "
            "vendido aos passageiros em lista de espera.",
        ],
    },
    {
        "title": "Bagagem de passageiros",
        "items": [
            "É permitido a cada passageiro, grátis e ao seu cuidado, um item de "
            "bagagem pessoal que não exceda 100 cm x 80 cm x 40 cm em tamanho e "
            "20 kg de peso total.",
            "Cada passageiro terá de cumprir com os regulamentos das Alfândegas e "
            "Migração na fronteira. Isso inclui não transportar bens que excedam "
            "USD 50,00 como estipulado pelas alfândegas.",
            "Se tal acontecer, a TPM-TUR não será responsável nem obrigada a aguardar "
            "para que o passageiro possa resolver o seu problema. Se o passageiro "
            "ficar retido na fronteira para resolver o seu problema com as "
            "autoridades competentes, não deverá pedir reembolso ou reduções em "
            "tarifas por ter sido deixado na fronteira.",
            "Bens comerciais são estritamente proibidos no autocarro.",
            "Se houver algum atraso na fronteira de 30 minutos devido a transgressão "
            "por parte dos passageiros da cláusula de bens comerciais, a TPM-TUR, no "
            "seu próprio julgamento, deixará o passageiro e este não será reembolsado.",
            "A TPM-TUR reserva o direito de recusar qualquer bagagem que não cumpra "
            "com estas condições.",
            "Itens de grande dimensão deverão ser transportados no atrelado.",
            "Bagagem não acompanhada não será transportada.",
            "A TPM-TUR não será responsável pela perda, estragos ou roubo da bagagem "
            "do passageiro, bagagem de mão ou pessoais.",
        ],
    },
    {
        "title": "Fumar",
        "items": ["Fumar é proibido em todos os autocarros."],
    },
    {
        "title": "Crianças não acompanhadas",
        "items": [
            "Crianças não acompanhadas inferiores a 12 anos não serão transportadas.",
        ],
    },
    {
        "title": "Álcool",
        "items": [
            "A TPM-TUR não permitirá o consumo de álcool nos seus veículos, nem irá "
            "transportar nenhum passageiro que embarque intoxicado, e reserva o "
            "direito de admissão em todos os seus autocarros.",
        ],
    },
    {
        "title": "Animais",
        "items": [
            "Nenhum animal será transportado, com excepção de um cão-guia treinado "
            "acompanhado de uma pessoa com deficiência visual, sujeito à apresentação "
            "da documentação relevante de um veterinário que permita atravessar a "
            "fronteira.",
        ],
    },
    {
        "title": "Condições gerais",
        "items": [
            "A TPM-TUR fará o esforço de manter os horários publicados, mas os "
            "serviços poderão ser afectados pelas condições de estrada, tempo e "
            "outros factores fora do controlo da TPM-TUR. A TPM-TUR não aceitará "
            "responsabilidade legal de qualquer custo que ocorra aos passageiros "
            "durante essas situações.",
            "A TPM-TUR reserva o direito de rever os lugares marcados sem aviso "
            "prévio e substituir os veículos por outros de standard diferente dos "
            "enumerados.",
            "Não é permitido aos passageiros desembarcar na paragem. Nenhum "
            "desembarque nas rotas planeadas será permitido.",
            "A TPM-TUR reserva o direito de cancelar os seus serviços por qualquer "
            "razão sem prévio aviso. Nenhuma responsabilidade legal será aceite "
            "pelas perdas dos passageiros que tenham feito reservas.",
            "Todas as tarifas e horários estarão sujeitos a mudanças sem prévio aviso.",
        ],
    },
]

# Contactos do bilhete de embarque.
EMPRESA = {
    "company_name": "TPM-TUR (PTY) — Transporte e Turismo",
    "company_address": "Rua da Resistência, Parcela 24, 1º Andar, Maputo — Moçambique",
    "company_website": "www.tpmtur.co.mz",
    "support_email": "info@tpmtur.co.mz",
    "support_phone": "+258 21 307 554",
    "contact_phones": [
        "+258 21 307 554",
        "+258 21 307 552",
        "+258 84 314 2681",
        "+258 84 314 2001",
        "+258 86 200 2211",
    ],
}


# --- Versao inglesa, tal como impressa no mesmo bilhete ---------------------
#
# O verso do bilhete traz as duas. A inglesa e mais curta de proposito — o
# operador condensou-a — e nao e uma traducao literal da portuguesa. Fica como
# esta impressa: e o texto que a TPM-TUR ja entrega ao passageiro, e reescreve-lo
# em ingles "melhor" seria publicar termos que ninguem aprovou.

INTRO_EN = "Passengers are subject to the following terms:"

FECHO_EN = "We wish you a safe and pleasant journey."

SECCOES_EN = [
    {
        "title": "Tickets",
        "items": [
            "Non-transferable, valid only for the named person, date, and time.",
            "It is the passenger's responsibility to confirm that the ticket "
            "information is correct.",
            "Stopovers are only allowed with the appropriate fare.",
        ],
    },
    {
        "title": "Changes",
        "items": [
            "Any change makes the ticket invalid.",
            "A new ticket and service fee are required for modifications.",
        ],
    },
    {
        "title": "Cancellations",
        "items": [
            "Must be made at the issuing agency.",
            "Cancellations 24+ hours before departure are subject to a 20% fee.",
            "No refunds for late cancellations.",
        ],
    },
    {
        "title": "Departure Time",
        "items": [
            "Passengers must arrive 15 minutes before departure.",
            "Unclaimed seats 3 minutes before will be reassigned.",
        ],
    },
    {
        "title": "Luggage",
        "items": [
            "One personal item per passenger (max. 100x80x40 cm, 20 kg).",
            "Customs rules apply; goods over USD 50 and commercial items are prohibited.",
            "TPM-TUR is not responsible for border delays, and no refund will be "
            "issued if a passenger is left behind.",
            "Oversized items go in the trailer.",
            "Unaccompanied luggage is not accepted.",
            "No liability for lost or damaged items.",
        ],
    },
    {
        "title": "Smoking",
        "items": ["Not allowed on board."],
    },
    {
        "title": "Unaccompanied Minors",
        "items": ["Children under 12 must be accompanied by an adult."],
    },
    {
        "title": "Alcohol",
        "items": [
            "Alcohol consumption is prohibited.",
            "Intoxicated passengers will not be transported.",
            "Right of admission is reserved.",
        ],
    },
    {
        "title": "Animals",
        "items": [
            "Animals are not allowed, except certified guide dogs with proper "
            "documentation.",
        ],
    },
    {
        "title": "General Conditions",
        "items": [
            "Delays may occur due to factors beyond TPM-TUR's control.",
            "The company may change vehicles or seating without notice, and cancel "
            "services if needed, with no liability.",
            "Fares and schedules are subject to change.",
        ],
    },
]
