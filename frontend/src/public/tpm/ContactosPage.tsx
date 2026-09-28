import { Link } from "react-router-dom";
import { ArrowUpRight, Mail, MapPin, Phone, Ticket } from "lucide-react";
import Reveal from "../landing/Reveal";
import TpmFormularioPedido from "./TpmFormularioPedido";
import TpmPagina, {
  EMAIL, MORADA, TELEFONE, TELEFONE_FIXO, TELEFONE_FIXO_HREF, TELEFONE_HREF,
  TpmIntro, useTpmMeta,
} from "./TpmChrome";
import { useTpmCopy } from "./tpm-copy";

/* Contactos.
 *
 * A morada completa é a que a empresa publica — a etiqueta que o Google mostra
 * no mapa ("2039 Rua da Resistência") é geocodificação dele, não o endereço que
 * a TPM-TUR dá de si própria. Vale o da empresa; o mapa mostra o que mostrar.
 *
 * A MORADA NÃO SE TRADUZ, nem com a página em inglês: é um endereço físico, e
 * quem o lê tem de o conseguir dizer a um motorista de táxi em Maputo.
 *
 * Não há horário de atendimento nesta página porque não há nenhum confirmado.
 * Inventar "segunda a sexta, 8h-17h" seria mandar alguém a uma porta fechada. */

/* O embed oficial do estabelecimento, tal como está no site da TPM-TUR: o `pb`
 * carrega o place id (0x1ee69ba9923f3131:0xc237b107e4159e4b), e por isso o pino
 * cai na sede e não numa aproximação da rua. */
const MAPA =
  "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3587.5037755073054!2d32.587324599999995" +
  "!3d-25.9515135!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x1ee69ba9923f3131" +
  "%3A0xc237b107e4159e4b!2sTPM%20TUR!5e0!3m2!1spt-PT!2smz!4v1751969942071!5m2!1spt-PT!2smz";

const MAPA_LINK =
  "https://www.google.com/maps/search/?api=1&query=TPM+TUR+Rua+da+Resistencia+Maputo";

export default function ContactosPage() {
  const { t } = useTpmCopy();
  const c = t.contactos;
  useTpmMeta(c.meta.titulo, c.meta.descricao);

  return (
    <TpmPagina activa="/tpm-tur/contactos">
      <TpmIntro migalha={c.migalha} titulo={c.titulo} descricao={c.descricao} />

      <section className="bzlp-sec">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="tpm-contactos">
              <div className="tpm-contactos-lista">
                <article className="tpm-contacto-cartao">
                  <span className="tpm-contacto-ico"><Phone size={22} aria-hidden /></span>
                  <h2>{c.ligue}</h2>
                  <a href={TELEFONE_HREF}>{TELEFONE}</a>
                  <a href={TELEFONE_FIXO_HREF}>{TELEFONE_FIXO}</a>
                </article>

                <article className="tpm-contacto-cartao">
                  <span className="tpm-contacto-ico"><Mail size={22} aria-hidden /></span>
                  <h2>{c.escreva}</h2>
                  <a href={`mailto:${EMAIL}`}>{EMAIL}</a>
                </article>

                <article className="tpm-contacto-cartao">
                  <span className="tpm-contacto-ico"><MapPin size={22} aria-hidden /></span>
                  <h2>{c.encontre}</h2>
                  <p>
                    Rua da Resistência, Parcela Nº 24<br />
                    Bairro de Maxaquene C, 1º Andar<br />
                    Maputo, Moçambique<br />
                    Código postal 1104
                  </p>
                </article>
              </div>

              {/* O formulário ocupa a coluna larga, onde estava o mapa. Era
                  uma ilha de 820px centrada na secção seguinte: não alinhava
                  nem com os cartões à esquerda nem com o mapa à direita, e
                  quem chegava à página de contactos tinha de rolar para
                  encontrar a única coisa que ali se faz. */}
              <TpmFormularioPedido />
            </div>
          </Reveal>
        </div>
      </section>

      {/* O mapa desceu para aqui, à largura toda. Ao lado dos cartões estava
          a ocupar o melhor lugar da página para mostrar uma morada que o
          cartão "Encontre-nos" já escreve por extenso. */}
      <section className="bzlp-sec alt">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="tpm-mapa">
              {/* O `title` não estava no original e é o que um leitor de ecrã
                  anuncia ao chegar aqui: sem ele, o enquadramento é só
                  "frame". O `loading="lazy"` evita que o mapa do Google pese
                  no carregamento de quem nunca chega a rolar até aqui. */}
              <iframe
                src={MAPA}
                title={c.mapaTitulo}
                loading="lazy"
                allowFullScreen
                referrerPolicy="no-referrer-when-downgrade"
              />
              <div className="tpm-mapa-barra">
                <span>{MORADA}</span>
                <a href={MAPA_LINK} target="_blank" rel="noreferrer">
                  {c.abrirMapa} <ArrowUpRight size={16} aria-hidden />
                </a>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <section className="tpm-escolha">
        <div className="bzlp-wrap">
          <div className="tpm-escolha-head">
            <h2>{c.banda.h2}</h2>
            <p>{c.banda.p}</p>
          </div>
          {/* So o bilhete. "Pedir orcamento" vivia aqui tambem, e com o
              formulario logo acima passou a ser um atalho que salta por cima
              dele — duas portas para a mesma sala, e a pior primeiro. */}
          <div style={{ display: "flex", justifyContent: "center" }}>
            <Link to="/comprar" className="bzlp-btn gold">
              <Ticket size={17} aria-hidden /> {c.banda.btn}
            </Link>
          </div>
        </div>
      </section>
    </TpmPagina>
  );
}
