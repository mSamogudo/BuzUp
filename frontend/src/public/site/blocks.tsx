/**
 * Blocos do site público, tal como desenhados nos protótipos.
 *
 * O conteúdo chega já traduzido pelo endpoint público
 * (`/api/public/pages/{slug}/{locale}/`) — aqui só se desenha. O mesmo
 * componente serve a pré-visualização ao vivo do editor do CMS, para o que se
 * vê no editor ser exactamente o que vai para o ar.
 */
import { createContext, useContext, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { sanitizeRichText } from "../../admin/cms/blocks";
import { ServiceRequestForm } from "./ServiceRequestForm";
import {
  MockCartoes,
  MockCompra,
  MockFrota,
  MockPasso,
  MockReceita,
  MockValidacao,
  PortalPreview,
} from "./mockups";

export interface PublicPlan {
  id: number;
  name: string;
  price_label: string;
  unit: string;
  cta_label: string;
  items: string[];
  highlighted: boolean;
  position: number;
}

export interface PublicPlanFeature {
  label: string;
  urban: string;
  intercity: string;
  institutional: string;
  position: number;
}

export interface PublicEcoSystem {
  id: number;
  name: string;
  logo: string;
  url: string;
  note: string;
  position: number;
}

export interface PublicBlock {
  type: string;
  position: number;
  content: Record<string, any>;
}

interface SiteDataValue {
  locale: "pt" | "en";
  plans: PublicPlan[];
  features: PublicPlanFeature[];
  systems: PublicEcoSystem[];
  /** Na pré-visualização do editor os botões não navegam. */
  inert?: boolean;
}

const SiteData = createContext<SiteDataValue>({ locale: "pt", plans: [], features: [], systems: [] });

export const SiteDataProvider = SiteData.Provider;
export const useSiteData = () => useContext(SiteData);

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function list(value: unknown): any[] {
  return Array.isArray(value) ? value : [];
}

/** Um CTA do CMS: rótulo só, sem destino próprio — o destino vem do tipo. */
function Cta({ label, to, variant }: { label: string; to: string; variant: string }) {
  const { inert } = useSiteData();
  if (!label) return null;
  if (inert) {
    return (
      <span aria-disabled="true" className={`bzs-cta ${variant}`}>
        {label}
      </span>
    );
  }
  if (to.startsWith("http") || to.startsWith("mailto:")) {
    return (
      <a className={`bzs-cta ${variant}`} href={to} rel="noopener noreferrer" target="_blank">
        {label}
      </a>
    );
  }
  if (to.startsWith("#")) {
    return (
      <a className={`bzs-cta ${variant}`} href={to}>
        {label}
      </a>
    );
  }
  return (
    <Link className={`bzs-cta ${variant}`} to={to}>
      {label}
    </Link>
  );
}

function SectionHead({ h2, lead, center = true }: { h2: string; lead?: string; center?: boolean }) {
  if (!h2 && !lead) return null;
  return (
    <header className={`bzs-sectionhead${center ? " bzs-sectionhead-center" : ""}`}>
      {h2 ? <h2 className="bzs-h2">{h2}</h2> : null}
      {lead ? <p className="bzs-sublead">{lead}</p> : null}
    </header>
  );
}

/* -------------------------------------------------------------------------- */

function Heroi({ content, anchor }: { content: Record<string, any>; anchor?: string }) {
  const chips = list(content.chips);
  return (
    <>
    <div className="bzs-hero" id={anchor}>
      {text(content.badge) ? (
        <span className="bzs-badge">
          <i aria-hidden="true" />
          {content.badge}
        </span>
      ) : null}
      <h1 className="bzs-h1">
        {text(content.h1a)}
        {text(content.h1b) ? <span>{content.h1b}</span> : null}
      </h1>
      {text(content.lead) ? <p className="bzs-lead">{content.lead}</p> : null}
      <div className="bzs-ctas">
        <Cta label={text(content.cta1)} to="/contactos" variant="bzs-cta-primary" />
        <Cta label={text(content.cta2)} to="/comprar" variant="bzs-cta-soft" />
        <Cta label={text(content.cta3)} to="#produto" variant="bzs-cta-ghost" />
      </div>
      {chips.length ? (
        <div className="bzs-chips">
          {chips.map((chip, i) => (
            <span className="bzs-chip" key={i}>
              {String(chip)}
            </span>
          ))}
        </div>
      ) : null}
    </div>
    <HeroiPreview content={content} />
    </>
  );
}

/**
 * Pré-visualização do portal por baixo do herói, com as quatro etiquetas
 * flutuantes. É decoração: só aparece quando o herói traz as etiquetas.
 */
function HeroiPreview({ content }: { content: Record<string, any> }) {
  const tags = list(content.tags);
  if (!tags.length) return null;
  const pontos = ["#2A9D8F", "#2D8CF0", "#FFB703", "#0D3B66"];
  return (
    <div className="bzs-heroshot">
      {tags.slice(0, 4).map((tag, i) => (
        <span className={`bzs-heroshot-tag bzs-heroshot-tag-${i + 1}`} key={i}>
          <i style={{ background: pontos[i] }} />
          {String(tag)}
        </span>
      ))}
      <PortalPreview />
    </div>
  );
}

function Logos({ content, anchor }: { content: Record<string, any>; anchor?: string }) {
  const items = list(content.items).filter((item) => text(item.url) || text(item.src));
  // A tira do desenho corre em ciclo: a lista sai duplicada e a animação
  // desloca-se exactamente metade, por isso a emenda nunca se vê.
  const ciclo = items.length ? [...items, ...items] : [];
  return (
    <section className="bzs-logos" id={anchor}>
      {text(content.h2) ? <h2 className="bzs-logos-title">{content.h2}</h2> : null}
      {text(content.lead) ? <p className="bzs-logos-lead">{content.lead}</p> : null}
      <div className="bzs-logos-mask">
        <div className="bzs-logos-track">
          {ciclo.map((item, i) => {
            const alt = i < items.length ? text(item.alt) : "";
            const claro = text(item.url) || text(item.src);
            const escuro = text(item.url_dark);
            return (
              <span className="bzs-logos-pill" key={i}>
                <img alt={alt} data-logo={escuro ? "light" : undefined} src={claro} />
                {escuro ? <img alt="" data-logo="dark" src={escuro} /> : null}
              </span>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/** As miniaturas do desenho, pela ordem dos cinco cartões de recursos. */
const MOCKS_RECURSOS = [MockCompra, MockValidacao, MockCartoes, MockReceita];

/**
 * Cartões de recursos.
 *
 * O desenho põe cinco: três em cima, e em baixo um estreito mais um largo com
 * o painel do mapa ao lado. Cada um leva a sua miniatura, encostada ao fundo do
 * cartão. Com um número de cartões diferente do desenho, cai numa grelha de
 * três colunas — o CMS pode acrescentar ou tirar sem partir a página.
 */
function Recursos({ content, anchor }: { content: Record<string, any>; anchor?: string }) {
  const items = list(content.items);
  const comoDesenhado = items.length === 5;

  const cartao = (item: any, i: number, largo = false) => {
    const Mock = MOCKS_RECURSOS[i];
    const bullets = list(item.bullets);
    return (
      <article className={`bzs-feat${largo ? " bzs-feat-wide" : ""}`} key={i}>
        <div className="bzs-feat-copy">
          <h3>{text(item.title)}</h3>
          <p>{text(item.text)}</p>
          {bullets.length ? (
            <ul className="bzs-bullets">
              {bullets.map((bullet, j) => (
                <li key={j}>{String(bullet)}</li>
              ))}
            </ul>
          ) : null}
        </div>
        {largo ? (
          <div className="bzs-feat-aside">
            <MockFrota aviso={text(content.map_note)} titulo={text(content.map_title)} />
          </div>
        ) : Mock ? (
          <div className="bzs-feat-mock">
            <Mock />
          </div>
        ) : null}
      </article>
    );
  };

  return (
    <section className="bzs-section bzs-features" id={anchor}>
      <div className="bzs-wrap">
        <SectionHead h2={text(content.h2)} lead={text(content.lead)} />
        {comoDesenhado ? (
          <>
            <div className="bzs-feat-row3">{items.slice(0, 3).map((item, i) => cartao(item, i))}</div>
            <div className="bzs-feat-row2">
              {cartao(items[3], 3)}
              {cartao(items[4], 4, true)}
            </div>
          </>
        ) : (
          <div className="bzs-feat-row3">{items.map((item, i) => cartao(item, i))}</div>
        )}
      </div>
    </section>
  );
}

/**
 * "Começar em três passos": três painéis numerados, cada um com duas
 * miniaturas, e o painel do portal de gestão por baixo.
 */
function Passos({ content, anchor }: { content: Record<string, any>; anchor?: string }) {
  const steps = list(content.steps);
  return (
    <section className="bzs-section bzs-steps" id={anchor}>
      <div className="bzs-wrap">
        <SectionHead h2={text(content.h2)} lead={text(content.lead)} />
        <div className="bzs-steps-row">
          {steps.map((step, i) => (
            <article className="bzs-step" key={i}>
              <span className="bzs-step-n">{text(step.n)}</span>
              <h3>{text(step.title)}</h3>
              <p>{text(step.text)}</p>
              <MockPasso
                m1={text(step.m1)}
                m1cta={text(step.m1cta)}
                m2={text(step.m2)}
                m2a={text(step.m2a)}
                m2b={text(step.m2b)}
              />
            </article>
          ))}
        </div>
        {text(content.panel_title) ? (
          <div className="bzs-steps-panel">
            <b>{content.panel_title}</b>
            <p>{text(content.panel_text)}</p>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function Porque({ content, anchor }: { content: Record<string, any>; anchor?: string }) {
  const stats = list(content.stats);
  return (
    <section className="bzs-wrap bzs-section" id={anchor}>
      <SectionHead h2={text(content.h2)} lead={text(content.lead)} />
      <div className="bzs-grid bzs-grid-4">
        {stats.map((stat, i) => (
          <article className="bzs-card bzs-card-soft" key={i}>
            <div className="bzs-stat">
              <span className="bzs-stat-value">{text(stat.value)}</span>
              <span className="bzs-stat-label">{text(stat.label)}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function Casos({ content, anchor }: { content: Record<string, any>; anchor?: string }) {
  const items = list(content.items);
  return (
    <section className="bzs-wrap bzs-section" id={anchor}>
      <SectionHead h2={text(content.h2)} lead={text(content.lead)} />
      <div className="bzs-grid bzs-grid-3">
        {items.map((item, i) => (
          <article className="bzs-card" key={i}>
            <span className="bzs-label">{text(item.kind)}</span>
            <p className="bzs-quote">{text(item.quote)}</p>
            <span className="bzs-who">{text(item.who)}</span>
          </article>
        ))}
      </div>
    </section>
  );
}

function Precos({ content, anchor }: { content: Record<string, any>; anchor?: string }) {
  const { plans, features } = useSiteData();
  const ids = list(content.plan_ids);
  const chosen = ids.length ? plans.filter((p) => ids.includes(p.id)) : plans;
  const notes = list(content.notes);
  const col = text(content.table_col);

  return (
    <section className="bzs-wrap bzs-section" id={anchor}>
      <SectionHead h2={text(content.h2)} lead={text(content.lead)} />

      <div className="bzs-grid bzs-grid-3">
        {chosen.map((plan) => (
          <article className={`bzs-plan${plan.highlighted ? " bzs-plan-featured" : ""}`} key={plan.id}>
            {plan.highlighted ? <span className="bzs-plan-badge">Mais procurado</span> : null}
            <span className="bzs-plan-name">{plan.name}</span>
            <span className="bzs-plan-price">{plan.price_label}</span>
            <span className="bzs-plan-unit">{plan.unit}</span>
            <ul className="bzs-bullets">
              {plan.items.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
            <Cta label={plan.cta_label} to="/contactos" variant="bzs-cta-ghost" />
          </article>
        ))}
      </div>

      {notes.length ? (
        <div className="bzs-grid bzs-grid-3" style={{ marginTop: 20 }}>
          {notes.map((note, i) => (
            <article className="bzs-card bzs-card-soft" key={i}>
              <h3 style={{ fontSize: 16 }}>{text(note.h)}</h3>
              <p>{text(note.p)}</p>
            </article>
          ))}
        </div>
      ) : null}

      {features.length && col ? (
        <>
          <div className="bzs-tablecard" style={{ marginTop: 34 }}>
            <table className="bzs-table">
              <thead>
                <tr>
                  <th>{col}</th>
                  {chosen.map((plan) => (
                    <th key={plan.id}>{plan.name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {features.map((feature, i) => (
                  <tr key={i}>
                    <td>{feature.label}</td>
                    <td>{feature.urban}</td>
                    <td>{feature.intercity}</td>
                    <td>{feature.institutional}</td>
                  </tr>
                ))}
                {text(content.table_foot) ? (
                  <tr>
                    <td style={{ fontWeight: 700, color: "var(--text)" }}>{content.table_foot}</td>
                    {chosen.map((plan) => (
                      <td key={plan.id}>
                        <Cta label={text(content.quote)} to="/contactos" variant="bzs-cta-ghost bzs-cta-sm" />
                      </td>
                    ))}
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>

          {/* Em mobile a tabela passa a lista de notas. */}
          <div className="bzs-tablelist" style={{ marginTop: 24 }}>
            {features.map((feature, i) => (
              <div className="bzs-tablelist-item" key={i}>
                <strong>{feature.label}</strong>
                <span>
                  {chosen[0]?.name || "Urbano"} <b>{feature.urban}</b>
                </span>
                <span>
                  {chosen[1]?.name || "Interurbano"} <b>{feature.intercity}</b>
                </span>
                <span>
                  {chosen[2]?.name || "Institucional"} <b>{feature.institutional}</b>
                </span>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}

function Faq({ content, anchor }: { content: Record<string, any>; anchor?: string }) {
  const items = list(content.items);
  return (
    <section className="bzs-narrow bzs-section" id={anchor}>
      <SectionHead h2={text(content.h2)} lead={text(content.lead)} />
      <div className="bzs-faq">
        {items.map((item, i) => (
          <details key={i}>
            <summary>{text(item.q)}</summary>
            <p>{text(item.a)}</p>
          </details>
        ))}
      </div>
    </section>
  );
}

function Form({ content, anchor }: { content: Record<string, any>; anchor?: string }) {
  const { inert } = useSiteData();
  const facts = list(content.facts);
  return (
    <section className="bzs-wrap bzs-section" id={anchor}>
      <div className="bzs-formgrid">
        <div>
          <h2 className="bzs-h2">{text(content.h2)}</h2>
          {text(content.lead) ? <p className="bzs-sublead">{content.lead}</p> : null}
          {facts.length ? (
            <ul className="bzs-facts">
              {facts.map((fact, i) => (
                <li key={i}>{String(fact)}</li>
              ))}
            </ul>
          ) : null}
        </div>
        <ServiceRequestForm
          fields={list(content.fields)}
          inert={inert}
          note={text(content.note)}
          sentText={text(content.sent_text)}
          sentTitle={text(content.sent_title)}
          submitLabel={text(content.submit)}
        />
      </div>
    </section>
  );
}

function Eco({ content, anchor }: { content: Record<string, any>; anchor?: string }) {
  const { systems } = useSiteData();
  const ids = list(content.system_ids);
  const chosen = ids.length ? systems.filter((s) => ids.includes(s.id)) : systems;
  return (
    <section className="bzs-wrap bzs-section" id={anchor}>
      <div className="bzs-eco">
        <div>
          {text(content.label) ? <span className="bzs-label">{content.label}</span> : null}
          <h2 className="bzs-h2" style={{ marginTop: 12 }}>
            {text(content.h2)}
          </h2>
          {text(content.lead) ? <p className="bzs-sublead">{content.lead}</p> : null}
          {text(content.note) ? (
            <p className="bzs-eco-note" style={{ marginTop: 16 }}>
              {content.note}
            </p>
          ) : null}
        </div>
        <div className="bzs-eco-logos">
          {chosen.map((system) => (
            <a
              className="bzs-eco-logo"
              href={system.url || "#"}
              key={system.id}
              rel="noopener noreferrer"
              target="_blank"
              title={system.name}
            >
              {system.logo ? <img alt={system.name} src={system.logo} /> : <span className="bzs-label">{system.name}</span>}
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}

function CtaBand({ content, anchor }: { content: Record<string, any>; anchor?: string }) {
  const facts = list(content.facts);
  return (
    <section className="bzs-ctaband" id={anchor}>
      <div className="bzs-ctaband-in">
        <h2>{text(content.h2)}</h2>
        {text(content.lead) ? <p>{content.lead}</p> : null}
        <div className="bzs-ctas">
          <Cta label={text(content.cta1)} to="/contactos" variant="bzs-cta-white" />
          <Cta label={text(content.cta2)} to="/precos" variant="bzs-cta-onnavy" />
        </div>
        {facts.length ? (
          <ul className="bzs-ctafacts">
            {facts.map((fact, i) => (
              <li key={i}>
                <i aria-hidden="true">✓</i>
                {String(fact)}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </section>
  );
}

function RichText({ content, anchor }: { content: Record<string, any>; anchor?: string }) {
  const html = sanitizeRichText(text(content.html));
  return (
    <section className="bzs-narrow bzs-section" id={anchor}>
      <SectionHead center={false} h2={text(content.h2)} lead={text(content.lead)} />
      {html ? (
        <div
          className="bzs-rich"
          // O HTML já passou pelo saneador: só h2, h3, p, ul, ol, a, strong, em.
          dangerouslySetInnerHTML={{ __html: html }}
        />
      ) : null}
    </section>
  );
}

function Media({ content }: { content: Record<string, any> }) {
  const src = text(content.url) || text(content.src);
  if (!src) return null;
  const full = text(content.width) === "full";
  return (
    <figure className={full ? "bzs-section" : "bzs-wrap bzs-section"} style={{ margin: 0 }}>
      <img alt={text(content.caption)} src={src} style={{ width: "100%", borderRadius: 22, display: "block" }} />
      {text(content.caption) ? (
        <figcaption className="bzs-sublead" style={{ marginTop: 12, textAlign: "center" }}>
          {content.caption}
        </figcaption>
      ) : null}
    </figure>
  );
}

const RENDERERS: Record<string, (props: { content: Record<string, any>; anchor?: string }) => ReactNode> = {
  heroi: Heroi,
  logos: Logos,
  recursos: Recursos,
  passos: Passos,
  porque: Porque,
  casos: Casos,
  precos: Precos,
  faq: Faq,
  form: Form,
  eco: Eco,
  cta: CtaBand,
  richtext: RichText,
  media: Media,
};

/** Âncora do menu por tipo de bloco. Só o primeiro de cada tipo a leva. */
const ANCHORS: Record<string, string> = {
  heroi: "top",
  recursos: "recursos",
  passos: "produto",
  porque: "porque",
  casos: "casos",
  precos: "precos",
  faq: "faq",
  form: "contacto",
  cta: "contacto",
  eco: "ecossistema",
  richtext: "produto",
};

export function BlockRenderer({ blocks }: { blocks: PublicBlock[] }) {
  // Tipos diferentes podem pedir a mesma âncora (`form` e `cta` são ambos
  // "contacto"): guarda-se a ÂNCORA usada, não o tipo, para nunca sair um id
  // repetido na página.
  const usados = new Set<string>();
  return (
    <>
      {blocks.map((block, i) => {
        const Renderer = RENDERERS[block.type];
        if (!Renderer) return null;
        const ancora = ANCHORS[block.type];
        const primeiro = Boolean(ancora) && !usados.has(ancora);
        if (primeiro) usados.add(ancora);
        return (
          <Renderer
            anchor={primeiro ? ancora : undefined}
            content={block.content || {}}
            key={`${block.type}-${block.position}-${i}`}
          />
        );
      })}
    </>
  );
}
