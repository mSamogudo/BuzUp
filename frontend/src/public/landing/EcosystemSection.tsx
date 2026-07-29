import { ArrowRight } from "lucide-react";
import Reveal from "./Reveal";
import type { Lang } from "./useLandingPrefs";

const SITE = "https://updigital.co.mz";

/** Família UpDigital — dados, logótipos e links do site institucional.
 *  `chipBg` reproduz a placa de fundo original de cada logótipo: as marcas
 *  nunca são recoloridas. */
interface Product {
  id: string; name: string; logo: string; shot: string; chipBg: string;
  accent: string; href: string; current?: boolean;
  cat: Record<Lang, string>; text: Record<Lang, string>;
}

const PRODUCTS: Product[] = [
  {
    id: "busup", name: "BusUp", logo: "/ecosystem/logos/busup.webp", shot: "/ecosystem/shots/px-4.webp",
    chipBg: "#000000", accent: "#0060F8", href: `${SITE}/solucoes/buzup`, current: true,
    cat: { pt: "Bilhética de Transportes", en: "Transport ticketing" },
    text: {
      pt: "Passagens digitais, check-in automático e gestão de frotas urbanas.",
      en: "Digital tickets, automatic check-in and urban fleet management.",
    },
  },
  {
    id: "payup", name: "PayUp", logo: "/ecosystem/logos/payup.webp", shot: "/ecosystem/shots/px-7.webp",
    chipBg: "transparent", accent: "#EF4444", href: `${SITE}/solucoes/payup`,
    cat: { pt: "Bilhética de Eventos", en: "Event ticketing" },
    text: {
      pt: "Venda de bilhetes, validação de entradas e pagamentos em tempo real para eventos.",
      en: "Ticket sales, entry validation and real-time payments for events.",
    },
  },
  {
    id: "cashup", name: "CashUp", logo: "/ecosystem/logos/cashup.webp", shot: "/ecosystem/shots/px-2.webp",
    chipBg: "#000000", accent: "#16A34A", href: `${SITE}/solucoes/cashup`,
    cat: { pt: "Pagamentos", en: "Payments" },
    text: {
      pt: "Pagamentos digitais, transações e controlo financeiro para empresas.",
      en: "Digital payments, transactions and financial control for businesses.",
    },
  },
  {
    id: "goup", name: "GoUp", logo: "/ecosystem/logos/goup.webp", shot: "/ecosystem/shots/px-5.webp",
    chipBg: "#000000", accent: "#0060F8", href: `${SITE}/solucoes/goup`,
    cat: { pt: "Gestão de Viagens", en: "Trip management" },
    text: {
      pt: "Reservas, rotas e gestão de passageiros num único painel para operadores.",
      en: "Bookings, routes and passenger management in a single operator dashboard.",
    },
  },
  {
    id: "vura", name: "VURA", logo: "/ecosystem/logos/vura.webp", shot: "/ecosystem/shots/px-6.webp",
    chipBg: "#F3F3F3", accent: "#2563EB", href: `${SITE}/solucoes/vura`,
    cat: { pt: "Gestão de Condomínios", en: "Condominium management" },
    text: {
      pt: "Controlo de acessos, convites de visitantes e portaria digital.",
      en: "Access control, visitor invitations and digital gatehouse.",
    },
  },
  {
    id: "gateup", name: "GateUp", logo: "/ecosystem/logos/gateup.webp", shot: "/ecosystem/shots/px-1.webp",
    chipBg: "transparent", accent: "#0060F8", href: `${SITE}/solucoes/gateup`,
    cat: { pt: "Controlo de Acessos", en: "Access control" },
    text: {
      pt: "Convites digitais, check-in e registo de visitas em tempo real.",
      en: "Digital invitations, check-in and real-time visit logs.",
    },
  },
  {
    id: "ossoma", name: "OSSOMA", logo: "/ecosystem/logos/ossoma.webp", shot: "/ecosystem/shots/px-3.webp",
    chipBg: "transparent", accent: "#1FA85C", href: `${SITE}/solucoes/ossoma`,
    cat: { pt: "Gestão Escolar", en: "School management" },
    text: {
      pt: "Matrículas, notas, presenças, propinas e comunicação escola-família.",
      en: "Enrolment, grades, attendance, fees and school-family communication.",
    },
  },
];

export default function EcosystemSection({ lang, kicker, h2, lead, visit }: {
  lang: Lang; kicker: string; h2: string; lead: string; visit: string;
}) {
  return (
    <section className="bzlp-sec alt" id="ecossistema">
      <div className="bzlp-wrap">
        <Reveal>
          <div className="bzlp-sechead">
            <div className="bzlp-kicker">{kicker}</div>
            <h2 className="bzlp-h2">{h2}</h2>
            <p className="bzlp-lead">{lead}</p>
          </div>
        </Reveal>

        <div className="bzlp-bento">
          {PRODUCTS.map((p, i) => (
            <Reveal key={p.id} delay={i * 45} className={i === 0 ? "bzlp-bento-feature" : ""}>
              <a
                className={`bzlp-tile${i === 0 ? " is-feature" : ""}${p.current ? " is-current" : ""}`}
                style={{ ["--pa" as string]: p.accent }}
                href={p.href} target="_blank" rel="noreferrer"
              >
                <div className="bzlp-tile-media">
                  <img src={p.shot} alt={`${p.name} — ${p.cat[lang]}`} loading="lazy" decoding="async"
                    width={1254} height={1254} />
                </div>
                <div className="bzlp-tile-body">
                  <span className="bzlp-plogo" style={{ background: p.chipBg === "transparent" ? undefined : p.chipBg }}>
                    <img src={p.logo} alt={p.name} height={i === 0 ? 34 : 24} loading="lazy" />
                  </span>
                  <span className="bzlp-tile-cat">{p.cat[lang]}</span>
                  <p>{p.text[lang]}</p>
                  <span className="bzlp-tile-cta">
                    {p.current ? (lang === "en" ? "You are here" : "Está aqui") : `${visit} ${p.name}`}
                    <ArrowRight size={15} aria-hidden />
                  </span>
                </div>
              </a>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
