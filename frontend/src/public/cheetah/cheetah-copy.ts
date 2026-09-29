import { useLandingPrefs, type Lang } from "../landing/useLandingPrefs";

/**
 * Texto do site institucional da Cheetah Express, em português e inglês.
 *
 * Mesma forma que `tpm-copy.ts` e `booking.i18n.ts`, pelo mesmo motivo: as
 * chaves são curtas e descritivas, e não a frase. Usar a frase como chave
 * parece prático até ao dia em que se corrige uma gralha e se perde a tradução.
 *
 * O INGLÊS É A LÍNGUA DE ORIGEM desta empresa — metade da rota é sul-africana
 * e o site oficial é inglês-primeiro. O português aqui NÃO é o do site oficial:
 * a versão `/pt/` de cheetah-express.com é tradução automática para português
 * do Brasil ("ônibus", "você", "Transportador" para *shuttles*). Está reescrito
 * em português de Moçambique.
 *
 * DUAS CORRECÇÕES AO SITE OFICIAL, deliberadas:
 *
 *  1. TOFO, e não "Tofu". O sítio é a Praia do Tofo, em Inhambane. O site
 *     oficial escreve "Tofu" — grafia corrente do lado sul-africano, mas errada
 *     em Moçambique, e este site é lido dos dois lados.
 *
 *  2. Os DIAS de partida. O site oficial contradiz-se: o texto de apresentação
 *     diz que o Tofo–Maputo–Nelspruit parte "todas as terças" e o Tofo–Maputo é
 *     "todas as sextas", mas os quadros de horários dizem "terças e sextas" nos
 *     dois. Segui os QUADROS, que são o documento mais específico. É o único
 *     facto deste site que não pude resolver sozinho —
 *     PRECISA DE CONFIRMAÇÃO DA CHEETAH EXPRESS.
 *
 * As PARAGENS não se traduzem: são lugares físicos, e quem as lê em inglês tem
 * de as conseguir dizer a um motorista de chapa em Maputo.
 */

/* A FORMA DE UM PERCURSO, escrita e nao inferida.
 *
 * O `EN` e declarado como `typeof PT`, e sem um tipo proprio os campos vazios
 * dos percursos de sentido unico — `nota: ""`, `precos: []` — inferiam tipos
 * diferentes dos dos outros e o ingles deixava de encaixar. Escrever a forma
 * resolve isso e serve de documentacao: quem acrescentar um percurso ve aqui
 * o que tem de preencher.
 *
 * `tipo` e o que distingue um SENTIDO de um DIA. Nao e cosmetica: chamar
 * "volta" ao segundo dia de uma viagem com dormida ensinaria ao passageiro
 * que pode apanha-lo para regressar, e nao pode. */
type Sentido = "ida" | "volta" | "dia1" | "dia2" | "unico";

type Painel = {
  tipo: Sentido;
  t: string;
  /** Paragem, local e hora. A duracao do painel NAO se escreve aqui: e a
   *  diferenca entre a primeira e a ultima hora, e a pagina calcula-a, para
   *  nao poder divergir dos dados. */
  linhas: [string, string, string][];
};

type Percurso = {
  id: string;
  nome: string;
  /** Curto, para o quadro-resumo. */
  dias: string;
  /** Inteiro, para o cabecalho do cartao. */
  diasLongo: string;
  duracao: string;
  preco: string;
  /** `true` quando o preco mostrado e o mais baixo de varios. */
  desde: boolean;
  /** Vazio quando nao ha nada a avisar. */
  nota: string;
  dormida: string;
  /** O detalhe dos precos, so quando ha mais do que um. */
  precos: string[];
  paineis: Painel[];
};


