import { Link } from "react-router-dom";
import { ArrowRight, Bus, Clock3, Snowflake, Wifi } from "lucide-react";
import CheRevela from "./CheRevela";
import HeroArte from "./HeroArte";
import RotaParagens from "./RotaParagens";
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

export default function CheetahLandingPage() {
  const { t } = useCheetahCopy();
  const i = t.inicio;

  useCheetahMeta(i.meta.titulo, i.meta.descricao);

  return (
    <CheetahPagina>
      {/* HERO — duas colunas. A única imagem que a empresa tem é uma
          composição VERTICAL recortada (o passageiro, a carrinha, a praia);
          esticada a toda a largura ficava um borrão. Ao lado do texto é o que
          ela foi feita para ser, e é o que o site oficial faz. */}
      <section className="che-hero">
        <div className="che-hero-in">
          <div className="che-hero-topo">
          {/* A entrada do hero é escalonada pela ordem de LEITURA: distintivo,
              título, texto, acções, e o cartão de compra por último. `--i` diz
              a posição; o CSS põe os 70ms entre cada. */}
          <div className="che-hero-copy">
            <span className="bzlp-badge che-entra">{i.hero.badge}</span>
            <h1 className="che-entra" style={{ "--i": 1 } as React.CSSProperties}>
              {i.hero.h1} <span>{i.hero.h1destaque}</span>
            </h1>
            <p className="che-entra" style={{ "--i": 2 } as React.CSSProperties}>{i.hero.lead}</p>
            <div className="che-hero-cta che-entra" style={{ "--i": 3 } as React.CSSProperties}>
              <Link to="/comprar" className="bzlp-btn gold">
                {t.comum.comprarBilhete} <ArrowRight size={17} aria-hidden />
              </Link>
              <Link to="/cheetah-express/horarios" className="bzlp-btn outline">
                {t.comum.verHorarios}
              </Link>
            </div>
            <p className="che-hero-grupo che-entra" style={{ "--i": 4 } as React.CSSProperties}>
              {i.hero.grupo}{" "}
              <Link to="/cheetah-express/contactos">{t.comum.falarConnosco}</Link>
            </p>
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
          <div className="che-hero-busca che-entra" style={{ "--i": 5 } as React.CSSProperties}>
            <HeroBusca textos={t.heroBusca} />
          </div>
        </div>
      </section>

      {/* PROVAS — os quatro pontos que o site oficial destaca. */}
      <section className="bzlp-sec" id="porque">
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
      </section>

      {/* SERVIÇOS — os três do site oficial. */}
      <section className="bzlp-sec alt" id="servicos">
        <div className="bzlp-wrap">
          <CheRevela>
            <div className="bzlp-sechead">
              <div className="bzlp-kicker">{i.servicos.kicker}</div>
              <h2 className="bzlp-h2">{i.servicos.h2}</h2>
            </div>
          </CheRevela>
          <div className="che-servicos">
            {i.servicos.itens.map((s, n) => (
              <CheRevela key={s.id} ordem={n}>
                <article className="che-servico">
                  <div className="che-servico-head">
                    <span className="che-servico-etiq">{s.etiqueta}</span>
                    <h3>{s.t}</h3>
                  </div>
                  <div className="che-servico-body">
                    <p>{s.p}</p>
                    <p className="che-servico-extra">{s.extra}</p>
                  </div>
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
      </section>

      {/* A ROTA — as paragens fixas, de sul para norte. */}
      <section className="bzlp-sec" id="rota">
        <div className="bzlp-wrap">
          <CheRevela>
            <div className="bzlp-sechead">
              <div className="bzlp-kicker">{i.rota.kicker}</div>
              <h2 className="bzlp-h2">{i.rota.h2}</h2>
              <p className="bzlp-lead">{i.rota.lead}</p>
            </div>
          </CheRevela>
          <div className="che-rota">
            {i.rota.lados.map((lado, n) => (
              <CheRevela key={lado.t} ordem={n}>
                <div className="che-rota-lado">
                  <h3>{lado.t}</h3>
                  <RotaParagens paragens={lado.paragens} />
                </div>
              </CheRevela>
            ))}
          </div>
        </div>
      </section>

      {/* PARCEIROS */}
      <section className="bzlp-sec alt" id="parceiros">
        <div className="bzlp-wrap">
          <CheRevela>
            <div className="bzlp-sechead">
              <div className="bzlp-kicker">{i.parceiros.kicker}</div>
              <h2 className="bzlp-h2">{i.parceiros.h2}</h2>
              <p className="bzlp-lead">{i.parceiros.lead}</p>
            </div>
          </CheRevela>
          <ul className="che-parceiros">
            {PARCEIROS.map((p) => (
              <li className="che-parceiro" key={p.f}>
                {/* `eager` com prioridade baixa, e não `lazy`: em `lazy` os
                    primeiros ficheiros mediam zero e a faixa abria vazia. */}
                <img
                  src={`/landing/cheetah/parceiros/${p.f}`}
                  alt={p.nome}
                  loading="eager"
                  fetchPriority="low"
                  decoding="async"
                />
              </li>
            ))}
          </ul>
        </div>
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
