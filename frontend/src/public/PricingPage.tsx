import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Check, Minus, ArrowRight, Menu, X } from "lucide-react";
import { useUi } from "../ui/UiPreferences";
import { useMkt } from "./site/mkt-i18n";
import { LangToggle } from "./site/LangToggle";
import { Seo } from "../ui/Seo";
import { PAGES, localizedPath, breadcrumbLd, faqLd, type Lang } from "../lib/seo";
import "./site/buzup-site.css";

type Bill = "monthly" | "annual";

const PRICING_FAQ = [
  { q: "Pagar com a BuzUp tem alguma taxa para o passageiro?", a: "Não. As recargas por M-Pesa, e-Mola, cartão ou nos pontos BuzUp não têm taxa de carregamento. Paga apenas o valor do bilhete ou da viagem avulsa." },
  { q: "Preciso de smartphone para usar a BuzUp?", a: "Não é obrigatório. Pode viajar apenas com o cartão BuzUp, recarregável em qualquer ponto ou agência. A app dá-lhe controlo extra do saldo, bilhetes e histórico." },
  { q: "Como funcionam as comissões para operadores?", a: "Aplicamos uma pequena percentagem sobre cada viagem paga através da plataforma. A taxa desce à medida que sobe de plano e pode ser negociada por volume no plano Frota+." },
  { q: "Posso mudar de plano mais tarde?", a: "Sim. Faça upgrade ou downgrade a qualquer momento — as alterações entram em vigor no ciclo de faturação seguinte, sem penalizações." },
  { q: "Quem fornece e instala os validadores?", a: "A BuzUp fornece os validadores a bordo e apoia a instalação e formação das equipas. Nos planos Operador e Frota+ o equipamento e o onboarding estão incluídos." },
];

