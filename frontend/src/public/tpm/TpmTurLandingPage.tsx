import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Armchair, ArrowRight, ArrowUpRight, BusFront, CheckCircle2, Download,
  Handshake, Phone, Route, Smartphone, Ticket, Users,
} from "lucide-react";
import Reveal from "../landing/Reveal";
import HeroBooking from "./HeroBooking";
import TpmPagina, { EMAIL, TELEFONE, TELEFONE_HREF, pedido, useTpmMeta } from "./TpmChrome";
import { useTpmCopy } from "./tpm-copy";

/* Landing institucional + passageiros da TPM-TUR, cliente da UpDigital.
 * Vive em /tpm-tur, ao lado da landing BusUp (/). O conteúdo vem do site
 * oficial (output/tpm-tur-site) — os factos (serviços, frota, contactos)
 * são os de lá; não se inventam números que a operação não confirmou.
 *
 * A barra e o rodapé saíram daqui para `TpmChrome`, e o texto para
 * `tpm-copy.ts`. Esta página fica com a composição das secções.
 *
 * A DOBRA É UM BLOCO. Fotografia, cartão de busca e faixa de prova vivem
 * dentro de `.tpm-dobra`, que mede a altura do ecrã menos a barra. O cartão
 * caía fora do primeiro ecrã (o herói tinha 760px fixos e o cartão começava
 * aos 684) — a acção da página só aparecia a quem rolasse.
 *
 * O QUE SAIU, E PORQUÊ. Dez blocos abaixo da dobra passaram a sete:
 *  - "O seu bilhete, em três passos": o formulário é o fluxo, e a primeira
 *    pergunta da FAQ repetia-o quase palavra por palavra.
 *  - "Vantagens", cinco afirmações não verificáveis, deram lugar aos três
 *    factos da faixa de prova, na dobra.
 *  - A faixa final de três cartões de contacto: email, telefone, comprar,
 *    app e portal estavam todos no CTA acima E no rodapé.
 *  - "Ver todas as partidas" no herói, "Comprar no browser" na faixa da app,
 *    e a tira "Também ao seu dispor": cópias de acções já presentes.
 *  - Os dois botões centrados "ver todos" / "ver a frota completa" subiram
 *    para junto dos títulos das secções.
 * Nada disto apagou informação que só existisse nesses blocos. */

/* Os ids das âncoras e as fotografias não mudam com o idioma: os primeiros são
 * URL, as segundas são as mesmas imagens. */
const SERVICOS_IDS = ["autocarros", "excursoes", "trabalhadores"] as const;
const SERVICOS_ICON = [BusFront, Route, Users];
const SERVICOS_IMG = ["/landing/tpm/coaches.webp", "/landing/tpm/coach.webp", "/landing/tpm/minibuses.webp"];
const FROTA_IMG = [
  "/landing/tpm/coach.webp",
  "/landing/tpm/coaster.webp",
  "/landing/tpm/minibuses.webp",
  "/landing/tpm/suv.webp",
];

/* Clientes e parceiros — a seccao que o site oficial tem e esta nao tinha.
 *
 * Os ficheiros sao os do carrossel de tpmtur.co.mz (wp-content/uploads,
 * 2025/10 e 2025/11), copiados para `public/landing/tpm/clientes/` com nomes
 * legiveis. No original NENHUM tem texto alternativo: sao 34 imagens que um
 * leitor de ecra anuncia como nada. Aqui cada uma leva o nome da organizacao,
 * lido do proprio logotipo.
 *
 * Duas notas de honestidade: o oval vermelho e verde traz so a sigla "MM" e
 * nao consegui apurar de quem e — fica a sigla, que e o que la esta escrito. O
 * verde e a CFM, Caminhos de Ferro de Mocambique. */
