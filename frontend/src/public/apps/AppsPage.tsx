/**
 * Site público B.4 — Apps.
 *
 * Os cinco produtos com o vocabulário do Portal: passageiro, agente,
 * motorista, POS de balcão e validador de bordo. Os ecrãs e os rótulos são os
 * de `docs/design-handoff/design/Apps BusUp.dc.html`.
 *
 * A moldura (menu e rodapé) vem do CMS, como no resto do site.
 */
import { useUi } from "../../ui/UiPreferences";
import { SiteFooter, SiteHeader } from "../site/SiteChrome";
import { useSite } from "../site/usePublicSite";
import { usePageMeta } from "../site/usePageMeta";
import "../site/site.css";
import "./apps.css";

interface Screen {
  step: string;
  title: string;
  lines: string[];
  cta?: string;
}

interface Product {
  key: string;
  name: string;
  audience: string;
  lead: string;
  screens: Screen[];
}

const PRODUCTS: Product[] = [
  {
    key: "passageiro",
    name: "App do passageiro",
    audience: "Android · quem viaja",
    lead: "Comprar, pagar e mostrar o bilhete sem passar pela bilheteira.",
    screens: [
      { step: "01", title: "Entrar", lines: ["Telefone", "Recebe um código por SMS"], cta: "Receber código" },
      { step: "02", title: "Código de confirmação", lines: ["6 dígitos", "Reenviar em 00:45"], cta: "Confirmar" },
      { step: "03", title: "Para onde vai?", lines: ["Origem e destino", "Data e número de bilhetes"], cta: "Procurar" },
      { step: "04", title: "Rotas a partir daqui", lines: ["L3 — Combatentes – Matola", "06:30 · 14 lugares · 90,00 MZN"] },
      { step: "05", title: "Escolher lugar", lines: ["Planta 2+2", "Fila corrida no fundo"], cta: "Continuar" },
      { step: "06", title: "Como quer pagar?", lines: ["M-Pesa · e-Mola", "Carteira BusUp", "95,00 MZN"], cta: "Pagar" },
      { step: "07", title: "Bilhete emitido", lines: ["Referência e QR", "Descarregar PDF"] },
    ],
  },
  {
    key: "agente",
    name: "App do agente",
    audience: "Android · quem vende a bordo e no terreno",
    lead: "Turno aberto, venda, validação e caixa fechada no mesmo aparelho.",
    screens: [
      { step: "01", title: "Entrar no serviço", lines: ["Código do agente", "Terminal POS-004"], cta: "Entrar" },
      { step: "02", title: "Abrir turno", lines: ["Viatura e rota", "Fundo de maneio 6 480,00"], cta: "Abrir" },
      { step: "03", title: "Vender bilhete", lines: ["Origem – destino", "150,00 MZN"], cta: "Cobrar" },
      { step: "04", title: "Validar", lines: ["Encoste o cartão", "Ou leia o QR do bilhete"] },
      { step: "05", title: "Últimos movimentos", lines: ["Vendas e validações do turno", "Validações (38)"] },
      { step: "06", title: "Fechar caixa", lines: ["Apurado 6 980,00 MZN", "Diferença −80,00"], cta: "Fechar" },
    ],
  },
  {
    key: "motorista",
    name: "App do motorista",
    audience: "Android · quem conduz",
    lead: "As viagens do dia, as paragens e o manifesto, sem papel.",
    screens: [
      { step: "01", title: "Entrar no serviço", lines: ["Utilizador e senha", "Viatura atribuída"], cta: "Entrar" },
      { step: "02", title: "As suas viagens", lines: ["L1 — Baixa – Zimpeto", "06:00 · Embarque"] },
      { step: "03", title: "Paragens", lines: ["Sequência da rota", "Partir · Iniciar · Fechar"] },
    ],
  },
  {
    key: "pos",
    name: "POS de balcão",
    audience: "Terminal Urovo / Sunmi · balcão e terminal rodoviário",
    lead: "Venda rápida, recarga de cartão e sessão com fecho conferido.",
    screens: [
      { step: "01", title: "Abrir sessão", lines: ["Sessão #POS-0221", "Balcão Junta · POS-004"], cta: "Abrir" },
      { step: "02", title: "Venda rápida", lines: ["Percurso e passageiros", "225,00 MZN"], cta: "Cobrar" },
      { step: "03", title: "Receber 225,00 MZN", lines: ["Dinheiro · M-Pesa · e-Mola", "Troco 75,00"] },
      { step: "04", title: "Venda concluída", lines: ["Bilhete impresso", "Reimprimir"] },
      { step: "05", title: "Recarregar cartão", lines: ["Encoste o cartão", "250,00 MZN"], cta: "Recarregar" },
      { step: "06", title: "Saldo do cartão", lines: ["Saldo actualizado", "Último movimento"] },
    ],
  },
  {
    key: "validador",
    name: "Validador de bordo",
    audience: "Ecrã fixo, sem toque",
    lead: "Lê cartão por NFC e bilhete por QR, e mostra a decisão em segundos.",
    screens: [
      { step: "01", title: "Validação · L1", lines: ["Encoste o cartão", "Ou aproxime o QR"] },
      { step: "02", title: "Aprovada", lines: ["Débito de tarifa", "Saldo restante"] },
      { step: "03", title: "Negada", lines: ["Saldo insuficiente", "Cartão bloqueado"] },
    ],
  },
];