const PT = {
  nav: {
    inicio: "Início",
    horarios: "Horários",
    contactos: "Contactos",
    termos: "Condições",
    entrar: "Entrar",
    entrarPortal: "Entrar no portal",
    comprar: "Comprar bilhete",
    saltar: "Saltar para o conteúdo",
    abrirMenu: "Abrir menu",
    fecharMenu: "Fechar menu",
    idioma: "Idioma",
    mudarIdioma: "Mudar idioma",
    temaClaro: "Modo claro",
    temaEscuro: "Modo escuro",
    paginaInicial: "Cheetah Express — página inicial",
    logoAlt: "Cheetah Express — transporte entre Moçambique e Nelspruit",
  },

  rodape: {
    tagline: "Transporte regular entre Moçambique e Nelspruit há mais de dez anos. Maputo, Matola, Tofo e África do Sul — seguro, fiável e rápido.",
    viagens: "Viagens",
    app: "App do passageiro",
    empresa: "Empresa",
    contactos: "Contactos",
    tecnologia: "Tecnologia",
    desenvolvidoPor: "Desenvolvido por",
    direitos: "Cheetah Express · Transporte de passageiros.",
  },

  comum: {
    pedirOrcamento: "Pedir orçamento",
    falarConnosco: "Falar connosco",
    comprarBilhete: "Comprar bilhete",
    caminho: "Caminho",
  },

  heroBusca: {
    titulo: "Encontre a sua viagem",
    tipoViagem: "Tipo de viagem",
    soIda: "Só ida",
    idaVolta: "Ida e volta",
    origem: "Origem",
    destino: "Destino",
    ida: "Ida",
    volta: "Volta",
    trocar: "Trocar origem e destino",
    procurar: "Procurar viagens",
    destinosAVenda: "Destinos à venda:",
    semPartidas: "Sem partidas à venda",
    deOnde: "De onde parte?",
    paraOnde: "Para onde vai?",
    passageiros: "Passageiros",
    passageiro1: "passageiro",
    passageiroN: "passageiros",
    dataVazia: "dd/mm/aaaa",
    erroPercurso: "Indique a origem e o destino.",
    erroMesmoLugar: "A origem e o destino não podem ser o mesmo lugar.",
    erroData: "Escolha a data de ida.",
    erroVolta: "Escolha a data de regresso.",
  },

  inicio: {
    meta: {
      titulo: "Cheetah Express — Maputo, Tofo e Nelspruit",
      descricao: "Transporte regular entre Moçambique e Nelspruit. Compre o bilhete online, consulte horários e preços das ligações Maputo–Nelspruit e Tofo–Maputo.",
    },
    hero: {
      badge: "Há mais de 10 anos na estrada",
      h1: "Seguro, fiável",
      h1destaque: "e rápido.",
      lead: "O seu transporte n.º 1 entre Nelspruit e Moçambique. Compre o bilhete online e embarque — Maputo, Matola, Tofo e África do Sul, todos os dias.",
      fotoAlt: "Carrinha da frota Cheetah Express, com o passageiro e a praia ao fundo",
    },
    provas: {
      kicker: "Porquê connosco",
      h2: "O que encontra a bordo",
      itens: [
        { t: "Totalmente climatizado", p: "Toda a frota tem ar condicionado — a viagem entre Maputo e Nelspruit faz-se com calor lá fora, não cá dentro." },
        { t: "Mais de 10 anos", p: "Uma década no transporte de passageiros nesta rota. Conhecemos a estrada, a fronteira e as horas a que ela enche." },
        { t: "Motoristas experientes", p: "Condução segura e equipa que fala a língua dos dois lados da fronteira. Sente-se e descanse." },
        { t: "Wi-Fi a bordo", p: "Viagens longas passam melhor ligadas. Wi-Fi em todas as viaturas, sem custo." },
      ],
    },
    servicos: {
      kicker: "Serviços",
      h2: "Três formas de viajar connosco",
      itens: [
        {
          id: "diario",
          etiqueta: "Diário",
          t1: "Shuttle",
          t2: "diário",
          sub: "Transferes diários entre Nelspruit e Maputo",
          p: "Ligação diária, de segunda a domingo, pela N4. Parte do Mundo's e do Shoprite da Matola e chega ao Ilanga Mall e ao Riverside Mall.",
          extra: "Inclui o DROP & SHOP, lançado com a Go Nelspruit e o Ilanga Mall: quem viaja de Maputo para Nelspruit é deixado à porta do centro comercial.",
          cta: "Ver horários",
        },
        {
          id: "mocambique",
          etiqueta: "Com dormida",
          t1: "Shuttles de",
          t2: "Moçambique",
          sub: "Do Tofo e de Maputo para Nelspruit",
          p: "Do Tofo a Nelspruit com dormida em Maputo, no Fatima's Backpackers. Nos dois sentidos, e também só Tofo–Maputo ou Maputo–Tofo.",
          extra: "O preço inclui a dormida — quarto privado ou dormitório, à sua escolha.",
          cta: "Ver horários",
        },
        {
          id: "excursoes",
          etiqueta: "À medida",
          t1: "Excursões",
          t2: "à medida",
          sub: "De OR Tambo ou de qualquer aeroporto para Moçambique",
          p: "Pacotes à medida para grupos, com alojamento incluído se quiser. Transporte para eventos e grupos, nacionais ou estrangeiros.",
          extra: "Diga-nos quantos são e para onde vão, e montamos a viagem.",
          cta: "Falar connosco",
        },
      ],
      botao: "Ver horários e preços",
    },
    rota: {
      kicker: "A rota",
      h2: "Onde paramos",
      lead: "As paragens fixas dos nossos percursos, de sul para norte.",
      lados: [
        { t: "Moçambique", paragens: ["Praia do Tofo — Mercado do Tofo", "Tofo — Supermercado Babalaza", "Maputo — Fatima's Backpackers, Av. Mao Tse Tung", "Maputo — Restaurante Mundo's, Av. Eduardo Mondlane", "Matola — Shoprite, portão principal"] },
        { t: "África do Sul", paragens: ["Komatipoort — Estação de serviço Engen", "Nelspruit — Ilanga Mall, entrada Mopani", "Nelspruit — Riverside Mall"] },
      ],
    },
    frota: {
      kicker: "A frota",
      h2: "As viaturas que o levam",
      /* Só se diz o que a marca já diz de si própria — o ar condicionado e o
         Wi-Fi vêm das provas do site oficial. Lugares e anos de matrícula não
         se inventam. */
      lead: "Minibus e carrinhas para grupos de todos os tamanhos. Toda a frota é climatizada e tem Wi-Fi a bordo.",
    },
    parceiros: {
      kicker: "Parceiros",
      h2: "Quem anda connosco",
      lead: "Organizações com quem trabalhamos nos dois lados da fronteira.",
    },
    cta: {
      h2: "Pronto para viajar?",
      p: "Compre o bilhete online e receba-o no telemóvel. Para grupos ou excursões à medida, fale connosco.",
    },
  },

  horarios: {
    meta: {
      titulo: "Horários e preços — Cheetah Express",
      descricao: "Horários das ligações Maputo–Nelspruit, Tofo–Maputo–Nelspruit e Maputo–Tofo da Cheetah Express, com paragens, horas e preços.",
    },
    migalha: "Horários",
    titulo: "Horários e preços",
    descricao: "Todos os nossos percursos, com as paragens, as horas e o preço de ida. Os preços estão em rands e em meticais — a conversão é aproximada e acompanha o câmbio do dia.",

    /* O quadro-resumo, antes de tudo. Quem chega aqui quer saber em que dias
       pode ir, quanto demora e quanto custa; cinco cartões parecidos obrigavam
       a ler os cinco para responder. */
    resumo: {
      h2: "Os cinco percursos, de relance",
      legenda: "Resumo dos percursos: dias, duração e preço",
      percurso: "Percurso",
      dias: "Dias",
      duracao: "Duração",
      preco: "Preço, só ida",
    },

    colunas: { paragem: "Paragem", hora: "Hora" },
    legendaQuadro: "paragens e horas",
    parte: "Parte",
    chega: "Chega",
    cerca: "cerca de",
    desde: "desde",
    precoRotulo: "Preço",
    precoDesdeRotulo: "Preço, desde",
    precoDetalhe: "Preço por pessoa, só ida",

    /* O SENTIDO NÃO PODE DEPENDER DA COR. Cada distintivo leva a palavra e,
       nos que têm direcção, uma seta; quem não distinga o vermelho do preto lê
       "IDA" e "VOLTA" e vê as setas apontarem para lados opostos.
       DIA 1 e DIA 2 são de outra família de propósito: não são sentidos, são a
       mesma viagem partida em dois dias, e confundi-los seria ensinar ao
       passageiro que pode apanhar o segundo painel para voltar. */
    sentidos: { ida: "Ida", volta: "Volta", dia1: "Dia 1", dia2: "Dia 2", unico: "Sentido único" },

    aviso: "As horas são as de partida previstas, e os tempos de viagem são a diferença entre elas. A travessia da fronteira de Ressano Garcia pode acrescentar tempo à viagem, sobretudo em fins-de-semana e feriados — recomendamos que conte com isso ao marcar ligações.",

    percursos: [
      {
        id: "maputo-nelspruit",
        nome: "Maputo ↔ Nelspruit",
        dias: "Todos os dias",
        diasLongo: "Todos os dias, de segunda a domingo",
        duracao: "4h30 a 5h",
        preco: "R450 · ≈ 1 800 MT",
        desde: false,
        nota: "Dois serviços por dia, um em cada sentido — escolha o painel do sentido em que viaja.",
        dormida: "",
        precos: [],
        paineis: [
          { tipo: "ida", t: "Maputo → Nelspruit", linhas: [
            ["Maputo", "Restaurante Mundo's, Av. Eduardo Mondlane", "05:30"],
            ["Matola", "Shoprite, portão principal", "06:00"],
            ["Nelspruit", "Ilanga Mall, entrada Mopani", "09:30"],
            ["Nelspruit", "Riverside Mall", "10:00"],
          ]},
          { tipo: "volta", t: "Nelspruit → Maputo", linhas: [
            ["Nelspruit", "Riverside Mall", "15:30"],
            ["Nelspruit", "Ilanga Mall, entrada Mopani", "16:00"],
            ["Matola", "Shoprite, portão principal", "20:00"],
            ["Maputo", "Restaurante Mundo's, Av. Eduardo Mondlane", "20:30"],
          ]},
        ],
      },
      {
        id: "tofo-nelspruit",
        nome: "Tofo → Maputo → Nelspruit",
        dias: "Terças e sextas",
        diasLongo: "Terças e sextas",
        duracao: "2 dias, com dormida",
        preco: "R1 200 · ≈ 5 400 MT",
        desde: true,
        nota: "Não são dois sentidos: é uma viagem só, partida em dois dias.",
        dormida: "A mesma viagem, em dois dias: dorme-se no Fatima's Backpackers, em Maputo, entre o Dia 1 e o Dia 2.",
        precos: [
          "Quarto privado no Fatima's: R1 500 · ≈ 6 750 MT",
          "Dormitório no Fatima's: R1 200 · ≈ 5 400 MT",
        ],
        paineis: [
          { tipo: "dia1", t: "Tofo → Maputo", linhas: [
            ["Tofo", "Mercado do Tofo", "05:30"],
            ["Tofo", "Supermercado Babalaza", "06:00"],
            ["Maputo", "Fatima's Backpackers, Av. Mao Tse Tung, e Mundo's", "15:30"],
          ]},
          { tipo: "dia2", t: "Maputo → Nelspruit", linhas: [
            ["Maputo", "Fatima's Backpackers, Av. Mao Tse Tung", "05:10"],
            ["Maputo", "Restaurante Mundo's", "05:30"],
            ["Nelspruit", "Ilanga Mall, entrada Mopani", "09:30"],
            ["Nelspruit", "Riverside Mall", "10:00"],
          ]},
        ],
      },
      {
        id: "nelspruit-tofo",
        nome: "Nelspruit → Maputo → Tofo",
        dias: "Domingos e quartas",
        diasLongo: "Domingos e quartas",
        duracao: "2 dias, com dormida",
        preco: "R1 200 · ≈ 5 400 MT",
        desde: true,
        nota: "Não são dois sentidos: é uma viagem só, partida em dois dias.",
        dormida: "A mesma viagem, em dois dias: dorme-se no Fatima's Backpackers, em Maputo, entre o Dia 1 e o Dia 2.",
        precos: [
          "Quarto privado no Fatima's: R1 500 · ≈ 6 750 MT",
          "Dormitório no Fatima's: R1 200 · ≈ 5 400 MT",
        ],
        paineis: [
          { tipo: "dia1", t: "Nelspruit → Maputo", linhas: [
            ["Nelspruit", "Riverside Mall", "15:30"],
            ["Nelspruit", "Ilanga Mall, entrada Mopani", "16:00"],
            ["Komatipoort", "Estação de serviço Engen", "17:00"],
            ["Maputo", "Fatima's Backpackers, Av. Mao Tse Tung, e Mundo's", "20:00"],
          ]},
          { tipo: "dia2", t: "Maputo → Tofo", linhas: [
            ["Maputo", "Fatima's Backpackers, Av. Mao Tse Tung", "06:30"],
            ["Maputo", "Restaurante Mundo's", "07:00"],
            ["Tofo", "Mercado do Tofo", "15:30"],
          ]},
        ],
      },
      {
        id: "tofo-maputo",
        nome: "Tofo → Maputo",
        dias: "Terças e sextas",
        diasLongo: "Terças e sextas",
        duracao: "cerca de 10h",
        preco: "R600 · ≈ 2 500 MT",
        desde: false,
        nota: "",
        dormida: "",
        precos: [],
        paineis: [
          { tipo: "unico", t: "Tofo → Maputo", linhas: [
            ["Tofo", "Mercado do Tofo", "05:30"],
            ["Tofo", "Supermercado Babalaza", "06:00"],
            ["Maputo", "Fatima's Backpackers, Av. Mao Tse Tung", "15:30"],
          ]},
        ],
      },
      {
        id: "maputo-tofo",
        nome: "Maputo → Tofo",
        dias: "Segundas e quintas",
        diasLongo: "Segundas e quintas",
        duracao: "cerca de 9h",
        preco: "2 500 MT",
        desde: false,
        nota: "",
        dormida: "",
        precos: [],
        paineis: [
          { tipo: "unico", t: "Maputo → Tofo", linhas: [
            ["Maputo", "Fatima's Backpackers, Av. Mao Tse Tung", "06:30"],
            ["Tofo", "Praia do Tofo", "15:30"],
          ]},
        ],
      },
    ] as Percurso[],
    cta: { h2: "Já sabe quando viaja?", p: "Escolha o percurso e a data e compre o bilhete online — chega-lhe ao telemóvel." },
  },
  contactos: {
    meta: {
      titulo: "Contactos — Cheetah Express",
      descricao: "Fale com a Cheetah Express: reservas, grupos e excursões à medida entre Moçambique e Nelspruit.",
    },
    migalha: "Contactos",
    titulo: "Fale connosco",
    descricao: "Para reservas, grupos ou excursões à medida. Respondemos em português e inglês.",
    cartoes: {
      reservas: { t: "Reservas", p: "Bilhetes, alterações e dúvidas sobre uma viagem marcada." },
      geral: { t: "Geral", p: "Tudo o resto — parcerias, grupos, faturação." },
      escritorio: { t: "Escritório", p: "Maputo, Moçambique · 1100" },
    },
    form: {
      h3: "Pedido de contacto",
      lead: "Preencha e nós respondemos. O botão abre o seu programa de email com a mensagem já escrita.",
      nome: "Nome",
      telefone: "Telefone",
      email: "Email",
      empresa: "Empresa (opcional)",
      assunto: "Assunto",
      assuntoVazio: "Escolha o assunto",
      assuntoGenerico: "Pedido de contacto",
      assuntos: {
        bilhete: "Bilhete ou reserva",
        grupo: "Transporte de grupo",
        excursao: "Excursão à medida",
        aeroporto: "Transfer de aeroporto",
        outro: "Outro assunto",
      },
      mensagem: "Mensagem",
      mensagemDica: "Diga-nos as datas, o percurso e quantas pessoas viajam.",
      submeter: "Preparar email",
      aviso: "Se o email não abriu sozinho, escreva-nos directamente para {email}.",
      corpo: { nome: "Nome", contacto: "Contacto", email: "Email", empresa: "Empresa", naoIndicada: "não indicada" },
    },
  },

  termos: {
    meta: {
      titulo: "Condições de transporte — Cheetah Express",
      descricao: "Condições de transporte da Cheetah Express: reservas, embarque, bagagem, travessia de fronteira, alterações e cancelamentos.",
    },
    migalha: "Condições",
    titulo: "Condições de transporte",
    descricao: "As regras da viagem: o que precisa de trazer, a que horas estar na paragem, e o que acontece se os planos mudarem.",
    porAprovar: "Texto provisório, por aprovar pela Cheetah Express. Não substitui as condições contratuais em vigor.",
    seccoes: [
      { h: "Reservas e bilhetes", p: [
        "A reserva confirma-se com o pagamento. O bilhete é enviado para o telemóvel e é esse que apresenta ao embarcar — em ecrã ou impresso.",
        "O bilhete é pessoal e vale para a data, o percurso e a pessoa nele indicados.",
      ]},
      { h: "Embarque", p: [
        "Esteja na paragem 30 minutos antes da hora de partida. A viatura parte à hora marcada; quem chega depois perde o lugar e o bilhete não é reembolsado.",
        "As paragens são as que constam do horário. Não há recolha nem largada fora delas, salvo em serviços contratados à medida.",
      ]},
      { h: "Documentos e travessia de fronteira", p: [
        "Os percursos entre Moçambique e a África do Sul atravessam a fronteira de Ressano Garcia / Lebombo. Cada passageiro é responsável por ter passaporte válido e, se lhe for exigido, visto.",
        "Menores de idade precisam de documentação própria para atravessar a fronteira. Informe-se junto das autoridades antes de viajar.",
        "A Cheetah Express não pode responder por um passageiro a quem as autoridades de fronteira recusem a passagem, e nesse caso não há reembolso da viagem.",
      ]},
      { h: "Bagagem", p: [
        "Cada passageiro pode levar uma mala de porão e uma bagagem de mão. Volumes acima disso dependem do espaço disponível e podem ter custo adicional.",
        "Não se transportam mercadorias para revenda, animais vivos nem bens perigosos.",
        "Objectos de valor, documentos e aparelhos electrónicos viajam com o passageiro, e não no porão.",
      ]},
      { h: "Alterações e cancelamentos", p: [
        "Pode alterar a data da viagem até 48 horas antes da partida, sujeito a lugar disponível.",
        "Cancelamentos comunicados com mais de 48 horas de antecedência dão direito a reembolso, com dedução dos encargos. Abaixo desse prazo não há reembolso.",
        "Se formos nós a cancelar a viagem, tem direito a remarcação sem custo ou ao reembolso integral.",
      ]},
      { h: "Atrasos", p: [
        "As horas indicadas são de partida prevista. Trânsito, estado da estrada e o tempo de espera na fronteira podem atrasar a chegada.",
        "Recomendamos que não marque voos ou ligações com pouca folga face à hora prevista de chegada.",
      ]},
      { h: "Preços", p: [
        "Os preços são indicados em rands sul-africanos e em meticais. O valor em meticais é aproximado e acompanha o câmbio; o valor cobrado é o que aparece no momento da compra.",
        "Nos percursos com dormida, o preço inclui o alojamento indicado no horário.",
      ]},
      { h: "Crianças", p: [
        "Crianças viajam sempre acompanhadas por um adulto responsável e ocupam lugar próprio, com bilhete.",
      ]},
      { h: "Comportamento a bordo", p: [
        "Não é permitido fumar nem consumir bebidas alcoólicas dentro da viatura.",
        "A equipa pode recusar o embarque a quem ponha em risco a segurança ou o conforto dos restantes passageiros.",
      ]},
      { h: "Contacto", p: [
        "Dúvidas sobre estas condições ou sobre uma viagem marcada: {email}.",
      ]},
    ],
  },
};