const CLIENTES: { f: string; nome: string }[] = [
  { f: "banco-de-mocambique.png", nome: "Banco de Moçambique" },
  { f: "assembleia-da-republica.png", nome: "Assembleia da República" },
  { f: "municipio-de-maputo.jpg", nome: "Município de Maputo" },
  { f: "cidade-da-matola.jpg", nome: "Cidade da Matola" },
  { f: "cfm.jpg", nome: "CFM — Caminhos de Ferro de Moçambique" },
  { f: "edm.jpg", nome: "Electricidade de Moçambique, E.P." },
  { f: "petromoc.jpg", nome: "Petromoc" },
  { f: "vodacom.jpg", nome: "Vodacom" },
  { f: "totalenergies.jpg", nome: "TotalEnergies" },
  { f: "millennium-bim.png", nome: "Millennium bim" },
  { f: "bci.png", nome: "BCI" },
  { f: "moza.png", nome: "Moza Banco" },
  { f: "nedbank.png", nome: "Nedbank" },
  { f: "bni.jpg", nome: "BNI — Banco Nacional de Investimento" },
  { f: "bvm.jpg", nome: "BVM — Bolsa de Valores de Moçambique" },
  { f: "inep.jpg", nome: "INEP — Instituto Nacional de Emprego" },
  { f: "iese.jpg", nome: "IESE — Instituto de Estudos Sociais e Económicos" },
  { f: "ocam.png", nome: "OCAM — Ordem dos Contabilistas e Auditores de Moçambique" },
  { f: "radio-mocambique.jpg", nome: "Rádio Moçambique" },
  { f: "fmn.jpg", nome: "Federação Moçambicana de Natação" },
  { f: "aism.jpg", nome: "AISM — American International School of Mozambique" },
  { f: "afecc-gloria-hotel.jpg", nome: "AFECC Gloria Hotel Maputo" },
  { f: "bureau-veritas.jpg", nome: "Bureau Veritas" },
  { f: "ccs-jv.png", nome: "CCS-JV" },
  { f: "impala.png", nome: "Impala" },
  { f: "grindrod.png", nome: "Grindrod" },
  { f: "twigg.jpg", nome: "TWIGG Exploration & Mining" },
  { f: "true-north.jpg", nome: "True North" },
  { f: "tayanna.jpg", nome: "Tayanna" },
  { f: "apco.png", nome: "APCO Heavy Duty Parts" },
  { f: "ronil.png", nome: "Ronil" },
  { f: "yutong.png", nome: "Yutong" },
  { f: "zhongtong.png", nome: "Zhongtong" },
  { f: "mm.png", nome: "MM" },
];

/* Metade dos clientes em cada tira do carrossel. O corte ao meio segue a ordem
 * do array acima, que é a do site oficial: a primeira fila fica com as
 * instituições e os bancos, a segunda com as restantes organizações. */
const CLIENTES_FILA_A = CLIENTES.slice(0, 17);
const CLIENTES_FILA_B = CLIENTES.slice(17);

/** Uma tira do carrossel de clientes.
 *
 *  A lista entra DUAS vezes. A animação desliza a tira -50% do próprio
 *  comprimento, por isso no instante em que reinicia a segunda cópia está
 *  exactamente onde a primeira começou — a emenda nunca se vê, e não é preciso
 *  uma linha de JavaScript para o loop ser infinito.
 *
 *  A cópia leva `aria-hidden` e texto alternativo vazio: sem isso um leitor de
 *  ecrã anunciava as 34 organizações a dobrar. */
function TiraClientes({
  itens,
  sentido,
  logoDe,
}: {
  itens: typeof CLIENTES;
  sentido: "para-esquerda" | "para-direita";
  logoDe: string;
}) {
  const grupo = (copia: boolean) => (
    <ul className="tpm-carrossel-grupo" aria-hidden={copia || undefined}>
      {itens.map((c) => (
        <li className="tpm-cliente" key={`${copia ? "copia" : "orig"}-${c.f}`}>
          {/* Sem `loading="lazy"`, e com `fetchPriority="low"`.
              Numa grelha parada o lazy é a escolha certa; numa tira que
              desfila não é: cada logótipo só começava a descarregar quando já
              estava à vista, e entrava em branco pela borda. Um cartão branco
              a atravessar o ecrã lê-se como defeito, não como espera.
              A prioridade baixa é o que impede que estes 34 ficheiros
              disputem largura de banda com a fotografia do herói, que é o
              que tem de pintar primeiro. */}
          <img src={`/landing/tpm/clientes/${c.f}`} alt={copia ? "" : `${logoDe} ${c.nome}`}
            width={283} height={188} fetchPriority="low" decoding="async" />
        </li>
      ))}
    </ul>
  );

  return (
    <div className="tpm-carrossel">
      <div className={`tpm-carrossel-tira ${sentido}`}>
        {grupo(false)}
        {grupo(true)}
      </div>
    </div>
  );
}

