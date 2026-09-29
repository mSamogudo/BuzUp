import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Bus, Clock3, Snowflake, Wifi } from "lucide-react";
import CheRevela from "./CheRevela";
import HeroArte from "./HeroArte";
import HeroDecoracoes from "./HeroDecoracoes";
import OndaCheetah from "./OndaCheetah";
import HeroBusca from "../comum/HeroBusca";
import CheetahPagina, { pedido, useCheetahMeta } from "./CheetahChrome";
import { useCheetahCopy } from "./cheetah-copy";

/* Página inicial da Cheetah Express, cliente da UpDigital.
 * Vive em /cheetah-express, ao lado da landing BusUp (/) e do site da
 * TPM-TUR (/tpm-tur). O conteúdo vem do site oficial (cheetah-express.com):
 * os factos — horas, paragens, preços, parceiros — são os de lá; não se
 * inventam números que a operação não confirmou.
 */

/* Os parceiros que o site oficial mostra. Nenhum deles tem texto alternativo
 * no original — são imagens que um leitor de ecrã anuncia como nada. Aqui cada
 * uma leva o nome da organização, lido do próprio logótipo. */
const PARCEIROS = [
  { f: "ilanga-mall.png", nome: "Ilanga Mall" },
  { f: "riverside-mall.jpg", nome: "Riverside Mall" },
  { f: "mediplus.png", nome: "Mediplus" },
  { f: "medi-evac.png", nome: "Medi-Evac" },
  { f: "casa.png", nome: "Casa" },
];

const PROVAS_ICON = [Snowflake, Clock3, Bus, Wifi];

/* A cor e o destino de cada cartão de serviço. São estrutura, não texto — por
   isso não vivem no dicionário, onde teriam de ser traduzidos sem razão. */
const SERVICOS_COR = ["che-s-vermelho", "che-s-branco", "che-s-laranja"];
const SERVICOS_LINK = [
  "/cheetah-express/horarios#maputo-nelspruit",
  "/cheetah-express/horarios#tofo-nelspruit",
  "/cheetah-express/contactos",
];

