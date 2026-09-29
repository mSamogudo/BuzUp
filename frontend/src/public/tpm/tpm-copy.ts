import { useLandingPrefs, type Lang } from "../landing/useLandingPrefs";

/**
 * Texto do site institucional da TPM-TUR, em português e inglês.
 *
 * Mesma forma que `booking.i18n.ts`, pelo mesmo motivo: as chaves são curtas e
 * descritivas, e não a frase portuguesa. Usar a frase como chave parece
 * prático até ao dia em que se corrige uma gralha e se perde a tradução.
 *
 * O QUE A TRADUÇÃO NÃO PODE DECIDIR SOZINHA. Há aqui texto que é da empresa e
 * não meu: a missão, a visão, os oito valores e os nomes das nove políticas
 * oficiais. Traduzi-los é escrever uma versão inglesa de um documento
 * institucional — o inglês que está aqui é uma tradução de trabalho e precisa
 * do aval da TPM-TUR antes de ir para o ar. Está marcado com OFICIAL onde
 * acontece.
 *
 * A morada NÃO se traduz: é um endereço físico, e quem o lê em inglês tem de
 * o conseguir dizer a um motorista de táxi em Maputo.
 */

const PT = {
  nav: {
    servicos: "Serviços",
    frota: "Nossa frota",
    sobre: "Sobre nós",
    politicas: "Nossas políticas",
    perguntas: "Perguntas",
    contactos: "Contactos",
    entrar: "Entrar",
    entrarPortal: "Entrar no portal",
    comprar: "Comprar bilhete",
    saltar: "Saltar para o conteúdo",
    abrirMenu: "Abrir menu",
    fecharMenu: "Fechar menu",
    idioma: "Idioma",
    mudarIdioma: "mudar para inglês",
    temaClaro: "Modo claro",
    temaEscuro: "Modo escuro",
    inicio: "Início",
    paginaInicial: "TPM-TUR — página inicial",
    logoAlt: "TPM-TUR, S.A. — Transporte e Turismo",
  },

  rodape: {
    tagline: "Empresa moçambicana de transporte e turismo. Ligamos pessoas aos seus destinos — passageiros, empresas e grupos.",
    viagens: "Viagens",
    app: "App do passageiro",
    empresa: "Empresa",
    contactos: "Contactos",
    tecnologia: "Tecnologia",
    desenvolvidoPor: "Desenvolvido por",
    direitos: "TPM-TUR, S.A. · Transporte e Turismo. Tecnologia BusUp · UpDigital.",
  },

  comum: {
    pedirOrcamento: "Pedir orçamento",
    verServicos: "Ver os serviços",
    verFrota: "Ver a frota",
    consultarDisponibilidade: "Consultar disponibilidade",
    caminho: "Caminho",
  },

  heroBusca: {
    titulo: "Encontre a sua viagem",
    tipoViagem: "Tipo de viagem",
    soIda: "Só ida",
    idaVolta: "Ida e volta",
    origem: "Origem",
    destino: "Destino",
    data: "Data",
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
      titulo: "TPM-TUR — Transporte e Turismo",
      descricao: "TPM-TUR, S.A. — transporte e turismo em Moçambique. Compre o bilhete online, conheça a frota e os serviços para empresas e grupos.",
    },
    hero: {
      badge: "TPM-TUR, S.A. — Transporte e Turismo",
      h1: "A sua próxima viagem",
      h1b: "começa",
      h1destaque: "aqui.",
      lead: "Compre o bilhete online, escolha o seu lugar e embarque sem filas. Mais perto do seu destino — viaje com a TPM-TUR.",
      fotoAlt: "Autocarros da frota TPM-TUR",
      grupo: "Precisa de transporte para um grupo?",
      todasPartidas: "Ver todas as partidas",
    },
    confianca: [
      { t: "Parceria público-privada", p: "EMTPM · ETM · Sky Rent, Lda." },
      { t: "Bilhete no telemóvel", p: "Sem papel, sem filas ao balcão." },
      { t: "Lugar marcado", p: "Escolha o seu lugar no mapa do autocarro." },
    ],
    passos: {
      kicker: "Viagens",
      h2: "O seu bilhete, em três passos",
      lead: "Do percurso ao lugar sentado, tudo se trata online — antes de sair de casa.",
      itens: [
        { h: "Escolha a viagem", p: "Indique a origem, o destino e a data. Consulte as partidas e os lugares disponíveis no momento." },
        { h: "Reserve o seu lugar", p: "Seleccione o lugar no mapa do autocarro, preencha os dados de quem viaja e pague online." },
        { h: "Receba o bilhete", p: "O bilhete fica no seu telemóvel logo após o pagamento. Apresente-o ao embarcar." },
      ],
      botao: "Ver partidas e preços",
    },
    // Os cinco pontos que o site oficial lista em VANTAGENS, tal como lá estão.
    vantagens: {
      kicker: "Vantagens",
      h2: "Porquê viajar connosco",
      itens: [
        "Qualidade dos autocarros e do serviço prestado",
        "Conforto devido ao alto padrão dos autocarros",
        "Agilidade e segurança na locomoção",
        "Escolha do destino da viagem de acordo com a necessidade",
        "Motoristas qualificados",
      ],
    },
    servicos: {
      kicker: "Serviços",
      h2: "O transporte certo para cada ocasião",
      lead: "Cinco serviços, da viagem em família à deslocação diária da sua equipa.",
      cards: [
        { h: "Aluguer de autocarros", p: "Executivos e normais. A equipa ajuda a identificar a viatura adequada ao percurso e ao número de passageiros.", cta: "Pedir orçamento", alt: "Autocarros executivos TPM-TUR disponíveis para aluguer" },
        { h: "Excursões", p: "Reúna o seu grupo e partilhe o destino e o programa. A equipa prepara uma proposta para a viagem.", cta: "Planear uma excursão", alt: "Autocarro TPM-TUR para excursões e grupos" },
        { h: "Transporte de trabalhadores", p: "Apresente as necessidades de deslocação da sua equipa: percursos, turnos e frequência.", cta: "Falar com a equipa", alt: "Minibuses da TPM-TUR para transporte de equipas" },
      ],
      tambem: "Também ao seu dispor:",
      transfers: "Transfers e shuttle",
      rentACar: "Rent-a-car",
      verTodos: "Ver todos os serviços",
    },
    frota: {
      kicker: "Frota",
      h2: "Conheça a frota,",
      h2b: "imagine a viagem",
      lead: "Autocarros, Coaster, Quantum e SUV — quatro categorias para grupos e percursos diferentes. Consulte a equipa sobre lotação, comodidades e disponibilidade da viatura pretendida.",
      itens: [
        { nome: "Autocarros", nota: "Percursos longos e grupos inteiros" },
        { nome: "Coaster", nota: "Grupos médios e excursões" },
        { nome: "Quantum", nota: "Equipas e transfers" },
        { nome: "SUV", nota: "Pequenos grupos e rent-a-car" },
      ],
      // As marcas sao as que o site oficial nomeia em NOSSOS AUTOCARROS.
      marcasTitulo: "Os nossos autocarros",
      marcas: "A empresa possui uma gama de viaturas das marcas Volkswagen (VW), Marcopolo, Zhongtong Bus, Foton, Quantum, Coaster, Mercedes Sprinter, Ford Transit e Yaching, concebidas para dar conforto a quem viaja.",
      altSufixo: "da TPM-TUR",
      verCompleta: "Ver a frota completa",
    },
    clientes: {
      kicker: "Confiança",
      h2: "Clientes e parceiros",
      lead: "Organizações que já viajam connosco.",
      logoDe: "Logótipo de",
    },
    app: {
      kicker: "App do passageiro",
      h2: "A sua viagem, sempre consigo",
      p: "Com a app BusUp Passageiro, compra bilhetes, escolhe o seu lugar e tem as viagens à mão — sem filas e sem papel.",
      itens: [
        "Entre com o seu número de telefone",
        "Escolha a viagem e o seu lugar",
        "Consulte os seus bilhetes na app",
      ],
      descarregar: "Descarregar para Android",
      browser: "Comprar no browser",
      shotAlt: "Ecrã de entrada da aplicação BusUp Passageiro",
    },
    sobre: {
      kicker: "A empresa",
      h2: "Somos TPM-TUR.",
      h2b: "Ligamos pessoas aos seus destinos.",
      // Texto do site oficial, na apresentacao que a empresa faz de si propria.
      p1: "A TPM-TUR, SA é uma empresa público-privada cujo capital é detido pela Empresa Municipal Transportes Públicos de Maputo (EMTPM), a Empresa Municipal de Transportes Públicos da Matola (ETM) e pela Sky Rent, Lda.",
      p2: "Esta parceria público-privada foi constituída com o intuito de rentabilizar o investimento feito na aquisição de uma frota de autocarros executivos, estando estes a ser geridos por uma entidade independente e autónoma.",
      parceiros: "Parceiros fundadores",
      link: "A nossa história, missão e valores",
    },
    faq: {
      kicker: "Perguntas frequentes",
      h2: "Antes de partir",
      itens: [
        { q: "Como posso comprar um bilhete?", a: "Clique em Comprar bilhete, escolha a origem, o destino e a data, seleccione o lugar, preencha os dados dos passageiros e conclua o pagamento. O bilhete fica no seu telemóvel." },
        { q: "Onde consulto horários e preços?", a: "Os horários, preços e lugares disponíveis são apresentados no portal de compra depois de escolher o percurso e a data. A disponibilidade pode variar." },
        { q: "Posso pedir transporte para uma empresa ou grupo?", a: "Sim. Envie um pedido para {email} com o percurso, as datas e o número de passageiros. A equipa irá indicar as opções disponíveis." },
      ],
      comprarLink: "Comprar bilhete",
      instalarLink: "página oficial de instalação",
    },
    escolha: {
      h2: "Qual é o seu próximo destino?",
      lead: "Daqui seguem dois caminhos. Escolha o seu.",
      viajar: {
        h: "Vou viajar",
        p: "Escolha a partida e o lugar no mapa do autocarro. Paga por M-Pesa, e-Mola ou cartão, e o bilhete fica no seu telemóvel.",
        btn: "Comprar bilhete",
      },
      grupo: {
        h: "Preciso de transporte para um grupo",
        p: "Empresas, excursões, transfers e aluguer com motorista. Diga o percurso, as datas e quantas pessoas — a equipa responde com as opções disponíveis.",
        btn: "Pedir orçamento",
      },
    },
    contactoStrip: {
      comercial: "Comercial",
      passageiros: "Passageiros",
      emLinha: "Em linha",
      comprar: "Comprar bilhete",
      app: "App do passageiro",
      portal: "Entrar no portal",
    },
  },

  sobre: {
    meta: {
      titulo: "Sobre nós — TPM-TUR",
      descricao: "Conheça a TPM-TUR, a sua parceria público-privada, missão, visão e valores no transporte e turismo em Moçambique.",
    },
    migalha: "Sobre nós",
    titulo: "Somos TPM-TUR. Transporte e turismo.",
    descricao: "Uma empresa moçambicana dedicada à mobilidade de pessoas, empresas e grupos.",
    parceria: {
      kicker: "A parceria",
      h2: "Uma parceria para",
      h2b: "pôr pessoas em movimento.",
      p1: "A TPM-TUR, S.A. resulta de uma parceria público-privada entre a Empresa Municipal Transportes Públicos de Maputo (EMTPM), a Empresa Municipal de Transportes Públicos da Matola (ETM) e a Sky Rent, Lda.",
      p2: "A parceria foi criada para rentabilizar o investimento numa frota de autocarros executivos, com gestão independente e autónoma.",
      link: "Conheça a nossa frota",
      fotoAlt: "Autocarros com a identidade da TPM-TUR alinhados no parque",
    },
    // OFICIAL — declarações institucionais da empresa.
    missao: { h: "A nossa missão", p: "Disponibilizar serviços de aluguer e transporte que tratem os clientes com dignidade e valorizem a segurança e o conforto." },
    visao: { h: "A nossa visão", p: "Tornar a TPM-TUR uma referência no aluguer de autocarros executivos, correspondendo às expectativas dos seus clientes." },
    valores: {
      kicker: "Valores",
      h2: "Os valores",
      h2b: "que nos orientam.",
      lead: "Princípios que a TPM-TUR assume na sua apresentação institucional.",
      // OFICIAL — os oito valores publicados pela empresa.
      itens: ["Comprometimento", "Respeito", "Integridade", "Humildade", "Empatia", "Educação", "Solidariedade", "Ética"],
    },
    parceiros: {
      h2: "Uma parceria público-privada.",
      itens: [
        { sigla: "EMTPM", nome: "Empresa Municipal Transportes Públicos de Maputo" },
        { sigla: "ETM", nome: "Empresa Municipal de Transportes Públicos da Matola" },
        { sigla: "Sky Rent", nome: "Sky Rent, Lda." },
      ],
    },
    callout: { h2: "Fale com a nossa equipa.", p: "Indique o percurso, as datas e o número de passageiros — respondemos com as opções disponíveis." },
  },

  servicos: {
    meta: {
      titulo: "Serviços — TPM-TUR",
      descricao: "Aluguer de autocarros, rent-a-car, excursões, transfers e transporte de trabalhadores. Conheça os serviços TPM-TUR.",
    },
    migalha: "Serviços",
    titulo: "Cinco serviços. Um percurso de cada vez.",
    descricao: "Soluções para passageiros, empresas e grupos. Fale connosco sobre o seu próximo percurso.",
    indice: "Serviços nesta página",
    servico: "Serviço",
    rotuloBrief: "No pedido, indique:",
    itens: [
      {
        titulo: "Aluguer de autocarros",
        intro: "Executivos e normais. Uma solução para o seu grupo.",
        texto: "Escolha o transporte para uma deslocação de grupo, um evento ou uma viagem organizada. A equipa TPM-TUR ajuda a identificar a viatura adequada ao percurso e ao número de passageiros.",
        cta: "Pedir orçamento",
        alt: "Autocarros executivos da TPM-TUR alinhados no parque",
        brief: ["Percurso e pontos de embarque", "Número de passageiros", "Data de partida e de regresso"],
      },
      {
        titulo: "Rent-a-car",
        intro: "Uma viatura para o percurso que tem em mente.",
        texto: "Consulte a TPM-TUR sobre o aluguer de viaturas. Indique o período e a utilização pretendida para receber informação sobre as opções, as condições e a disponibilidade.",
        cta: "Consultar disponibilidade",
        alt: "Pick-up Mazda BT-50 da frota TPM-TUR, numa estrada junto à costa",
        brief: ["Datas e duração do aluguer", "Tipo de viatura pretendido", "Local de levantamento e entrega"],
      },
      {
        titulo: "Excursões",
        intro: "Reúna as pessoas. Comece a planear a viagem.",
        texto: "Organize o transporte da sua excursão com a TPM-TUR. Partilhe o destino e o programa para que a equipa possa preparar uma proposta para o grupo.",
        cta: "Planear uma excursão",
        alt: "Autocarro TPM-TUR para viagens de grupo",
        brief: ["Destino e itinerário", "Tamanho do grupo", "Datas e horários previstos"],
      },
      {
        titulo: "Transfers e shuttle",
        intro: "Entre o ponto de partida e o seu compromisso.",
        texto: "Peça uma solução de transporte para a deslocação de pessoas entre locais definidos. Partilhe os pontos de recolha e chegada e os horários de que necessita.",
        cta: "Pedir um transfer",
        alt: "Viaturas Quantum da TPM-TUR",
        brief: ["Pontos de recolha e chegada", "Horários das deslocações", "Passageiros e bagagem prevista"],
      },
      {
        titulo: "Transporte de trabalhadores",
        intro: "A mobilidade da sua equipa faz parte do trabalho.",
        texto: "Apresente as necessidades de deslocação dos seus trabalhadores. A TPM-TUR disponibiliza este serviço para empresas; a proposta é preparada de acordo com o percurso e a operação pretendida.",
        cta: "Falar com a equipa",
        alt: "Coaster da frota TPM-TUR",
        brief: ["Percursos e pontos de recolha", "Turnos e frequência", "Número de colaboradores"],
      },
    ],
    callout: { h2: "Diga-nos para onde quer ir.", p: "Quanto mais souber sobre o percurso, mais rápida é a resposta. A equipa confirma condições e disponibilidade — nada é adjudicado automaticamente." },
  },

  frota: {
    meta: {
      titulo: "Nossa frota — TPM-TUR",
      descricao: "Conheça os autocarros, Coaster, Quantum e SUV da frota TPM-TUR e consulte a disponibilidade com a nossa equipa.",
    },
    migalha: "Nossa frota",
    titulo: "Conheça a frota. Imagine a viagem.",
    descricao: "Diferentes viaturas para diferentes percursos. Explore as quatro categorias e encontre a solução com a nossa equipa.",
    indice: "Categorias nesta página",
    itens: [
      {
        nome: "Autocarros", etiqueta: "Executivos e normais",
        alt: "Autocarro executivo da TPM-TUR estacionado, visto de frente",
        texto: "Autocarros executivos e normais — a escolha para percursos longos e para mover um grupo inteiro de uma vez.",
        uso: "Viagens, excursões e aluguer com motorista.",
      },
      {
        nome: "Coaster", etiqueta: "Midibus",
        alt: "Dois midibuses Coaster da TPM-TUR lado a lado",
        texto: "Os midibuses Coaster, para quando o grupo não enche um autocarro mas já não cabe numa carrinha.",
        uso: "Transfers, excursões e deslocações de equipas.",
      },
      {
        nome: "Quantum", etiqueta: "Minibus",
        alt: "Minibuses Quantum da TPM-TUR alinhados no parque",
        texto: "Os minibuses Quantum são a opção mais ágil da frota, feita para grupos pequenos.",
        uso: "Transfers, shuttle e transporte de trabalhadores.",
      },
      {
        nome: "SUV", etiqueta: "Rent-a-car",
        alt: "Pick-up Mazda BT-50 da categoria SUV da TPM-TUR, numa estrada junto à costa",
        texto: "A categoria de ligeiros do rent-a-car, para quem precisa da viatura inteira e não de um lugar no autocarro.",
        uso: "Aluguer de viatura, mediante consulta de condições e disponibilidade.",
      },
    ],
    escolher: {
      kicker: "Como escolher",
      h2: "Uma viatura adequada",
      h2b: "à sua necessidade.",
      passos: [
        { n: "01", h: "Diga o percurso", p: "Origem, destino e paragens previstas. A distância condiciona a categoria." },
        { n: "02", h: "Conte o grupo", p: "O número de passageiros e a bagagem determinam a lotação necessária." },
        { n: "03", h: "Confirme connosco", p: "A equipa confirma lotação, comodidades e disponibilidade da viatura." },
      ],
    },
    callout: { h2: "Precisa de uma viatura para um grupo?", p: "Indique o percurso e o número de passageiros — confirmamos a viatura disponível." },
  },

  politicas: {
    meta: {
      titulo: "Nossas políticas — TPM-TUR",
      descricao: "As políticas que a TPM-TUR assume na sua actividade: qualidade, segurança, compliance, ética, inclusão e direitos humanos.",
    },
    migalha: "Nossas políticas",
    titulo: "Como nos comprometemos a trabalhar.",
    descricao: "As nove políticas que a TPM-TUR assume na sua actividade — da qualidade do serviço à conduta de quem o presta.",
    kicker: "Políticas institucionais",
    h2: "Nove compromissos",
    lead: "Cada política tem um documento próprio. O texto integral publicado pela empresa é o que vale, e prevalece sobre qualquer apresentação feita aqui.",
    subtitulo: "Documento institucional publicado pela TPM-TUR, S.A.",
    ler: "Ler a política",
    // OFICIAL — os nomes das nove políticas, tal como a empresa os publica.
    itens: [
      "Política de Qualidade",
      "Política de Saúde e Segurança no Trabalho",
      "Política de Responsabilidade Social",
      "Política de Compliance",
      "Política de Ética e Conduta Profissional",
      "Política de Inclusão e Diversidade",
      "Política de Direitos Humanos",
      "Política de Combate à Escravatura Moderna",
      "Política de Recrutamento e Selecção Transparente",
    ],
    callout: { h2: "Tem uma questão sobre estas políticas?", p: "Escreva para {email} e a equipa encaminha o pedido para quem o pode responder.", cta: "Contactar a TPM-TUR", secundario: "Sobre a TPM-TUR" },
  },

  contactos: {
    meta: {
      titulo: "Contactos — TPM-TUR",
      descricao: "Contacte a TPM-TUR em Maputo: telefones, email e localização na Rua da Resistência, Bairro de Maxaquene C.",
    },
    migalha: "Contactos",
    titulo: "Vamos conversar sobre a sua viagem.",
    descricao: "Pedidos de orçamento, parcerias e informações. Aqui estão os contactos da TPM-TUR e onde nos encontrar.",
    ligue: "Ligue-nos",
    escreva: "Escreva-nos",
    encontre: "Encontre-nos",
    abrirMapa: "Abrir no Google Maps",
    mapaTitulo: "Mapa da localização da TPM-TUR, na Rua da Resistência, Maputo",
    banda: { h2: "Já sabe para onde vai?", p: "Não precisa de nos ligar para comprar: escolha a partida e o lugar em linha.", btn: "Comprar bilhete" },
    form: {
      h3: "Conte-nos o que precisa.",
      lead: "Preenche os detalhes e preparamos o email para a nossa equipa. Nada é enviado automaticamente — revê a mensagem antes de a mandar.",
      nome: "Nome completo *",
      telefone: "Contacto telefónico *",
      email: "Email *",
      empresa: "Empresa (opcional)",
      assunto: "Assunto *",
      assuntoVazio: "Seleccione um serviço ou assunto",
      mensagem: "Como podemos ajudar? *",
      mensagemDica: "Indique o percurso, as datas, o número de passageiros e outras necessidades.",
      submeter: "Preparar email",
      aviso: "Se o seu programa de email não abriu, envie os detalhes para {email} ou ligue para {telefone}.",
      corpo: { nome: "Nome", contacto: "Contacto", email: "Email", empresa: "Empresa", naoIndicada: "Não indicada" },
      assuntos: {
        autocarros: "Aluguer de autocarros",
        "rent-a-car": "Rent-a-car",
        excursoes: "Excursões",
        transfers: "Transfers e shuttle",
        trabalhadores: "Transporte de trabalhadores",
        coaster: "Disponibilidade de Coaster",
        quantum: "Disponibilidade de Quantum",
        suv: "Disponibilidade de SUV",
        viagem: "Informação sobre uma viagem",
        outro: "Outro assunto",
      },
      assuntoGenerico: "Pedido de informação",
    },
  },
};