/* Ícones da faixa de prova, na ordem do array `confianca` do tpm-copy. */
const PROVA_ICON = [Handshake, Smartphone, Armchair];

export default function TpmTurLandingPage() {
  const { hash } = useLocation();
  const { t } = useTpmCopy();
  const i = t.inicio;

  useTpmMeta(i.meta.titulo, i.meta.descricao);

  /* As páginas institucionais ligam a `/tpm-tur#faq`. O react-router muda a
   * URL mas não rola para a âncora — sem isto, quem clica em "Perguntas"
   * noutra página aterra no topo da landing e pensa que o link está partido. */
  useEffect(() => {
    if (!hash) return;
    const alvo = document.querySelector(hash);
    if (alvo) alvo.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [hash]);

  return (
    <TpmPagina>
      {/* ── A DOBRA ──────────────────────────────────────────────────────
          Fotografia, cartão de busca e faixa de prova são um bloco com a
          altura do ecrã menos a barra. O cartão deixou de cair fora do
          primeiro ecrã: é a acção da página e é a primeira coisa que se vê. */}
      <div className="tpm-dobra">
        {/* O cartão vive DENTRO do herói, e não a cavalo na aresta de baixo
            como antes. Ficava metade sobre a fotografia e metade sobre a
            página: a aresta cortava-o ao meio e a acção principal aparecia
            partida entre dois fundos. Aqui assenta inteiro sobre a imagem,
            com uma faixa de fotografia por baixo — é o que a tela desenha.
            O `overflow:hidden` do <section> deixou de ser um problema porque
            já nada transborda. */}
        <section className="tpm-hero">
          <img className="tpm-hero-photo" src="/landing/tpm/coaches.webp"
            alt={i.hero.fotoAlt} width={1920} height={1920}
            fetchPriority="high" decoding="sync" />
          <div className="tpm-hero-in">
            {/* Sem etiqueta por cima do título. Dizia "TPM-TUR, S.A. —
                Transporte e Turismo", que é o que o logótipo da barra já diz
                a três centímetros dali, e empurrava o título para baixo. */}
            <h1>{i.hero.h1}<br />{i.hero.h1b} <span>{i.hero.h1destaque}</span></h1>
            <p>{i.hero.lead}</p>
            <HeroBooking />
            {/* Um caminho secundário, e não dois, e em texto e não em botão:
                um segundo botão ao lado de "Procurar viagens" disputava-lhe a
                atenção. "Ver todas as partidas" saiu — era o que o botão do
                próprio formulário faz, a dois centímetros de distância. */}
            <p className="tpm-hero-grupo">
              {i.hero.grupo}{" "}
              <a href={pedido("Pedido de orçamento TPM-TUR")}>{t.comum.pedirOrcamento}</a>
            </p>
          </div>
        </section>

        {/* Três factos, não cinco afirmações. Substitui a secção "Vantagens",
            que dizia coisas como "conforto devido ao alto padrão dos
            autocarros" — não verificável, e por isso sem valor para quem
            decide. Estes três verificam-se: a parceria consta do registo da
            empresa, o bilhete fica no telemóvel, o lugar escolhe-se no mapa. */}
        <div className="tpm-dobra-prova">
          <div className="tpm-dobra-prova-in">
            {i.confianca.map((c, n) => {
              const Icone = PROVA_ICON[n];
              return (
                <div className="tpm-dobra-prova-item" key={c.t}>
                  <Icone size={18} aria-hidden strokeWidth={2} />
                  <div>
                    <strong>{c.t}</strong>
                    <span>{c.p}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 1 · QUEM SOMOS */}
      <section className="bzlp-sec" id="sobre">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="tpm-sobre">
              <div>
                <div className="bzlp-kicker left">{i.sobre.kicker}</div>
                <h2>{i.sobre.h2}<br /><span>{i.sobre.h2b}</span></h2>
              </div>
              <div className="tpm-sobre-copy">
                <p>{i.sobre.p1}</p>
                <p>{i.sobre.p2}</p>
                <div className="tpm-sobre-partners" aria-label={i.sobre.parceiros}>
                  <span>EMTPM</span><span>ETM</span><span>Sky Rent, Lda</span>
                </div>
                <Link to="/tpm-tur/sobre-nos" className="bzlp-ghost" style={{ paddingLeft: 0, marginTop: 14 }}>
                  {i.sobre.link} <ArrowUpRight size={16} aria-hidden />
                </Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* 2 · SERVIÇOS */}
      <section className="bzlp-sec alt" id="servicos">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="tpm-sechead-linha">
              <div>
                <div className="bzlp-kicker left">{i.servicos.kicker}</div>
                <h2 className="bzlp-h2 left">{i.servicos.h2}</h2>
                <p className="bzlp-lead left">{i.servicos.lead}</p>
              </div>
              <Link to="/tpm-tur/servicos" className="tpm-sec-link">
                {i.servicos.verTodos} <ArrowRight size={17} aria-hidden />
              </Link>
            </div>
          </Reveal>
          <div className="tpm-services">
            {i.servicos.cards.map((s, n) => {
              const Icone = SERVICOS_ICON[n];
              return (
                <Reveal key={s.h} delay={n * 70}>
                  <article className="tpm-service">
                    <img src={SERVICOS_IMG[n]} alt={s.alt} width={1200} height={750} loading="lazy" decoding="async" />
                    <div className="tpm-service-body">
                      <h3><Icone size={18} aria-hidden style={{ verticalAlign: "-3px", marginRight: 8, color: "var(--blue2)" }} />{s.h}</h3>
                      <p>{s.p}</p>
                      <Link to={`/tpm-tur/servicos#${SERVICOS_IDS[n]}`}>{s.cta} <ArrowUpRight size={16} aria-hidden /></Link>
                    </div>
                  </article>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* 3 · FROTA */}
      <section className="bzlp-sec" id="frota">
        <div className="bzlp-wrap">
          {/* Cabecalho a esquerda, e nao centrado: duas seccoes seguidas com a
              mesma composicao — etiqueta ao meio, titulo ao meio, fila de
              cartoes iguais — fazem a pagina parecer gerada. */}
          <Reveal>
            <div className="tpm-frota-head">
              <div>
                <div className="bzlp-kicker left">{i.frota.kicker}</div>
                <h2 className="bzlp-h2 left">{i.frota.h2}<br />{i.frota.h2b}</h2>
              </div>
              <div>
                <p className="bzlp-lead left">{i.frota.lead}</p>
                {/* As marcas da frota, tal como o site oficial as nomeia em
                    NOSSOS AUTOCARROS. */}
                <p className="tpm-frota-marcas">{i.frota.marcas}</p>
                <Link to="/tpm-tur/frota" className="tpm-sec-link">
                  {i.frota.verCompleta} <ArrowRight size={17} aria-hidden />
                </Link>
              </div>
            </div>
          </Reveal>
          <div className="tpm-fleet">
            {i.frota.itens.map((v, n) => (
              <Reveal key={v.nome} delay={n * 60}>
                <figure className="tpm-vehicle">
                  <img src={FROTA_IMG[n]} alt={`${v.nome} ${i.frota.altSufixo}`}
                    width={1200} height={1500} loading="lazy" decoding="async" />
                  <figcaption>{v.nome}<small>{v.nota}</small></figcaption>
                </figure>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* 4 · APP DO PASSAGEIRO — o único lugar da página onde se descarrega.
          "Comprar no browser" saiu daqui: era a quarta cópia da mesma acção. */}
      <section className="tpm-app" id="app">
        <div className="tpm-app-in">
          <Reveal>
            <div className="tpm-app-shot">
              <img src="/landing/tpm/app-login.png" alt={i.app.shotAlt}
                width={430} height={900} loading="lazy" decoding="async" />
            </div>
          </Reveal>
          <Reveal delay={90}>
            <div>
              <div className="bzlp-kicker left">{i.app.kicker}</div>
              <h2>{i.app.h2}</h2>
              <p>{i.app.p}</p>
              <ul>
                {i.app.itens.map((li) => (
                  <li key={li}><CheckCircle2 size={18} aria-hidden /> {li}</li>
                ))}
              </ul>
              <div className="tpm-app-cta">
                <Link to="/baixar" className="bzlp-btn gold"><Download size={18} aria-hidden /> {i.app.descarregar}</Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* 5 · FAQ — a pergunta "como instalo a app Android" saiu: a faixa da
          app, imediatamente acima, é a resposta e traz o botão. */}
      <section className="bzlp-sec alt" id="faq">
        <div className="bzlp-wrap tpm-faq-wrap">
          <Reveal>
            <div className="tpm-faq-head">
              <div className="bzlp-kicker left">{i.faq.kicker}</div>
              <h2 className="bzlp-h2 left">{i.faq.h2}</h2>
            </div>
          </Reveal>
          <div className="tpm-faq">
            {i.faq.itens.map((item) => (
              <details key={item.q}>
                <summary>{item.q}</summary>
                {/* O email é a única ligação que sobrevive dentro de uma
                    resposta: vem por marcador, para a frase poder mudar de
                    ordem em inglês sem partir o link. */}
                <p>
                  {item.a.split("{email}").map((parte, n, todas) => (
                    <span key={n}>
                      {parte}
                      {n < todas.length - 1 && <a href={`mailto:${EMAIL}`}>{EMAIL}</a>}
                    </span>
                  ))}
                </p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* 6 · CLIENTES E PARCEIROS — as 34 organizações em duas tiras a
          desfilar em sentidos opostos. Em grelha eram uma parede de logótipos
          que ninguém percorre; a desfilar ocupam menos de metade da altura. */}
      <section className="bzlp-sec" id="clientes">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="bzlp-sechead">
              <div className="bzlp-kicker">{i.clientes.kicker}</div>
              <h2 className="bzlp-h2">{i.clientes.h2}</h2>
              <p className="bzlp-lead">{i.clientes.lead}</p>
            </div>
          </Reveal>
        </div>
        {/* Fora do `bzlp-wrap`: as tiras vão de ponta a ponta do ecrã, que é o
            que faz o movimento parecer contínuo em vez de preso numa caixa. */}
        <TiraClientes itens={CLIENTES_FILA_A} logoDe={i.clientes.logoDe} sentido="para-esquerda" />
        <TiraClientes itens={CLIENTES_FILA_B} logoDe={i.clientes.logoDe} sentido="para-direita" />
      </section>

      {/* 7 · CTA FINAL — dois caminhos, e nao dois botoes iguais.
          "Comprar bilhete" e auto-servico, instantaneo, de quem vai viajar;
          "Pedir orcamento" e uma conversa comercial com uma empresa. Lado a
          lado e com o mesmo peso, obrigavam cada visitante a ler os dois para
          descobrir qual era o seu. O dourado — a cor que a marca reserva para
          "olha para aqui" — marca a accao do caminho do passageiro.

          A faixa de três cartões de contacto que vinha depois disto saiu: o
          email, o telefone, o "comprar bilhete", a app e o portal estavam
          todos aqui em cima E no rodapé. */}
      <section className="tpm-escolha" id="contacto">
        <div className="bzlp-wrap">
          <div className="tpm-escolha-head">
            <h2>{i.escolha.h2}</h2>
            <p>{i.escolha.lead}</p>
          </div>
          <div className="tpm-escolha-cartoes">
            <article className="tpm-escolha-cartao">
              <span className="tpm-escolha-ico"><Ticket size={24} aria-hidden /></span>
              <h3>{i.escolha.viajar.h}</h3>
              <p>{i.escolha.viajar.p}</p>
              <Link to="/comprar" className="bzlp-btn gold">
                {i.escolha.viajar.btn} <ArrowRight size={17} aria-hidden />
              </Link>
            </article>
            <article className="tpm-escolha-cartao is-grupo">
              <span className="tpm-escolha-ico"><Users size={24} aria-hidden /></span>
              <h3>{i.escolha.grupo.h}</h3>
              <p>{i.escolha.grupo.p}</p>
              <div className="tpm-escolha-accoes">
                <a href={pedido("Pedido de orçamento TPM-TUR")} className="bzlp-btn outline">
                  {i.escolha.grupo.btn} <ArrowUpRight size={16} aria-hidden />
                </a>
                {/* O telefone vem para junto do botao: quem pede orcamento para
                    um grupo quer muitas vezes falar com alguem, e o numero
                    estava so no rodape. */}
                <a href={TELEFONE_HREF} className="tpm-escolha-tel">
                  <Phone size={17} aria-hidden /> {TELEFONE}
                </a>
              </div>
            </article>
          </div>
        </div>
      </section>
    </TpmPagina>
  );
}