const EN: typeof PT = {
  nav: {
    inicio: "Home",
    horarios: "Timetable",
    contactos: "Contact",
    termos: "Conditions",
    entrar: "Sign in",
    entrarPortal: "Sign in to the portal",
    comprar: "Buy a ticket",
    saltar: "Skip to content",
    abrirMenu: "Open menu",
    fecharMenu: "Close menu",
    idioma: "Language",
    mudarIdioma: "Change language",
    temaClaro: "Light mode",
    temaEscuro: "Dark mode",
    paginaInicial: "Cheetah Express — home",
    logoAlt: "Cheetah Express — transport between Mozambique and Nelspruit",
  },

  rodape: {
    tagline: "Scheduled transport between Mozambique and Nelspruit for over ten years. Maputo, Matola, Tofo and South Africa — safe, reliable and fast.",
    viagens: "Travel",
    app: "Passenger app",
    empresa: "Company",
    contactos: "Contact",
    tecnologia: "Technology",
    desenvolvidoPor: "Built by",
    direitos: "Cheetah Express · Passenger transport.",
  },

  comum: {
    pedirOrcamento: "Request a quote",
    falarConnosco: "Get in touch",
    comprarBilhete: "Buy a ticket",
    caminho: "Path",
  },

  heroBusca: {
    titulo: "Find your trip",
    tipoViagem: "Trip type",
    soIda: "One way",
    idaVolta: "Return",
    origem: "From",
    destino: "To",
    ida: "Departure",
    volta: "Return",
    trocar: "Swap origin and destination",
    procurar: "Search trips",
    destinosAVenda: "On sale:",
    semPartidas: "No departures on sale",
    deOnde: "Where from?",
    paraOnde: "Where to?",
    passageiros: "Passengers",
    passageiro1: "passenger",
    passageiroN: "passengers",
    dataVazia: "dd/mm/yyyy",
    erroPercurso: "Please choose where you are travelling from and to.",
    erroMesmoLugar: "Origin and destination cannot be the same place.",
    erroData: "Please choose the outbound date.",
    erroVolta: "Please choose the return date.",
  },

  inicio: {
    meta: {
      titulo: "Cheetah Express — Maputo, Tofo and Nelspruit",
      descricao: "Scheduled transport between Mozambique and Nelspruit. Book online and check timetables and fares for Maputo–Nelspruit and Tofo–Maputo.",
    },
    hero: {
      badge: "Over 10 years on the road",
      h1: "Safe, reliable",
      h1destaque: "and fast.",
      lead: "Your no. 1 shuttle between Nelspruit and Mozambique. Book online and board — Maputo, Matola, Tofo and South Africa, every day.",
      fotoAlt: "A Cheetah Express shuttle, with a passenger and the beach behind",
    },
    provas: {
      kicker: "Why travel with us",
      h2: "What you get on board",
      itens: [
        { t: "Fully air-conditioned", p: "Every vehicle in the fleet is air-conditioned — the Maputo–Nelspruit run is hot outside, not inside." },
        { t: "Over 10 years", p: "A decade carrying passengers on this route. We know the road, the border, and the hours it fills up." },
        { t: "Experienced drivers", p: "Safe driving and a crew that speaks the language on both sides of the border. Sit back and relax." },
        { t: "Wi-Fi on board", p: "Long trips go better connected. Wi-Fi in every vehicle, at no extra cost." },
      ],
    },
    servicos: {
      kicker: "Services",
      h2: "Three ways to travel with us",
      itens: [
        {
          id: "diario",
          etiqueta: "Daily",
          t1: "Daily",
          t2: "shuttles",
          sub: "Daily transfers between Nelspruit and Maputo",
          p: "Daily service, Monday to Sunday, along the N4. Departs from Mundo's and the Matola Shoprite, arriving at Ilanga Mall and Riverside Mall.",
          extra: "Includes DROP & SHOP, launched with Go Nelspruit and Ilanga Mall: travelling from Maputo to Nelspruit drops you at the mall door.",
          cta: "Booking times",
        },
        {
          id: "mocambique",
          etiqueta: "With overnight",
          t1: "Mozambique",
          t2: "shuttles",
          sub: "From Tofo and Maputo to Nelspruit",
          p: "Tofo to Nelspruit with an overnight stop in Maputo, at Fatima's Backpackers. Both directions, plus Tofo–Maputo and Maputo–Tofo on their own.",
          extra: "The fare includes the overnight stay — private room or dormitory, your choice.",
          cta: "Booking times",
        },
        {
          id: "excursoes",
          etiqueta: "Tailor-made",
          t1: "Custom",
          t2: "tours",
          sub: "From OR Tambo or any airport into Mozambique",
          p: "Tailor-made group packages, with lodging included if you want it. Transport for events and groups, local or international.",
          extra: "Tell us how many you are and where you are going, and we build the trip.",
          cta: "Get in touch",
        },
      ],
      botao: "See timetables and fares",
    },
    rota: {
      kicker: "The route",
      h2: "Where we stop",
      lead: "The fixed stops on our services, south to north.",
      lados: [
        { t: "Mozambique", paragens: ["Praia do Tofo — Tofo Market", "Tofo — Babalaza Supermarket", "Maputo — Fatima's Backpackers, Av. Mao Tse Tung", "Maputo — Mundo's restaurant, Av. Eduardo Mondlane", "Matola — Shoprite, main gates"] },
        { t: "South Africa", paragens: ["Komatipoort — Engen service station", "Nelspruit — Ilanga Mall, Mopani entrance", "Nelspruit — Riverside Mall"] },
      ],
    },
    frota: {
      kicker: "The fleet",
      h2: "The vehicles that take you",
      lead: "Minibuses and vans for groups of every size. The whole fleet is air-conditioned and has Wi-Fi on board.",
    },
    parceiros: {
      kicker: "Partners",
      h2: "Who travels with us",
      lead: "Organisations we work with on both sides of the border.",
    },
    cta: {
      h2: "Ready to travel?",
      p: "Book online and get your ticket on your phone. For groups or tailor-made tours, get in touch.",
    },
  },

  horarios: {
    meta: {
      titulo: "Timetable and fares — Cheetah Express",
      descricao: "Cheetah Express timetables for Maputo–Nelspruit, Tofo–Maputo–Nelspruit and Maputo–Tofo, with stops, times and fares.",
    },
    migalha: "Timetable",
    titulo: "Timetable and fares",
    descricao: "All our services, with stops, times and the one-way fare. Fares are shown in rands and meticais — the conversion is approximate and tracks the day's rate.",

    resumo: {
      h2: "All five services at a glance",
      legenda: "Summary of services: days, journey time and fare",
      percurso: "Service",
      dias: "Days",
      duracao: "Journey time",
      preco: "Fare, one way",
    },

    colunas: { paragem: "Stop", hora: "Time" },
    legendaQuadro: "stops and times",
    parte: "Departs",
    chega: "Arrives",
    cerca: "about",
    desde: "from",
    precoRotulo: "Fare",
    precoDesdeRotulo: "Fare, from",
    precoDetalhe: "Fare per person, one way",

    sentidos: { ida: "Outbound", volta: "Return", dia1: "Day 1", dia2: "Day 2", unico: "One way" },

    aviso: "Times shown are scheduled departures, and journey times are the difference between them. Crossing the Ressano Garcia / Lebombo border can add to the journey, especially at weekends and on public holidays — please allow for it when planning connections.",

    percursos: [
      {
        id: "maputo-nelspruit",
        nome: "Maputo ↔ Nelspruit",
        dias: "Every day",
        diasLongo: "Every day, Monday to Sunday",
        duracao: "4h30 to 5h",
        preco: "R450 · ≈ MT 1,800",
        desde: false,
        nota: "Two services a day, one in each direction — pick the panel for the way you are travelling.",
        dormida: "",
        precos: [],
        paineis: [
          { tipo: "ida", t: "Maputo → Nelspruit", linhas: [
            ["Maputo", "Mundo's restaurant, Av. Eduardo Mondlane", "05:30"],
            ["Matola", "Shoprite, main gates", "06:00"],
            ["Nelspruit", "Ilanga Mall, Mopani entrance", "09:30"],
            ["Nelspruit", "Riverside Mall", "10:00"],
          ]},
          { tipo: "volta", t: "Nelspruit → Maputo", linhas: [
            ["Nelspruit", "Riverside Mall", "15:30"],
            ["Nelspruit", "Ilanga Mall, Mopani entrance", "16:00"],
            ["Matola", "Shoprite, main gates", "20:00"],
            ["Maputo", "Mundo's restaurant, Av. Eduardo Mondlane", "20:30"],
          ]},
        ],
      },
      {
        id: "tofo-nelspruit",
        nome: "Tofo → Maputo → Nelspruit",
        dias: "Tuesdays and Fridays",
        diasLongo: "Tuesdays and Fridays",
        duracao: "2 days, overnight included",
        preco: "R1,200 · ≈ MT 5,400",
        desde: true,
        nota: "These are not two directions: it is one journey, split over two days.",
        dormida: "One journey over two days: you stay overnight at Fatima's Backpackers in Maputo, between Day 1 and Day 2.",
        precos: [
          "Private room at Fatima's: R1,500 · ≈ MT 6,750",
          "Dorm bed at Fatima's: R1,200 · ≈ MT 5,400",
        ],
        paineis: [
          { tipo: "dia1", t: "Tofo → Maputo", linhas: [
            ["Tofo", "Tofo market", "05:30"],
            ["Tofo", "Babalaza supermarket", "06:00"],
            ["Maputo", "Fatima's Backpackers, Av. Mao Tse Tung, and Mundo's", "15:30"],
          ]},
          { tipo: "dia2", t: "Maputo → Nelspruit", linhas: [
            ["Maputo", "Fatima's Backpackers, Av. Mao Tse Tung", "05:10"],
            ["Maputo", "Mundo's restaurant", "05:30"],
            ["Nelspruit", "Ilanga Mall, Mopani entrance", "09:30"],
            ["Nelspruit", "Riverside Mall", "10:00"],
          ]},
        ],
      },
      {
        id: "nelspruit-tofo",
        nome: "Nelspruit → Maputo → Tofo",
        dias: "Sundays and Wednesdays",
        diasLongo: "Sundays and Wednesdays",
        duracao: "2 days, overnight included",
        preco: "R1,200 · ≈ MT 5,400",
        desde: true,
        nota: "These are not two directions: it is one journey, split over two days.",
        dormida: "One journey over two days: you stay overnight at Fatima's Backpackers in Maputo, between Day 1 and Day 2.",
        precos: [
          "Private room at Fatima's: R1,500 · ≈ MT 6,750",
          "Dorm bed at Fatima's: R1,200 · ≈ MT 5,400",
        ],
        paineis: [
          { tipo: "dia1", t: "Nelspruit → Maputo", linhas: [
            ["Nelspruit", "Riverside Mall", "15:30"],
            ["Nelspruit", "Ilanga Mall, Mopani entrance", "16:00"],
            ["Komatipoort", "Engen service station", "17:00"],
            ["Maputo", "Fatima's Backpackers, Av. Mao Tse Tung, and Mundo's", "20:00"],
          ]},
          { tipo: "dia2", t: "Maputo → Tofo", linhas: [
            ["Maputo", "Fatima's Backpackers, Av. Mao Tse Tung", "06:30"],
            ["Maputo", "Mundo's restaurant", "07:00"],
            ["Tofo", "Tofo market", "15:30"],
          ]},
        ],
      },
      {
        id: "tofo-maputo",
        nome: "Tofo → Maputo",
        dias: "Tuesdays and Fridays",
        diasLongo: "Tuesdays and Fridays",
        duracao: "about 10h",
        preco: "R600 · ≈ MT 2,500",
        desde: false,
        nota: "",
        dormida: "",
        precos: [],
        paineis: [
          { tipo: "unico", t: "Tofo → Maputo", linhas: [
            ["Tofo", "Tofo market", "05:30"],
            ["Tofo", "Babalaza supermarket", "06:00"],
            ["Maputo", "Fatima's Backpackers, Av. Mao Tse Tung", "15:30"],
          ]},
        ],
      },
      {
        id: "maputo-tofo",
        nome: "Maputo → Tofo",
        dias: "Mondays and Thursdays",
        diasLongo: "Mondays and Thursdays",
        duracao: "about 9h",
        preco: "MT 2,500",
        desde: false,
        nota: "",
        dormida: "",
        precos: [],
        paineis: [
          { tipo: "unico", t: "Maputo → Tofo", linhas: [
            ["Maputo", "Fatima's Backpackers, Av. Mao Tse Tung", "06:30"],
            ["Tofo", "Tofo beach", "15:30"],
          ]},
        ],
      },
    ] as Percurso[],
    cta: { h2: "Know when you are travelling?", p: "Pick the service and the date and buy online — the ticket reaches your phone." },
  },
  contactos: {
    meta: {
      titulo: "Contact — Cheetah Express",
      descricao: "Talk to Cheetah Express: bookings, groups and tailor-made tours between Mozambique and Nelspruit.",
    },
    migalha: "Contact",
    titulo: "Get in touch",
    descricao: "For bookings, groups or tailor-made tours. We answer in English and Portuguese.",
    cartoes: {
      reservas: { t: "Bookings", p: "Tickets, changes and questions about a booked trip." },
      geral: { t: "General", p: "Everything else — partnerships, groups, invoicing." },
      escritorio: { t: "Office", p: "Maputo, Mozambique · 1100" },
    },
    form: {
      h3: "Contact request",
      lead: "Fill this in and we will reply. The button opens your email app with the message already written.",
      nome: "Name",
      telefone: "Phone",
      email: "Email",
      empresa: "Company (optional)",
      assunto: "Subject",
      assuntoVazio: "Choose a subject",
      assuntoGenerico: "Contact request",
      assuntos: {
        bilhete: "Ticket or booking",
        grupo: "Group transport",
        excursao: "Tailor-made tour",
        aeroporto: "Airport transfer",
        outro: "Something else",
      },
      mensagem: "Message",
      mensagemDica: "Tell us the dates, the route and how many people are travelling.",
      submeter: "Prepare email",
      aviso: "If your email app did not open, write to us directly at {email}.",
      corpo: { nome: "Name", contacto: "Phone", email: "Email", empresa: "Company", naoIndicada: "not given" },
    },
  },

  termos: {
    meta: {
      titulo: "Conditions of carriage — Cheetah Express",
      descricao: "Cheetah Express conditions of carriage: bookings, boarding, luggage, border crossing, changes and cancellations.",
    },
    migalha: "Conditions",
    titulo: "Conditions of carriage",
    descricao: "The rules of the trip: what to bring, what time to be at the stop, and what happens when plans change.",
    porAprovar: "Draft text, pending approval by Cheetah Express. It does not replace the contractual terms in force.",
    seccoes: [
      { h: "Bookings and tickets", p: [
        "A booking is confirmed on payment. The ticket is sent to your phone and that is what you show when boarding — on screen or printed.",
        "The ticket is personal and valid for the date, route and person named on it.",
      ]},
      { h: "Boarding", p: [
        "Be at the stop 30 minutes before departure. The vehicle leaves on time; anyone arriving later loses their seat and the fare is not refunded.",
        "Stops are those listed in the timetable. There is no pick-up or drop-off elsewhere, except on tailor-made charters.",
      ]},
      { h: "Documents and border crossing", p: [
        "Services between Mozambique and South Africa cross the Ressano Garcia / Lebombo border. Each passenger is responsible for holding a valid passport and, where required, a visa.",
        "Minors need their own documentation to cross the border. Please check with the authorities before travelling.",
        "Cheetah Express cannot be held responsible where border authorities refuse a passenger entry, and in that case the fare is not refunded.",
      ]},
      { h: "Luggage", p: [
        "Each passenger may carry one hold bag and one piece of hand luggage. Anything beyond that depends on available space and may carry an extra charge.",
        "We do not carry goods for resale, live animals or dangerous goods.",
        "Valuables, documents and electronics travel with the passenger, not in the hold.",
      ]},
      { h: "Changes and cancellations", p: [
        "You may change your travel date up to 48 hours before departure, subject to availability.",
        "Cancellations notified more than 48 hours in advance are refundable, less charges. Below that window there is no refund.",
        "If we cancel the service, you are entitled to rebook at no cost or to a full refund.",
      ]},
      { h: "Delays", p: [
        "Times shown are scheduled departures. Traffic, road conditions and waiting time at the border can delay arrival.",
        "We recommend not booking flights or connections with little slack against the scheduled arrival time.",
      ]},
      { h: "Fares", p: [
        "Fares are shown in South African rands and in meticais. The metical figure is approximate and tracks the exchange rate; the amount charged is the one shown at the time of purchase.",
        "On services with an overnight stop, the fare includes the accommodation stated in the timetable.",
      ]},
      { h: "Children", p: [
        "Children always travel accompanied by a responsible adult and occupy their own seat, with a ticket.",
      ]},
      { h: "Conduct on board", p: [
        "Smoking and drinking alcohol are not permitted inside the vehicle.",
        "The crew may refuse boarding to anyone putting the safety or comfort of other passengers at risk.",
      ]},
      { h: "Contact", p: [
        "Questions about these conditions or about a booked trip: {email}.",
      ]},
    ],
  },
};

const DICIONARIOS: Record<Lang, typeof PT> = { pt: PT, en: EN };

/** Texto do site da Cheetah Express na língua escolhida, mais o selector.
 *  A língua é a mesma preferência partilhada por todo o site público. */
export function useCheetahCopy() {
  const { lang, setLang } = useLandingPrefs();
  return { t: DICIONARIOS[lang], lang, setLang };
}
