import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Mail, Phone, MapPin, Check, ArrowRight, Menu, X } from "lucide-react";
import { useUi } from "../ui/UiPreferences";
import { useMkt } from "./site/mkt-i18n";
import { LangToggle } from "./site/LangToggle";
import { Seo } from "../ui/Seo";
import { PAGES, localizedPath, breadcrumbLd, organizationLd, type Lang } from "../lib/seo";
import "./site/buzup-site.css";

export default function ContactPage({ lang = "pt" }: { lang?: Lang }) {
  const { toggleTheme } = useUi();
  const { t } = useMkt(lang);
  const lp = (p: string) => localizedPath(p, lang);
  const [open, setOpen] = useState(false);
  const [sent, setSent] = useState(false);
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

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = formRef.current;
    if (!form) return;
    let ok = true;
    form.querySelectorAll<HTMLInputElement>("input[required]").forEach((inp) => {
      const bad =
        !inp.value.trim() ||
        (inp.type === "email" && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(inp.value));
      inp.closest(".field")?.classList.toggle("err", bad);
      if (bad) ok = false;
    });
    if (!ok) return;
    setSent(true);
  };

  const clearErr = (e: React.FormEvent<HTMLInputElement>) =>
    e.currentTarget.closest(".field")?.classList.remove("err");

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

      {/* CONTACT */}
      <main className="ct">
        <div className="wrap ct-grid">
          {/* left */}
          <div className="ct-aside reveal">
            <span className="eyebrow">{t("Contacto")}</span>
            <h1>{t("Vamos pôr a sua cidade a viajar com um toque.")}</h1>
            <p className="lead">{t("Conte-nos sobre a sua operação ou tire as suas dúvidas. A equipa BuzUp responde em menos de 24 horas.")}</p>

            <ul className="methods">
              <li>
                <span className="ic"><Mail /></span>
                <div><small>{t("Email")}</small><b>ola@buzup.co.mz</b></div>
              </li>
              <li>
                <span className="ic"><Phone /></span>
                <div><small>{t("Telefone")}</small><b>+258 84 000 0000</b></div>
              </li>
              <li>
                <span className="ic"><MapPin /></span>
                <div><small>{t("Escritório")}</small><b>{t("Maputo, Moçambique")}</b></div>
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
              <p>{t("Obrigado. A equipa BuzUp entrará em contacto em breve.")}</p>
            </div>

            {!sent && (
              <form className="ct-form" ref={formRef} onSubmit={onSubmit} noValidate>
                <div className="fields">
                  <div className="field">
                    <label htmlFor="name">{t("Nome")}</label>
                    <input type="text" id="name" name="name" placeholder={t("O seu nome")} required onInput={clearErr} />
                  </div>
                  <div className="field">
                    <label htmlFor="org">{t("Empresa / Organização")}</label>
                    <input type="text" id="org" name="org" placeholder={t("Nome da organização")} onInput={clearErr} />
                  </div>
                  <div className="field">
                    <label htmlFor="email">{t("Email")}</label>
                    <input type="email" id="email" name="email" placeholder={t("email@empresa.com")} required onInput={clearErr} />
                  </div>
                  <div className="field">
                    <label htmlFor="phone">{t("Telefone")}</label>
                    <input type="tel" id="phone" name="phone" placeholder="+258 ..." onInput={clearErr} />
                  </div>
                  <div className="field full">
                    <label htmlFor="profile">{t("Eu sou…")}</label>
                    <select id="profile" name="profile">
                      <option value="">{t("Selecione…")}</option>
                      <option>{t("Passageiro")}</option>
                      <option>{t("Operador de transporte")}</option>
                      <option>{t("Município / Entidade pública")}</option>
                      <option>{t("Parceiro / Ponto de recarga")}</option>
                      <option>{t("Imprensa")}</option>
                      <option>{t("Outro")}</option>
                    </select>
                  </div>
                  <div className="field full">
                    <label htmlFor="message">{t("Mensagem")}</label>
                    <textarea id="message" name="message" placeholder={t("Conte-nos como podemos ajudar…")} />
                  </div>
                </div>

                <button type="submit" className="btn btn-primary btn-lg submit">
                  {t("Enviar mensagem")} <ArrowRight />
                </button>
                <p className="fine">{t("Ao enviar, concorda com a nossa")} <a href="#">{t("Política de Privacidade")}</a>.</p>
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
              <Link to={`${lp("/tarifas")}#operadores`}>{t("Operadores parceiros")}</Link>
              <a href="#">{t("Carreiras")}</a>
              <a href="#">{t("Imprensa")}</a>
            </div>
            <div className="foot-col">
              <h5>{t("Suporte")}</h5>
              <Link to={lp("/contacto")}>{t("Central de ajuda")}</Link>
              <a href="mailto:ola@buzup.co.mz">ola@buzup.co.mz</a>
              <a href="tel:+258840000000">+258 84 000 0000</a>
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
