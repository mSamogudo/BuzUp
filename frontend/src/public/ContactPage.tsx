import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Mail, Phone, Globe, MapPin, Check, ArrowRight, Menu, X, Loader2 } from "lucide-react";
import { useUi } from "../ui/UiPreferences";
import { submitContactLead } from "../lib/api";
import { useMkt } from "./site/mkt-i18n";
import { LangToggle } from "./site/LangToggle";
import { BrandLogo } from "./site/BrandLogo";
import { Seo } from "../ui/Seo";
import { PAGES, localizedPath, breadcrumbLd, organizationLd, type Lang } from "../lib/seo";
import "./site/buzup-site.css";

export default function ContactPage({ lang = "pt" }: { lang?: Lang }) {
  const { toggleTheme } = useUi();
  const { t } = useMkt(lang);
  const lp = (p: string) => localizedPath(p, lang);
  const [open, setOpen] = useState(false);
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState("");
  const [errors, setErrors] = useState<{ name?: string; email?: string }>({});
  const rootRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

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

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = formRef.current;
    if (!form || submitting) return;
    setServerError("");

    const data = new FormData(form);
    const get = (k: string) => String(data.get(k) ?? "").trim();
    const name = get("name");
    const email = get("email");

    const nextErrors: { name?: string; email?: string } = {};
    if (!name) nextErrors.name = t("Indique o seu nome.");
    if (!email) nextErrors.email = t("Indique o seu email.");
    else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email))
      nextErrors.email = t("Email inválido. Verifique o endereço.");

    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      form.querySelector<HTMLElement>(`[name="${Object.keys(nextErrors)[0]}"]`)?.focus();
      return;
    }
    setErrors({});

    setSubmitting(true);
    try {
      await submitContactLead({
        source: "contact",
        name,
        email,
        organization: get("org"),
        phone: get("phone"),
        profile: get("profile"),
        message: get("message"),
        locale: lang,
        website: get("website"), // honeypot
      });
      setSent(true);
    } catch (err) {
      setServerError(
        err instanceof Error && err.message
          ? err.message
          : t("Não foi possível enviar. Tente novamente ou escreva para sales@updigital.co.mz.")
      );
    } finally {
      setSubmitting(false);
    }
  };

  const clearErr = (field: "name" | "email") =>
    setErrors((prev) => (prev[field] ? { ...prev, [field]: undefined } : prev));

  return (
    <div className="bz bz-contact" ref={rootRef}>
      <Seo
        page={PAGES.contact}
        lang={lang}
        jsonLd={[
          breadcrumbLd([{ name: "Início", path: "/" }, { name: t("Contacto"), path: "/contacto" }]),
          organizationLd(),
        ]}
      />
      <a className="skip-link" href="#main">{t("Saltar para o conteúdo")}</a>
      {/* NAV */}
      <nav className="nav scrolled">
        <div className="wrap nav-inner">
          <Link to={lp("/")} className="brand" aria-label="BuzUp">
            <BrandLogo />
          </Link>
          <div className="nav-links">
            <Link to={`${lp("/")}#funcionalidades`}>{t("Funcionalidades")}</Link>
            <Link to={`${lp("/")}#como-funciona`}>{t("Como funciona")}</Link>
            <Link to={`${lp("/")}#cartao`}>{t("Cartão")}</Link>
            <Link to={lp("/tarifas")}>{t("Tarifas")}</Link>
            <Link to={lp("/contacto")} className="active">{t("Contacto")}</Link>
          </div>
          <div className="nav-cta">
            <div className="nav-tools">
              <button className="ttbtn" onClick={toggleTheme} aria-label="Alternar tema claro/escuro" title="Tema">
                <svg className="ico-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></svg>
                <svg className="ico-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4.2" /><path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4" /></svg>
              </button>
              <LangToggle lang={lang} ptPath="/contacto" enPath="/en/contacto" />
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
            <span className="brand"><BrandLogo /></span>
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

      {/* CONTACT */}
      <main className="ct" id="main" tabIndex={-1}>
        <div className="wrap ct-grid">
          {/* left */}
          <div className="ct-aside reveal">
            <span className="eyebrow">{t("Contacto")}</span>
            <h1>{t("Vamos pôr a sua cidade a viajar com um toque.")}</h1>
            <p className="lead">{t("Conte-nos sobre a sua operação ou tire as suas dúvidas. A equipa BuzUp responde em menos de 24 horas.")}</p>

            <ul className="methods">
              <li>
                <span className="ic"><Mail /></span>
                <div><small>{t("Email")}</small><b>sales@updigital.co.mz</b></div>
              </li>
              <li>
                <span className="ic"><Phone /></span>
                <div><small>{t("Telefone")}</small><b>+258 86 693 0017<br />+258 85 300 4449</b></div>
              </li>
              <li>
                <span className="ic"><Globe /></span>
                <div><small>{t("Website")}</small><b>www.updigital.co.mz</b></div>
              </li>
              <li>
                <span className="ic"><MapPin /></span>
                <div><small>{t("Escritório")}</small><b>{t("Av. Alberto Massavanhane, nº 1265 R/c, Matola")}</b></div>
              </li>
            </ul>

            <div className="assure">
              <span className="chip"><span className="dot" /> {t("Resposta < 24h")}</span>
              <span className="chip"><span className="dot" /> {t("Demo sem compromisso")}</span>
            </div>
          </div>

          {/* right: form */}
          <div className="ct-form-wrap reveal d1">
            <div className={`ct-success${sent ? " show" : ""}`}>
              <div className="ico"><Check /></div>
              <h3>{t("Mensagem enviada!")}</h3>
              <p>{t("A equipa BuzUp responde em menos de 24 horas, normalmente no mesmo dia útil.")}</p>
            </div>

            {!sent && (
              <form className="ct-form" ref={formRef} onSubmit={onSubmit} noValidate>
                {/* Honeypot — hidden from users + assistive tech; bots fill it. */}
                <div className="hp-field" aria-hidden="true">
                  <label htmlFor="website">Website</label>
                  <input type="text" id="website" name="website" tabIndex={-1} autoComplete="off" />
                </div>

                <div className="fields">
                  <div className={`field${errors.name ? " err" : ""}`}>
                    <label htmlFor="name">{t("Nome")}</label>
                    <input
                      type="text" id="name" name="name" placeholder={t("O seu nome")} required
                      aria-invalid={errors.name ? true : undefined}
                      aria-describedby={errors.name ? "err-name" : undefined}
                      onInput={() => clearErr("name")}
                    />
                    {errors.name && <span className="err-msg" id="err-name" role="alert">{errors.name}</span>}
                  </div>
                  <div className="field">
                    <label htmlFor="org">{t("Empresa / Organização")}</label>
                    <input type="text" id="org" name="org" placeholder={t("Nome da organização")} />
                  </div>
                  <div className={`field${errors.email ? " err" : ""}`}>
                    <label htmlFor="email">{t("Email")}</label>
                    <input
                      type="email" id="email" name="email" placeholder={t("email@empresa.com")} required
                      inputMode="email" autoComplete="email"
                      aria-invalid={errors.email ? true : undefined}
                      aria-describedby={errors.email ? "err-email" : undefined}
                      onInput={() => clearErr("email")}
                    />
                    {errors.email && <span className="err-msg" id="err-email" role="alert">{errors.email}</span>}
                  </div>
                  <div className="field">
                    <label htmlFor="phone">{t("Telefone")}</label>
                    <input type="tel" id="phone" name="phone" placeholder="+258 ..." autoComplete="tel" />
                  </div>
                  <div className="field full">
                    <label htmlFor="profile">{t("Eu sou…")}</label>
                    <select id="profile" name="profile" defaultValue="">
                      <option value="">{t("Selecione…")}</option>
                      <option value="passageiro">{t("Passageiro")}</option>
                      <option value="operador">{t("Operador de transporte")}</option>
                      <option value="municipio">{t("Município / Entidade pública")}</option>
                      <option value="parceiro">{t("Parceiro / Ponto de recarga")}</option>
                      <option value="imprensa">{t("Imprensa")}</option>
                      <option value="outro">{t("Outro")}</option>
                    </select>
                  </div>
                  <div className="field full">
                    <label htmlFor="message">{t("Mensagem")}</label>
                    <textarea id="message" name="message" placeholder={t("Conte-nos como podemos ajudar…")} />
                  </div>
                </div>

                {serverError && <p className="form-error" role="alert">{serverError}</p>}

                <button type="submit" className="btn btn-primary btn-lg submit" disabled={submitting}>
                  {submitting
                    ? <>{t("A enviar…")} <Loader2 className="spin" /></>
                    : <>{t("Enviar mensagem")} <ArrowRight /></>}
                </button>
                <p className="fine">
                  {t("Ao enviar, concorda com a nossa")}{" "}
                  <a href="https://www.updigital.co.mz" target="_blank" rel="noopener">{t("Política de Privacidade")}</a>.
                </p>
              </form>
            )}
          </div>
        </div>
      </main>

      {/* FOOTER */}
      <footer>
        <div className="wrap">
          <div className="foot-top">
            <div className="foot-brand">
              <span className="brand">
                <BrandLogo tone="onDark" />
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
              <a href="https://www.updigital.co.mz" target="_blank" rel="noopener">{t("Sobre a UpDigital")}</a>
              <Link to={`${lp("/tarifas")}#operadores`}>{t("Operadores parceiros")}</Link>
              <a href="https://www.updigital.co.mz" target="_blank" rel="noopener">{t("Carreiras")}</a>
              <a href="mailto:sales@updigital.co.mz?subject=Imprensa%20BuzUp">{t("Imprensa")}</a>
            </div>
            <div className="foot-col">
              <h5>{t("Suporte")}</h5>
              <Link to={lp("/contacto")}>{t("Central de ajuda")}</Link>
              <a href="mailto:sales@updigital.co.mz">sales@updigital.co.mz</a>
              <a href="tel:+258866930017">+258 86 693 0017</a>
              <a href="https://www.updigital.co.mz" target="_blank" rel="noopener">www.updigital.co.mz</a>
              <Link to={lp("/contacto")}>{t("Pontos de recarga")}</Link>
            </div>
          </div>
          <div className="foot-bottom">
            <span>{t("© 2026 BuzUp · UpDigital. Todos os direitos reservados.")}</span>
            <a className="powered" href="https://www.updigital.co.mz" target="_blank" rel="noopener" aria-label="Powered by UpDigital">
              <span className="pb-label">Powered by</span>
              <img src="/assets/up-digital-logo/up_digital_light.png" alt="UpDigital" />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