export default function AppsPage() {
  const { locale } = useUi();
  const lang = locale === "en" ? "en" : "pt";
  const site = useSite(lang);

  usePageMeta({
    title: "Apps BusUp — passageiro, agente, motorista, POS e validador",
    description: "Os cinco produtos do BusUp, com o vocabulário do Portal: fluxos completos das apps móveis e do POS.",
    path: "/apps",
    locale: lang,
  });

  return (
    <div className="bzs">
      <div className="bzs-topgrad">
        <SiteHeader site={site} />
        <div className="bzs-hero">
          <span className="bzs-badge">
            <i aria-hidden="true" />
            App mobile e POS · fluxos completos
          </span>
          <h1 className="bzs-h1">
            Os cinco produtos,
            <span>com o vocabulário do Portal.</span>
          </h1>
          <p className="bzs-lead">
            A app do passageiro, a do agente, a do motorista, o POS de balcão e o validador de bordo partilham tipos,
            paleta, pílulas de estado e traduções de enums com o portal de gestão.
          </p>
          <div className="bzs-ctas">
            <a className="bzs-cta bzs-cta-primary" href="/baixar">
              Descarregar apps
            </a>
            <a className="bzs-cta bzs-cta-ghost" href="/contactos">
              Falar com vendas
            </a>
          </div>
        </div>
      </div>

      {PRODUCTS.map((product) => (
        <section className="bzs-wrap bzs-section" id={product.key} key={product.key}>
          <header className="bzs-sectionhead">
            <span className="bzs-label">{product.audience}</span>
            <h2 className="bzs-h2" style={{ marginTop: 10 }}>
              {product.name}
            </h2>
            <p className="bzs-sublead">{product.lead}</p>
          </header>

          <div className="bza-rail">
            {product.screens.map((screen) => (
              <article className="bza-phone" key={screen.step}>
                <div className="bza-status">
                  <span>09:41</span>
                  <span className="bza-step">{screen.step}</span>
                </div>
                <div className="bza-screen">
                  <strong className="bza-title">{screen.title}</strong>
                  <ul className="bza-lines">
                    {screen.lines.map((line, i) => (
                      <li key={i}>{line}</li>
                    ))}
                  </ul>
                  {screen.cta ? <span className="bza-cta">{screen.cta}</span> : null}
                </div>
              </article>
            ))}
          </div>
        </section>
      ))}

      <section className="bzs-wrap bzs-section">
        <div className="bzs-ctaband">
          <h2>Leve o BusUp para a sua frota.</h2>
          <p>Mostramos a plataforma a operar com as suas rotas, os seus horários e os seus números.</p>
          <div className="bzs-ctas">
            <a className="bzs-cta bzs-cta-primary" href="/contactos">
              Falar com vendas
            </a>
            <a className="bzs-cta bzs-cta-ghost" href="/precos">
              Ver preços
            </a>
          </div>
        </div>
      </section>

      <SiteFooter site={site} />
    </div>
  );
}