export default function PricingPage({ lang = "pt" }: { lang?: Lang }) {
  const { toggleTheme } = useUi();
  const { locale, t } = useMkt(lang);
  const lp = (p: string) => localizedPath(p, lang);
  const [open, setOpen] = useState(false);
  const [bill, setBill] = useState<Bill>("monthly");
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting) {
            en.target.classList.add("in");
            io.unobserve(en.target);
          }
        });
      },
      { threshold: 0.14, rootMargin: "0px 0px -8% 0px" }
    );
    root.querySelectorAll(".reveal").forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  const close = () => setOpen(false);
  const opAmount = bill === "annual" ? "7.900" : "9.900";
  const cycle =
    locale === "en"
      ? bill === "annual" ? "/ mo, billed yearly" : "/ mo"
      : bill === "annual" ? "/ mês, faturado anual" : "/ mês";

  return (
    <div className="bz bz-pricing" ref={rootRef}>
      <Seo
        page={PAGES.pricing}
        lang={lang}
        jsonLd={[
          breadcrumbLd([{ name: "Início", path: "/" }, { name: t("Tarifas"), path: "/tarifas" }]),
          faqLd(PRICING_FAQ.map((f) => ({ q: t(f.q), a: t(f.a) }))),
        ]}
      />
      {/* NAV */}
      <nav className="nav scrolled">
        <div className="wrap nav-inner">
          <Link to={lp("/")} className="brand" aria-label="BuzUp">
            <svg className="nfc" width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M6 8.5a8 8 0 0 1 0 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <path d="M10 6.5a12 12 0 0 1 0 11" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <path d="M14 4.5a16 16 0 0 1 0 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <span><b>Buz</b><span className="up">Up</span></span>
          </Link>
          <div className="nav-links">
            <Link to={`${lp("/")}#funcionalidades`}>{t("Funcionalidades")}</Link>
            <Link to={`${lp("/")}#como-funciona`}>{t("Como funciona")}</Link>
            <Link to={`${lp("/")}#cartao`}>{t("Cartão")}</Link>
            <Link to={lp("/tarifas")} className="active">{t("Tarifas")}</Link>
            <Link to={lp("/contacto")}>{t("Contacto")}</Link>
          </div>
          <div className="nav-cta">
            <div className="nav-tools">
              <button className="ttbtn" onClick={toggleTheme} aria-label="Alternar tema claro/escuro" title="Tema">
                <svg className="ico-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></svg>
                <svg className="ico-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4.2" /><path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4" /></svg>
              </button>
              <LangToggle lang={lang} ptPath="/tarifas" enPath="/en/tarifas" />
            </div>
            <Link to={lp("/contacto")} className="btn btn-ghost btn-sm">{t("Falar com vendas")}</Link>
            <Link to={`${lp("/")}#download`} className="btn btn-primary btn-sm">{t("Baixar a app")}</Link>
            <button className="menu-btn" onClick={() => setOpen(true)} aria-label="Abrir menu"><Menu /></button>
          </div>
        </div>
      </nav>

      {/* mobile drawer */}
      <div className={`drawer${open ? " open" : ""}`} onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
        <div className="drawer-panel">
          <div className="row">
            <span className="brand"><b>Buz</b><span className="up">Up</span></span>
            <button className="close-btn" onClick={close} aria-label="Fechar menu"><X /></button>
          </div>
          <Link to={`${lp("/")}#funcionalidades`} onClick={close}>{t("Funcionalidades")}</Link>
          <Link to={`${lp("/")}#como-funciona`} onClick={close}>{t("Como funciona")}</Link>
          <Link to={`${lp("/")}#cartao`} onClick={close}>{t("Cartão")}</Link>
          <Link to={lp("/tarifas")} onClick={close}>{t("Tarifas")}</Link>
          <Link to={lp("/contacto")} onClick={close}>{t("Contacto")}</Link>
          <Link to={`${lp("/")}#download`} className="btn btn-primary" onClick={close}>{t("Baixar a app")}</Link>
        </div>
      </div>

      {/* PAGE HERO */}
      <header className="pagehero">
        <div className="wrap">
          <span className="eyebrow reveal">{t("Tarifas e planos")}</span>
          <h1 className="reveal d1">{t("Preços simples para")} <span className="accent">{t("passageiros e operadores.")}</span></h1>
          <p className="sub reveal d2">{t("Sem taxas escondidas, sem surpresas. Os passageiros pagam pela viagem; os operadores escalam quando precisam.")}</p>
        </div>
      </header>

      {/* PASSENGER TICKETS */}
      <section className="section--tight" style={{ paddingTop: "30px" }}>
        <div className="wrap">
          <div className="head center reveal">
            <span className="eyebrow" style={{ justifyContent: "center" }}>{t("Para passageiros")}</span>
            <h2>{t("Escolha o bilhete certo para si.")}</h2>
            <p>{t("Pague por viagem ou poupe com um passe. Tudo gerido na app BuzUp, do seu telemóvel.")}</p>
          </div>
          <div className="ticket-grid">
            <div className="ticket reveal">
              <div className="name">{t("Avulsa")}</div>
              <div className="price">20,00 <small>MZN</small></div>
              <div className="per">{t("por viagem")}</div>
              <p className="desc">{t("Pague só quando viaja, debitado do saldo a cada toque.")}</p>
              <div className="li"><Check /> {t("Sem compromisso")}</div>
              <div className="li"><Check /> {t("Debitado do saldo")}</div>
            </div>
            <div className="ticket reveal d1">
              <div className="name">{t("Diário")}</div>
              <div className="price">12,00 <small>MZN</small></div>
              <div className="per">{t("por dia")}</div>
              <p className="desc">{t("Viagens ilimitadas durante todo o dia, ideal para o dia a dia.")}</p>
              <div className="li"><Check /> {t("Válido 24 horas")}</div>
              <div className="li"><Check /> {t("Viagens ilimitadas")}</div>
            </div>
            <div className="ticket feat reveal d2">
              <div className="badge">{t("Mais popular")}</div>
              <div className="name">{t("Semanal")}</div>
              <div className="price">60,00 <small>MZN</small></div>
              <div className="per">{t("por semana")}</div>
              <p className="desc">{t("Sete dias de viagens sem preocupações e com poupança.")}</p>
              <div className="li"><Check /> {t("Válido 7 dias")}</div>
              <div className="li"><Check /> {t("Poupe face ao diário")}</div>
            </div>
            <div className="ticket reveal d3">
              <div className="name">{t("Mensal")}</div>
              <div className="price">180,00 <small>MZN</small></div>
              <div className="per">{t("por mês")}</div>
              <p className="desc">{t("Um mês inteiro de mobilidade livre, com o melhor valor por viagem.")}</p>
              <div className="li"><Check /> {t("Válido 30 dias")}</div>
              <div className="li"><Check /> {t("Melhor valor por viagem")}</div>
            </div>
          </div>
          <p className="muted reveal d1" style={{ textAlign: "center", marginTop: "26px", fontWeight: 500 }}>
            {t("Recargas por")} <b style={{ color: "var(--ink)" }}>M-Pesa</b>, <b style={{ color: "var(--ink)" }}>e-Mola</b>{t(", cartão bancário ou nos pontos BuzUp — sem qualquer taxa de carregamento.")}
          </p>
        </div>
      </section>

      {/* OPERATOR PLANS */}
      <section className="section" id="operadores" style={{ background: "var(--soft)" }}>
        <div className="wrap">
          <div className="head center reveal">
            <span className="eyebrow" style={{ justifyContent: "center" }}>{t("Para operadores e parceiros")}</span>
            <h2>{t("A plataforma que põe a sua frota a receber sem dinheiro físico.")}</h2>
            <p>{t("Validadores, gestão de receitas e relatórios em tempo real. Comece sem custos fixos e escale com a sua operação.")}</p>
          </div>

          <div className="billing reveal" role="group" aria-label="Ciclo de faturação">
            <button className={bill === "monthly" ? "active" : ""} onClick={() => setBill("monthly")}>{t("Mensal")}</button>
            <button className={bill === "annual" ? "active" : ""} onClick={() => setBill("annual")}>{t("Anual")}</button>
            <span className="save">{t("2 meses grátis")}</span>
          </div>

          <div className="plan-grid" style={{ marginTop: "36px" }}>
            <article className="plan reveal">
              <span className="tag">{t("Arranque")}</span>
              <p className="pfor">{t("Para operadores que estão a começar com uma ou duas viaturas.")}</p>
              <div className="price"><span className="cur">MZN</span><span className="amount">0</span></div>
              <span className="per">{t("grátis + 3% por viagem")}</span>
              <ul>
                <li><Check /> {t("Até 2 validadores")}</li>
                <li><Check /> {t("Recebimento sem contacto")}</li>
                <li><Check /> {t("App de bordo do motorista")}</li>
                <li><Check /> {t("Relatórios básicos de receita")}</li>
                <li className="off"><Minus /> {t("Gestão de frota")}</li>
                <li className="off"><Minus /> {t("Acesso à API")}</li>
              </ul>
              <Link to={lp("/contacto")} className="btn btn-ghost">{t("Começar grátis")}</Link>
            </article>

            <article className="plan feat reveal d1">
              <span className="badge">{t("Mais popular")}</span>
              <span className="tag">{t("Operador")}</span>
              <p className="pfor">{t("Para empresas com várias viaturas e equipas em rota.")}</p>
              <div className="price"><span className="cur">MZN</span><span className="amount">{opAmount}</span></div>
              <span className="per"><span className="cycle">{cycle}</span> {t("+ 1,5% por viagem")}</span>
              <ul>
                <li><Check /> {t("Validadores ilimitados")}</li>
                <li><Check /> {t("Gestão de frota e rotas")}</li>
                <li><Check /> {t("Relatórios em tempo real")}</li>
                <li><Check /> {t("Repasses diários automáticos")}</li>
                <li><Check /> {t("Vários operadores na conta")}</li>
                <li><Check /> {t("Suporte prioritário")}</li>
              </ul>
              <Link to={lp("/contacto")} className="btn btn-white">{t("Escolher Operador")}</Link>
            </article>

            <article className="plan reveal d2">
              <span className="tag">{t("Frota+")}</span>
              <p className="pfor">{t("Para redes, municípios e grandes operadores de transporte.")}</p>
              <div className="price"><span className="amount">{t("Personalizado")}</span></div>
              <span className="per">{t("à medida da sua operação")}</span>
              <ul>
                <li><Check /> {t("Tudo do plano Operador")}</li>
                <li><Check /> {t("Acesso à API e integrações")}</li>
                <li><Check /> {t("Marca própria (white-label)")}</li>
                <li><Check /> {t("SLA e gestor de conta")}</li>
                <li><Check /> {t("Comissão negociada por volume")}</li>
                <li><Check /> {t("Onboarding e formação")}</li>
              </ul>
              <Link to={lp("/contacto")} className="btn btn-ghost">{t("Pedir proposta")}</Link>
            </article>
          </div>
        </div>
      </section>

      {/* COMPARISON */}
      <section className="section compare">
        <div className="wrap">
          <div className="head center reveal">
            <span className="eyebrow" style={{ justifyContent: "center" }}>{t("Comparação")}</span>
            <h2>{t("Compare os planos de operador.")}</h2>
          </div>
          <div className="ctable reveal d1">
            <table>
              <thead>
                <tr><th>{t("Funcionalidade")}</th><th>{t("Arranque")}</th><th className="hot">{t("Operador")}</th><th>{t("Frota+")}</th></tr>
              </thead>
              <tbody>
                <tr><td>{t("Validadores")}</td><td>{t("Até 2")}</td><td className="hot">{t("Ilimitados")}</td><td>{t("Ilimitados")}</td></tr>
                <tr><td>{t("Comissão por viagem")}</td><td>3%</td><td className="hot">1,5%</td><td>{t("Negociada")}</td></tr>
                <tr><td>{t("Pagamento sem contacto")}</td><td className="y" /><td className="hot y" /><td className="y" /></tr>
                <tr><td>{t("Relatórios em tempo real")}</td><td className="n" /><td className="hot y" /><td className="y" /></tr>
                <tr><td>{t("Gestão de frota e rotas")}</td><td className="n" /><td className="hot y" /><td className="y" /></tr>
                <tr><td>{t("Repasses diários automáticos")}</td><td className="n" /><td className="hot y" /><td className="y" /></tr>
                <tr><td>{t("Acesso à API e integrações")}</td><td className="n" /><td className="hot n" /><td className="y" /></tr>
                <tr><td>{t("Marca própria (white-label)")}</td><td className="n" /><td className="hot n" /><td className="y" /></tr>
                <tr><td>{t("SLA e gestor de conta")}</td><td className="n" /><td className="hot n" /><td className="y" /></tr>
                <tr><td>{t("Suporte")}</td><td>{t("Email")}</td><td className="hot">{t("Prioritário")}</td><td>{t("Dedicado")}</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="section--tight">
        <div className="wrap">
          <div className="head center reveal">
            <span className="eyebrow" style={{ justifyContent: "center" }}>{t("Perguntas frequentes")}</span>
            <h2>{t("Ainda com dúvidas?")}</h2>
          </div>
          <div className="faq__list reveal d1">
            <details className="faq__item"><summary>{t("Pagar com a BuzUp tem alguma taxa para o passageiro?")}<i /></summary><p>{t("Não. As recargas por M-Pesa, e-Mola, cartão ou nos pontos BuzUp não têm taxa de carregamento. Paga apenas o valor do bilhete ou da viagem avulsa.")}</p></details>
            <details className="faq__item"><summary>{t("Preciso de smartphone para usar a BuzUp?")}<i /></summary><p>{t("Não é obrigatório. Pode viajar apenas com o cartão BuzUp, recarregável em qualquer ponto ou agência. A app dá-lhe controlo extra do saldo, bilhetes e histórico.")}</p></details>
            <details className="faq__item"><summary>{t("Como funcionam as comissões para operadores?")}<i /></summary><p>{t("Aplicamos uma pequena percentagem sobre cada viagem paga através da plataforma. A taxa desce à medida que sobe de plano e pode ser negociada por volume no plano Frota+.")}</p></details>
            <details className="faq__item"><summary>{t("Posso mudar de plano mais tarde?")}<i /></summary><p>{t("Sim. Faça upgrade ou downgrade a qualquer momento — as alterações entram em vigor no ciclo de faturação seguinte, sem penalizações.")}</p></details>
            <details className="faq__item"><summary>{t("Quem fornece e instala os validadores?")}<i /></summary><p>{t("A BuzUp fornece os validadores a bordo e apoia a instalação e formação das equipas. Nos planos Operador e Frota+ o equipamento e o onboarding estão incluídos.")}</p></details>
          </div>
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="cta">
        <div className="wrap">
          <div className="cta-card reveal">
            <div className="inner">
              <h2>{t("Vamos desenhar o plano certo para a sua operação.")}</h2>
              <p>{t("Fale com a equipa BuzUp e receba uma proposta à medida da sua frota. Respondemos em menos de 24 horas.")}</p>
              <Link to={lp("/contacto")} className="btn btn-white">{t("Agendar demonstração")} <ArrowRight /></Link>
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer>
        <div className="wrap">
          <div className="foot-top">
            <div className="foot-brand">
              <span className="brand">
                <svg className="nfc" width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M6 8.5a8 8 0 0 1 0 7M10 6.5a12 12 0 0 1 0 11M14 4.5a16 16 0 0 1 0 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                <span><b>Buz</b><span className="up">Up</span></span>
              </span>
              <p>{t("O transporte público de Moçambique, mais rápido, seguro e sem papel.")}</p>
            </div>
            <div className="foot-col">
              <h5>{t("Produto")}</h5>
              <Link to={`${lp("/")}#funcionalidades`}>{t("Funcionalidades")}</Link>
              <Link to={`${lp("/")}#como-funciona`}>{t("Como funciona")}</Link>
              <Link to={`${lp("/")}#cartao`}>{t("Cartão BuzUp")}</Link>
              <Link to={lp("/tarifas")}>{t("Tarifas")}</Link>
            </div>
            <div className="foot-col">
              <h5>{t("Empresa")}</h5>
              <a href="#">{t("Sobre a UpDigital")}</a>
              <a href="#operadores">{t("Operadores parceiros")}</a>
              <a href="#">{t("Carreiras")}</a>
              <a href="#">{t("Imprensa")}</a>
            </div>
            <div className="foot-col">
              <h5>{t("Suporte")}</h5>
              <Link to={lp("/contacto")}>{t("Central de ajuda")}</Link>
              <a href="mailto:sales@updigital.co.mz">sales@updigital.co.mz</a>
              <a href="https://www.updigital.co.mz" target="_blank" rel="noopener">www.updigital.co.mz</a>
              <a href="#">{t("Pontos de recarga")}</a>
            </div>
          </div>
          <div className="foot-bottom">
            <span>{t("© 2026 BuzUp · UpDigital. Todos os direitos reservados.")}</span>
            <a className="powered" href="#" aria-label="Powered by UpDigital">
              <span className="pb-label">Powered by</span>
              <img src="/assets/up-digital-logo/up_digital_light.png" alt="UpDigital" />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