export default function CheetahLandingPage() {
  const { t } = useCheetahCopy();
  const i = t.inicio;

  /* Qual dos três cartões está sob o rato. Serve para os OUTROS recuarem: o
     grupo reage, e não só o cartão apontado. Um cartão que cresce sozinho
     parece um botão; três que se reorganizam parecem uma escolha. */
  const [servicoActivo, setServicoActivo] = useState<number | null>(null);

  useCheetahMeta(i.meta.titulo, i.meta.descricao);

  return (
    <CheetahPagina>
      {/* HERO — duas colunas. A única imagem que a empresa tem é uma
          composição VERTICAL recortada (o passageiro, a carrinha, a praia);
          esticada a toda a largura ficava um borrão. Ao lado do texto é o que
          ela foi feita para ser, e é o que o site oficial faz. */}
      <section className="che-hero">
        <HeroDecoracoes />
        <div className="che-hero-in">
          <div className="che-hero-topo">
          {/* A entrada do hero é escalonada pela ordem de LEITURA: distintivo,
              título, texto, acções, e o cartão de compra por último. `--i` diz
              a posição; o CSS põe os 70ms entre cada. */}
          <div className="che-hero-copy">
            <span className="bzlp-badge che-entra">{i.hero.badge}</span>
            {/* Palavra a palavra, e não em bloco: o título é a primeira coisa
                que se lê e assim lê-se na ordem em que foi escrito. Cada
                palavra é um `inline-block` próprio — o espaço entre elas fica
                no markup para a frase continuar a ser uma frase para quem
                copia ou para um leitor de ecrã. */}
            <h1>
              {i.hero.h1.split(" ").map((palavra, n) => (
                <span className="che-palavra che-entra" key={`${palavra}-${n}`}
                  style={{ "--i": 1 + n * 0.6 } as React.CSSProperties}>
                  {palavra}
                </span>
              )).reduce<React.ReactNode[]>((acc, el, n) => (n === 0 ? [el] : [...acc, " ", el]), [])}
              {" "}
              <span className="che-destaque che-entra"
                style={{ "--i": 1 + i.hero.h1.split(" ").length * 0.6 } as React.CSSProperties}>
                {i.hero.h1destaque}
              </span>
            </h1>
            <p className="che-entra" style={{ "--i": 3 } as React.CSSProperties}>{i.hero.lead}</p>
            {/* Os dois botões e a linha do grupo saíram daqui. O cartão de
                pesquisa logo abaixo É a acção do hero, e um par de botões por
                cima dele era um segundo conjunto de acções a competir com a
                primeira — sem contar que "Comprar bilhete" já está na barra.
                Quem procura horários ou grupos tem-nos na navegação. */}
          </div>
          {/* Paralaxe ao rolar e inclinação a seguir o ponteiro — ver
              HeroArte. `width`/`height` reais do ficheiro ficam lá dentro:
              reservam o espaço e evitam o salto da página enquanto carrega. */}
          <HeroArte src="/landing/cheetah/hero-autocarro.png" alt={i.hero.fotoAlt} />
          </div>

          {/* A compra começa DENTRO da chapa, e não a cavalo dela.
              Estava a seguir ao hero, com margem negativa a puxá-lo para cima:
              o desenho lia-se bem, mas a conta nunca fechava — mesmo com a
              chapa no mínimo, a coluna de texto mais o respiro já valiam
              548px, e somados à barra e aos 435px que o cartão mede em ecrã
              médio davam 1001px numa dobra de 900. Aqui dentro, a chapa e o
              cartão são um bloco só e cabem na primeira vista por construção,
              em vez de por subtracção. */}
          <div className="che-hero-busca che-entra" style={{ "--i": 3.8 } as React.CSSProperties}>
            <HeroBusca textos={t.heroBusca} variante="barra" />
          </div>
        </div>

        <OndaCheetah />
      </section>

      {/* PROVAS — os quatro pontos que o site oficial destaca. */}
      <section className="bzlp-sec tem-onda" id="porque">
        <div className="bzlp-wrap">
          <CheRevela>
            <div className="bzlp-sechead">
              <div className="bzlp-kicker">{i.provas.kicker}</div>
              <h2 className="bzlp-h2">{i.provas.h2}</h2>
            </div>
          </CheRevela>
          <ul className="che-provas">
            {i.provas.itens.map((p, n) => {
              const Icone = PROVAS_ICON[n];
              return (
                <CheRevela as="li" className="che-prova" key={p.t} ordem={n}>
                  <span className="che-prova-ico"><Icone size={22} aria-hidden /></span>
                  <h3>{p.t}</h3>
                  <p>{p.p}</p>
                </CheRevela>
              );
            })}
          </ul>
        </div>
        {/* As provas entregam a página à faixa preta dos serviços. */}
        <OndaCheetah className="che-onda--seccao che-onda--para-escuro" />
      </section>

      {/* SERVIÇOS — os três do site oficial. */}
      <section className="bzlp-sec che-sec-preta tem-onda" id="servicos">
        <div className="bzlp-wrap">
          <CheRevela>
            <div className="bzlp-sechead">
              <div className="bzlp-kicker">{i.servicos.kicker}</div>
              <h2 className="bzlp-h2">{i.servicos.h2}</h2>
            </div>
          </CheRevela>
          {/* Três cartões de cor cheia — vermelho, branco, laranja. É a peça
              mais reconhecível do site oficial. A cor é estrutura e não texto,
              por isso mora aqui e não no dicionário. */}
          <div className="che-servicos" onMouseLeave={() => setServicoActivo(null)}>
            {i.servicos.itens.map((s, n) => (
              <CheRevela key={s.id} ordem={n}>
                <article
                  className={`che-servico ${SERVICOS_COR[n]}`}
                  data-recuado={servicoActivo !== null && servicoActivo !== n ? "" : undefined}
                  onMouseEnter={() => setServicoActivo(n)}
                >
                  <span className="che-servico-etiq">{s.etiqueta}</span>
                  <h3>{s.t1} <span>{s.t2}</span></h3>
                  <p className="che-servico-sub">{s.sub}</p>
                  <div className="che-servico-body">
                    <p>{s.p}</p>
                    <p>{s.extra}</p>
                  </div>
                  <Link className="che-servico-cta" to={SERVICOS_LINK[n]}>
                    {s.cta} <ArrowRight size={15} aria-hidden />
                  </Link>
                </article>
              </CheRevela>
            ))}
          </div>
          <div style={{ textAlign: "center", marginTop: 30 }}>
            <Link to="/cheetah-express/horarios" className="bzlp-btn outline">
              {i.servicos.botao} <ArrowRight size={17} aria-hidden />
            </Link>
          </div>
        </div>
        {/* Sai do preto para o branco dos parceiros. */}
        <OndaCheetah className="che-onda--seccao che-onda--para-claro" />
      </section>

      {/* PARCEIROS */}
      <section className="bzlp-sec tem-onda" id="parceiros">
        <div className="bzlp-wrap">
          <CheRevela>
            <div className="bzlp-sechead">
              <div className="bzlp-kicker">{i.parceiros.kicker}</div>
              <h2 className="bzlp-h2">{i.parceiros.h2}</h2>
              <p className="bzlp-lead">{i.parceiros.lead}</p>
            </div>
          </CheRevela>
          {/* TRES COPIAS da mesma fila. A fita desliza exactamente um terço, e
              ao fim do percurso a segunda copia está onde a primeira estava —
              é assim que o laço fecha sem se ver o corte. Só a primeira fala:
              as outras duas levam `aria-hidden` e texto alternativo vazio,
              para um leitor de ecrã anunciar os cinco parceiros uma vez e não
              quinze. Ver `.che-parceiros` em `cheetah.css`. */}
          <div className="che-parceiros-caixa">
            <ul className="che-parceiros">
              {[0, 1, 2].flatMap((copia) =>
                PARCEIROS.map((p) => (
                  <li
                    aria-hidden={copia > 0 || undefined}
                    className="che-parceiro"
                    key={`${copia}-${p.f}`}
                  >
                    {/* `eager` com prioridade baixa, e não `lazy`: em `lazy` os
                        primeiros ficheiros mediam zero e a faixa abria vazia. */}
                    <img
                      src={`/landing/cheetah/parceiros/${p.f}`}
                      alt={copia === 0 ? p.nome : ""}
                      loading="eager"
                      fetchPriority="low"
                      decoding="async"
                    />
                  </li>
                )),
              )}
            </ul>
          </div>
        </div>
        {/* A chamada final é escura: a onda entra nela. */}
        <OndaCheetah className="che-onda--seccao che-onda--para-escuro" />
      </section>

      {/* CHAMADA FINAL — dois caminhos: comprar, ou falar connosco. */}
      <section className="che-cta" id="contacto">
        <div className="bzlp-wrap che-cta-in">
          <div>
            <h2>{i.cta.h2}</h2>
            <p>{i.cta.p}</p>
          </div>
          <div className="che-cta-btns">
            <Link to="/comprar" className="bzlp-btn gold">
              {t.comum.comprarBilhete} <ArrowRight size={17} aria-hidden />
            </Link>
            <a href={pedido(t.comum.pedirOrcamento)} className="bzlp-btn outline">
              {t.comum.pedirOrcamento}
            </a>
          </div>
        </div>
      </section>
    </CheetahPagina>
  );
}