const EN: typeof PT = {
  nav: {
    servicos: "Services",
    frota: "Our fleet",
    sobre: "About us",
    politicas: "Our policies",
    perguntas: "FAQ",
    contactos: "Contact",
    entrar: "Sign in",
    entrarPortal: "Sign in to the portal",
    comprar: "Buy a ticket",
    saltar: "Skip to content",
    abrirMenu: "Open menu",
    fecharMenu: "Close menu",
    idioma: "Language",
    mudarIdioma: "switch to Portuguese",
    temaClaro: "Light mode",
    temaEscuro: "Dark mode",
    inicio: "Home",
    paginaInicial: "TPM-TUR — home page",
    logoAlt: "TPM-TUR, S.A. — Transport and Tourism",
  },

  rodape: {
    tagline: "A Mozambican transport and tourism company. We connect people to their destinations — passengers, companies and groups.",
    viagens: "Travel",
    app: "Passenger app",
    empresa: "Company",
    contactos: "Contact",
    tecnologia: "Technology by",
    desenvolvidoPor: "Built by",
    direitos: "TPM-TUR, S.A. · Transport and Tourism. Technology by BusUp · UpDigital.",
  },

  comum: {
    pedirOrcamento: "Request a quote",
    verServicos: "See the services",
    verFrota: "See the fleet",
    consultarDisponibilidade: "Check availability",
    caminho: "Breadcrumb",
  },

  heroBusca: {
    titulo: "Find your journey",
    tipoViagem: "Trip type",
    soIda: "One way",
    idaVolta: "Round trip",
    origem: "From",
    destino: "To",
    data: "Date",
    ida: "Outbound",
    volta: "Return",
    trocar: "Swap origin and destination",
    procurar: "Search journeys",
    destinosAVenda: "Destinations on sale:",
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
      titulo: "TPM-TUR — Transport and Tourism",
      descricao: "TPM-TUR, S.A. — transport and tourism in Mozambique. Buy your ticket online, and explore the fleet and the services for companies and groups.",
    },
    hero: {
      badge: "TPM-TUR, S.A. — Transport and Tourism",
      h1: "Your next journey",
      h1b: "starts",
      h1destaque: "here.",
      lead: "Buy your ticket online, pick your seat and board without queueing. Closer to your destination — travel with TPM-TUR.",
      fotoAlt: "Buses from the TPM-TUR fleet",
      grupo: "Need transport for a group?",
      todasPartidas: "See all departures",
    },
    confianca: [
      { t: "Public-private partnership", p: "EMTPM · ETM · Sky Rent, Lda." },
      { t: "Ticket on your phone", p: "No paper, no queueing at the counter." },
      { t: "Reserved seat", p: "Pick your seat on the bus plan." },
    ],
    passos: {
      kicker: "Travel",
      h2: "Your ticket, in three steps",
      lead: "From the route to the seat, it is all handled online — before you leave home.",
      itens: [
        { h: "Choose the journey", p: "Enter the origin, the destination and the date. See the departures and the seats available right now." },
        { h: "Reserve your seat", p: "Pick the seat on the bus plan, fill in the travellers' details and pay online." },
        { h: "Get the ticket", p: "The ticket lands on your phone as soon as the payment clears. Show it when you board." },
      ],
      botao: "See departures and fares",
    },
    vantagens: {
      kicker: "Advantages",
      h2: "Why travel with us",
      itens: [
        "Quality of the coaches and of the service",
        "Comfort, from the high standard of the coaches",
        "Agility and safety on the move",
        "The destination chosen to fit what you need",
        "Qualified drivers",
      ],
    },
    servicos: {
      kicker: "Services",
      h2: "The right transport for every occasion",
      lead: "Five services, from the family trip to your team's daily commute.",
      cards: [
        { h: "Bus hire", p: "Executive and standard coaches. The team helps identify the vehicle that fits the route and the number of passengers.", cta: "Request a quote", alt: "TPM-TUR executive coaches available for hire" },
        { h: "Excursions", p: "Gather your group and share the destination and the programme. The team prepares a proposal for the trip.", cta: "Plan an excursion", alt: "TPM-TUR coach for excursions and groups" },
        { h: "Staff transport", p: "Tell us what your team's commute needs: routes, shifts and frequency.", cta: "Talk to the team", alt: "TPM-TUR minibuses for staff transport" },
      ],
      tambem: "Also available:",
      transfers: "Transfers and shuttle",
      rentACar: "Car hire",
      verTodos: "See all services",
    },
    frota: {
      kicker: "Fleet",
      h2: "Meet the fleet,",
      h2b: "picture the journey",
      lead: "Coaches, Coaster, Quantum and SUV — four categories for different groups and routes. Ask the team about capacity, amenities and availability of the vehicle you have in mind.",
      itens: [
        { nome: "Coaches", nota: "Long routes and whole groups" },
        { nome: "Coaster", nota: "Mid-sized groups and excursions" },
        { nome: "Quantum", nota: "Teams and transfers" },
        { nome: "SUV", nota: "Small groups and car hire" },
      ],
      marcasTitulo: "Our coaches",
      marcas: "The company runs a range of vehicles from Volkswagen (VW), Marcopolo, Zhongtong Bus, Foton, Quantum, Coaster, Mercedes Sprinter, Ford Transit and Yaching, built to keep passengers comfortable.",
      altSufixo: "from TPM-TUR",
      verCompleta: "See the full fleet",
    },
    clientes: {
      kicker: "Trust",
      h2: "Clients and partners",
      lead: "Organisations that already travel with us.",
      logoDe: "Logo of",
    },
    app: {
      kicker: "Passenger app",
      h2: "Your journey, always with you",
      p: "With the BusUp Passenger app you buy tickets, pick your seat and keep your journeys at hand — no queues, no paper.",
      itens: [
        "Sign in with your phone number",
        "Choose the journey and your seat",
        "Find your tickets in the app",
      ],
      descarregar: "Download for Android",
      browser: "Buy in the browser",
      shotAlt: "Sign-in screen of the BusUp Passenger app",
    },
    sobre: {
      kicker: "The company",
      h2: "We are TPM-TUR.",
      h2b: "We connect people to their destinations.",
      // Traducao de trabalho do texto institucional do site oficial.
      p1: "TPM-TUR, SA is a public-private company whose capital is held by Empresa Municipal Transportes Públicos de Maputo (EMTPM), Empresa Municipal de Transportes Públicos da Matola (ETM) and Sky Rent, Lda.",
      p2: "This public-private partnership was formed to make the investment in a fleet of executive coaches pay off, with those coaches run by an independent and autonomous entity.",
      parceiros: "Founding partners",
      link: "Our story, mission and values",
    },
    faq: {
      kicker: "Frequently asked questions",
      h2: "Before you set off",
      itens: [
        { q: "How do I buy a ticket?", a: "Click Buy a ticket, choose the origin, the destination and the date, pick the seat, fill in the passengers' details and complete the payment. The ticket lands on your phone." },
        { q: "Where do I find timetables and fares?", a: "Timetables, fares and available seats appear in the booking portal once you choose the route and the date. Availability may vary." },
        { q: "Can I request transport for a company or a group?", a: "Yes. Send a request to {email} with the route, the dates and the number of passengers. The team will come back with the available options." },
      ],
      comprarLink: "Buy a ticket",
      instalarLink: "official installation page",
    },
    escolha: {
      h2: "Where are you headed next?",
      lead: "Two paths from here. Take yours.",
      viajar: {
        h: "I am travelling",
        p: "Pick the departure and your seat on the bus plan. Pay with M-Pesa, e-Mola or card, and the ticket lands on your phone.",
        btn: "Buy a ticket",
      },
      grupo: {
        h: "I need transport for a group",
        p: "Companies, excursions, transfers and hire with a driver. Tell us the route, the dates and how many people — the team comes back with the available options.",
        btn: "Request a quote",
      },
    },
    contactoStrip: {
      comercial: "Sales",
      passageiros: "Passengers",
      emLinha: "Online",
      comprar: "Buy a ticket",
      app: "Passenger app",
      portal: "Sign in to the portal",
    },
  },

  sobre: {
    meta: {
      titulo: "About us — TPM-TUR",
      descricao: "Meet TPM-TUR, its public-private partnership, mission, vision and values in transport and tourism in Mozambique.",
    },
    migalha: "About us",
    titulo: "We are TPM-TUR. Transport and tourism.",
    descricao: "A Mozambican company dedicated to the mobility of people, companies and groups.",
    parceria: {
      kicker: "The partnership",
      h2: "A partnership to",
      h2b: "put people in motion.",
      p1: "TPM-TUR, S.A. is the result of a public-private partnership between Empresa Municipal Transportes Públicos de Maputo (EMTPM), Empresa Municipal de Transportes Públicos da Matola (ETM) and Sky Rent, Lda.",
      p2: "The partnership was created to make the investment in a fleet of executive coaches pay off, under independent and autonomous management.",
      link: "Meet our fleet",
      fotoAlt: "Buses carrying TPM-TUR livery lined up in the yard",
    },
    // OFICIAL — tradução de trabalho de uma declaração institucional.
    missao: { h: "Our mission", p: "To provide hire and transport services that treat clients with dignity and hold safety and comfort as values." },
    visao: { h: "Our vision", p: "To make TPM-TUR a reference in executive coach hire, meeting the expectations of its clients." },
    valores: {
      kicker: "Values",
      h2: "The values",
      h2b: "that guide us.",
      lead: "Principles TPM-TUR states in its institutional presentation.",
      // OFICIAL — tradução de trabalho dos oito valores publicados.
      itens: ["Commitment", "Respect", "Integrity", "Humility", "Empathy", "Courtesy", "Solidarity", "Ethics"],
    },
    parceiros: {
      h2: "A public-private partnership.",
      // Nomes de entidades registadas: NAO se traduzem, nem com a pagina em
      // ingles. Traduzi-los aqui deixava a mesma empresa com dois nomes na
      // mesma pagina, porque o paragrafo acima usa o legal.
      itens: [
        { sigla: "EMTPM", nome: "Empresa Municipal Transportes Públicos de Maputo" },
        { sigla: "ETM", nome: "Empresa Municipal de Transportes Públicos da Matola" },
        { sigla: "Sky Rent", nome: "Sky Rent, Lda." },
      ],
    },
    callout: { h2: "Talk to our team.", p: "Tell us the route, the dates and the number of passengers — we come back with the available options." },
  },

  servicos: {
    meta: {
      titulo: "Services — TPM-TUR",
      descricao: "Bus hire, car hire, excursions, transfers and staff transport. Explore the TPM-TUR services.",
    },
    migalha: "Services",
    titulo: "Five services. One route at a time.",
    descricao: "Solutions for passengers, companies and groups. Talk to us about your next route.",
    indice: "Services on this page",
    servico: "Service",
    rotuloBrief: "In your request, tell us:",
    itens: [
      {
        titulo: "Bus hire",
        intro: "Executive and standard coaches. A solution for your group.",
        texto: "Choose the transport for a group trip, an event or an organised journey. The TPM-TUR team helps identify the vehicle that fits the route and the number of passengers.",
        cta: "Request a quote",
        alt: "TPM-TUR executive coaches lined up in the yard",
        brief: ["Route and pick-up points", "Number of passengers", "Departure and return dates"],
      },
      {
        titulo: "Car hire",
        intro: "A vehicle for the route you have in mind.",
        texto: "Ask TPM-TUR about vehicle hire. Tell us the period and the intended use to get information on the options, the terms and availability.",
        cta: "Check availability",
        alt: "Mazda BT-50 pick-up from the TPM-TUR fleet, on a coastal road",
        brief: ["Hire dates and duration", "Type of vehicle", "Pick-up and drop-off location"],
      },
      {
        titulo: "Excursions",
        intro: "Gather the people. Start planning the trip.",
        texto: "Organise your excursion's transport with TPM-TUR. Share the destination and the programme so the team can prepare a proposal for the group.",
        cta: "Plan an excursion",
        alt: "TPM-TUR coach for group journeys",
        brief: ["Destination and itinerary", "Group size", "Expected dates and times"],
      },
      {
        titulo: "Transfers and shuttle",
        intro: "Between the starting point and your appointment.",
        texto: "Request a transport solution to move people between set locations. Share the pick-up and drop-off points and the times you need.",
        cta: "Request a transfer",
        alt: "TPM-TUR Quantum vehicles",
        brief: ["Pick-up and drop-off points", "Times of each run", "Passengers and expected luggage"],
      },
      {
        titulo: "Staff transport",
        intro: "Your team's mobility is part of the job.",
        texto: "Tell us what your staff's commute needs. TPM-TUR provides this service to companies; the proposal is prepared according to the route and the operation you have in mind.",
        cta: "Talk to the team",
        alt: "Coaster from the TPM-TUR fleet",
        brief: ["Routes and pick-up points", "Shifts and frequency", "Number of employees"],
      },
    ],
    callout: { h2: "Tell us where you want to go.", p: "The more we know about the route, the faster the answer. The team confirms terms and availability — nothing is committed automatically." },
  },

  frota: {
    meta: {
      titulo: "Our fleet — TPM-TUR",
      descricao: "Explore the coaches, Coaster, Quantum and SUV in the TPM-TUR fleet and check availability with our team.",
    },
    migalha: "Our fleet",
    titulo: "Meet the fleet. Picture the journey.",
    descricao: "Different vehicles for different routes. Explore the four categories and find the right one with our team.",
    indice: "Categories on this page",
    itens: [
      {
        nome: "Coaches", etiqueta: "Executive and standard",
        alt: "TPM-TUR executive coach parked, seen from the front",
        texto: "Executive and standard coaches — the choice for long routes and for moving a whole group at once.",
        uso: "Journeys, excursions and hire with a driver.",
      },
      {
        nome: "Coaster", etiqueta: "Midibus",
        alt: "Two TPM-TUR Coaster midibuses side by side",
        texto: "The Coaster midibuses, for when the group does not fill a coach but no longer fits in a van.",
        uso: "Transfers, excursions and team travel.",
      },
      {
        nome: "Quantum", etiqueta: "Minibus",
        alt: "TPM-TUR Quantum minibuses lined up in the yard",
        texto: "The Quantum minibuses are the nimblest option in the fleet, made for small groups.",
        uso: "Transfers, shuttle and staff transport.",
      },
      {
        nome: "SUV", etiqueta: "Car hire",
        alt: "Mazda BT-50 pick-up in the TPM-TUR SUV category, on a coastal road",
        texto: "The light-vehicle category of the car hire service, for whoever needs the whole vehicle and not a seat on a coach.",
        uso: "Vehicle hire, subject to terms and availability.",
      },
    ],
    escolher: {
      kicker: "How to choose",
      h2: "A vehicle that fits",
      h2b: "what you need.",
      passos: [
        { n: "01", h: "Tell us the route", p: "Origin, destination and expected stops. The distance shapes the category." },
        { n: "02", h: "Count the group", p: "The number of passengers and the luggage set the capacity needed." },
        { n: "03", h: "Confirm with us", p: "The team confirms capacity, amenities and availability of the vehicle." },
      ],
    },
    callout: { h2: "Need a vehicle for a group?", p: "Tell us the route and the number of passengers — we confirm the vehicle available." },
  },

  politicas: {
    meta: {
      titulo: "Our policies — TPM-TUR",
      descricao: "The policies TPM-TUR holds in its activity: quality, safety, compliance, ethics, inclusion and human rights.",
    },
    migalha: "Our policies",
    titulo: "How we commit to work.",
    descricao: "The nine policies TPM-TUR holds in its activity — from the quality of the service to the conduct of those who deliver it.",
    kicker: "Institutional policies",
    h2: "Nine commitments",
    lead: "Each policy has its own document. The full text published by the company is what counts, and prevails over any presentation made here.",
    subtitulo: "Institutional document published by TPM-TUR, S.A.",
    ler: "Read the policy",
    // OFICIAL — tradução de trabalho. Os documentos são publicados em
    // português; estes nomes ingleses não são os da empresa até ela os validar.
    itens: [
      "Quality Policy",
      "Occupational Health and Safety Policy",
      "Social Responsibility Policy",
      "Compliance Policy",
      "Ethics and Professional Conduct Policy",
      "Inclusion and Diversity Policy",
      "Human Rights Policy",
      "Modern Slavery Policy",
      "Transparent Recruitment and Selection Policy",
    ],
    callout: { h2: "A question about these policies?", p: "Write to {email} and the team passes it on to whoever can answer it.", cta: "Contact TPM-TUR", secundario: "About TPM-TUR" },
  },

  contactos: {
    meta: {
      titulo: "Contact — TPM-TUR",
      descricao: "Contact TPM-TUR in Maputo: phone numbers, email and location on Rua da Resistência, Bairro de Maxaquene C.",
    },
    migalha: "Contact",
    titulo: "Let's talk about your journey.",
    descricao: "Quote requests, partnerships and information. Here are TPM-TUR's contacts and where to find us.",
    ligue: "Call us",
    escreva: "Write to us",
    encontre: "Find us",
    abrirMapa: "Open in Google Maps",
    mapaTitulo: "Map of the TPM-TUR location, on Rua da Resistência, Maputo",
    banda: { h2: "Already know where you are going?", p: "You do not need to call us to buy: pick the departure and the seat online.", btn: "Buy a ticket" },
    form: {
      h3: "Tell us what you need.",
      lead: "Fill in the details and we prepare the email to our team. Nothing is sent automatically — review the message before sending it.",
      nome: "Full name *",
      telefone: "Phone number *",
      email: "Email *",
      empresa: "Company (optional)",
      assunto: "Subject *",
      assuntoVazio: "Select a service or subject",
      mensagem: "How can we help? *",
      mensagemDica: "Tell us the route, the dates, the number of passengers and anything else you need.",
      submeter: "Prepare email",
      aviso: "If your email program did not open, send the details to {email} or call {telefone}.",
      corpo: { nome: "Name", contacto: "Phone", email: "Email", empresa: "Company", naoIndicada: "Not given" },
      assuntos: {
        autocarros: "Bus hire",
        "rent-a-car": "Car hire",
        excursoes: "Excursions",
        transfers: "Transfers and shuttle",
        trabalhadores: "Staff transport",
        coaster: "Coaster availability",
        quantum: "Quantum availability",
        suv: "SUV availability",
        viagem: "Information about a journey",
        outro: "Another subject",
      },
      assuntoGenerico: "Information request",
    },
  },
};

export const COPY: Record<Lang, typeof PT> = { pt: PT, en: EN };

/** O texto da página no idioma escolhido, mais o próprio selector. */
export function useTpmCopy() {
  const { lang, setLang } = useLandingPrefs();
  return { t: COPY[lang], lang, setLang };
}
