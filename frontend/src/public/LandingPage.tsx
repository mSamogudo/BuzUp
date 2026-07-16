import { useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Wallet, ScanLine, CreditCard, BarChart3, ShieldCheck, Users,
  Smartphone, Store, LayoutDashboard, Bus, Download, ArrowRight,
  CheckCircle2, TrendingUp, Route as RouteIcon, RefreshCw, Banknote,
} from "lucide-react";
import { useBranding, pickLogo } from "../lib/branding";

function Wordmark({ url, alt, height = 30 }: { url: string; alt: string; height?: number }) {
  if (url) return <img src={url} alt={alt} style={{ height, display: "block" }} />;
  return (
    <span style={{ fontWeight: 800, fontSize: height * 0.8, letterSpacing: "-0.02em" }}>
      Bus<span style={{ color: "#2D8CF0" }}>Up</span>
    </span>
  );
}

const BENEFITS = [
  { icon: Banknote, title: "Fim do dinheiro na mão", text: "Sem troco nem notas a circular. Menos furtos, menos erros e mais higiene a bordo." },
  { icon: TrendingUp, title: "Receita 100% rastreável", text: "Cada bilhete fica registado. Combate direto à evasão de receita e ao desvio de fundos." },
  { icon: BarChart3, title: "Dados para decidir", text: "Fluxo de passageiros por rota, horário e veículo — informação real para planear o transporte." },
  { icon: Users, title: "Inclusão de todos", text: "Quem não tem smartphone usa um cartão recarregável. Ninguém fica de fora do sistema." },
];

const STEPS = [
  { icon: Wallet, title: "1. Carrega saldo", text: "O passageiro carrega a carteira por M-Pesa ou e-Mola — no telemóvel ou num agente." },
  { icon: ScanLine, title: "2. Embarca", text: "Mostra o QR Code ou aproxima o cartão NFC. O agente valida num segundo." },
  { icon: CheckCircle2, title: "3. Viaja", text: "O bilhete é debitado na hora e a viagem fica registada no sistema." },
];

const TOOLS = [
  {
    icon: Smartphone, name: "App Passageiro", tag: "Android · telemóvel",
    items: ["Carteira digital em Meticais", "Recarga M-Pesa e e-Mola", "Bilhete por QR Code", "Histórico de viagens e rotas"],
  },
  {
    icon: Store, name: "App POS", tag: "Agente / Motorista",
    items: ["Venda e validação de bilhetes", "Leitura QR + cartão NFC", "Terminais SUNMI / Urovo", "Atualização automática (OTA)"],
  },
  {
    icon: LayoutDashboard, name: "Portal de Gestão", tag: "Município / Operador",
    items: ["Rotas, viagens e frota", "Motoristas e passageiros", "Relatórios PDF de receita", "Auditoria e segurança"],
  },
];

const CITY = [
  "Transparência total — receita do transporte auditável ao cêntimo.",
  "Combate à corrupção — o dinheiro deixa de passar de mão em mão.",
  "Imagem inovadora — a cidade referência em transporte digital.",
  "Relatórios oficiais — mapas de receita e uso prontos a exportar.",
  "Rápido de implementar — funciona nos autocarros atuais, sem obra.",
  "Feito em Moçambique — suporte local e pagamentos nacionais.",
];

const FEATURES = [
  { icon: Banknote, label: "Pagamento cashless" },
  { icon: ScanLine, label: "Bilhete por QR Code" },
  { icon: CreditCard, label: "Cartão NFC recarregável" },
  { icon: Wallet, label: "Recarga M-Pesa / e-Mola" },
  { icon: BarChart3, label: "Relatórios em tempo real" },
  { icon: ShieldCheck, label: "Auditoria e segurança" },
  { icon: RouteIcon, label: "Gestão de rotas e viagens" },
  { icon: Bus, label: "Frota e livrete de veículos" },
  { icon: RefreshCw, label: "Atualização remota das apps" },
];

export default function LandingPage() {
  const { branding } = useBranding();
  const darkLogo = pickLogo(branding.sidebar_logo_url, branding.primary_logo_url);

  useEffect(() => {
    document.title = "BusUp · Transporte público cashless";
  }, []);

  return (
    <div className="bzlp">
      <style>{CSS}</style>

      {/* HEADER */}
      <header className="bzlp-nav">
        <div className="bzlp-nav-in">
          <Link to="/" className="bzlp-logo"><Wordmark url={darkLogo} alt="BusUp" height={28} /></Link>
          <nav className="bzlp-links">
            <a href="#funcionalidades">Funcionalidades</a>
            <a href="#apps">Aplicações</a>
            <a href="#municipios">Municípios</a>
          </nav>
          <div className="bzlp-nav-cta">
            <Link to="/login" className="bzlp-ghost">Entrar</Link>
            <Link to="/baixar" className="bzlp-btn sm"><Download size={16} /> Baixar app</Link>
          </div>
        </div>
      </header>

      {/* HERO */}
      <section className="bzlp-hero">
        <div className="bzlp-hero-in">
          <div className="bzlp-hero-txt">
            <span className="bzlp-badge">Transporte público · Cashless</span>
            <h1>O transporte da sua cidade,<br /><span>agora sem dinheiro físico.</span></h1>
            <p>O <b>BusUp</b> digitaliza o pagamento nos autocarros e chapas. O passageiro paga com o
              telemóvel ou cartão — <b>sem troco, sem filas, sem perdas</b> — e o município passa a ver,
              em tempo real, cada viagem e cada metical.</p>
            <div className="bzlp-hero-cta">
              <Link to="/baixar" className="bzlp-btn"><Download size={18} /> Baixar aplicação</Link>
              <a href="#funcionalidades" className="bzlp-btn outline">Ver funcionalidades <ArrowRight size={16} /></a>
            </div>
            <div className="bzlp-chips">
              <span><b>QR</b> no telemóvel</span>
              <span><b>Cartão NFC</b></span>
              <span><b>M-Pesa</b></span>
              <span><b>e-Mola</b></span>
            </div>
          </div>
          <div className="bzlp-hero-art" aria-hidden>
            <div className="bzlp-phone">
              <div className="bzlp-phone-top" />
              <div className="bzlp-wallet">
                <span className="bzlp-wallet-l">Saldo BusUp</span>
                <span className="bzlp-wallet-v">250,00 MT</span>
              </div>
              <div className="bzlp-qr"><ScanLine size={64} strokeWidth={1.4} /></div>
              <div className="bzlp-phone-btn"><Bus size={16} /> Embarcar</div>
            </div>
            <div className="bzlp-pos">
              <span>POS</span>
              <CheckCircle2 size={30} />
              <small>Bilhete válido</small>
            </div>
          </div>
        </div>
      </section>

      {/* BENEFITS */}
      <section className="bzlp-sec" id="funcionalidades">
        <div className="bzlp-wrap">
          <div className="bzlp-kicker">O QUE O BUSUP RESOLVE</div>
          <h2 className="bzlp-h2">Menos dinheiro na mão. Mais controlo na cidade.</h2>
          <div className="bzlp-benefits">
            {BENEFITS.map((b) => (
              <div className="bzlp-benefit" key={b.title}>
                <div className="bzlp-bi"><b.icon size={22} /></div>
                <h3>{b.title}</h3>
                <p>{b.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW */}
      <section className="bzlp-sec alt">
        <div className="bzlp-wrap">
          <div className="bzlp-kicker">COMO FUNCIONA</div>
          <h2 className="bzlp-h2">Três passos. Uma viagem sem atrito.</h2>
          <div className="bzlp-steps">
            {STEPS.map((s) => (
              <div className="bzlp-step" key={s.title}>
                <div className="bzlp-si"><s.icon size={26} /></div>
                <h3>{s.title}</h3>
                <p>{s.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* APPS */}
      <section className="bzlp-sec" id="apps">
        <div className="bzlp-wrap">
          <div className="bzlp-kicker">UMA PLATAFORMA, TRÊS FERRAMENTAS</div>
          <h2 className="bzlp-h2">Do passageiro ao gestor — tudo ligado.</h2>
          <div className="bzlp-tools">
            {TOOLS.map((t) => (
              <div className="bzlp-tool" key={t.name}>
                <div className="bzlp-tool-head">
                  <div className="bzlp-ti"><t.icon size={26} /></div>
                  <div>
                    <h3>{t.name}</h3>
                    <span>{t.tag}</span>
                  </div>
                </div>
                <ul>
                  {t.items.map((i) => <li key={i}>{i}</li>)}
                </ul>
              </div>
            ))}
          </div>
          <div className="bzlp-tools-cta">
            <Link to="/baixar" className="bzlp-btn"><Download size={18} /> Descarregar as aplicações</Link>
          </div>
        </div>
      </section>

      {/* MUNICIPIOS */}
      <section className="bzlp-city" id="municipios">
        <div className="bzlp-wrap">
          <div className="bzlp-city-in">
            <div className="bzlp-city-txt">
              <div className="bzlp-kicker light">PARA O SEU MUNICÍPIO</div>
              <h2>Uma cidade mais moderna, transparente e eficiente.</h2>
              <p>Modernize o transporte urbano, aumente a receita e ofereça aos cidadãos uma viagem mais
                simples e digna — com controlo total nas suas mãos.</p>
            </div>
            <div className="bzlp-city-list">
              {CITY.map((c) => {
                const [b, ...rest] = c.split(" — ");
                return (
                  <div className="bzlp-city-item" key={c}>
                    <span className="bzlp-tick"><CheckCircle2 size={18} /></span>
                    <span><b>{b}</b>{rest.length ? ` — ${rest.join(" — ")}` : ""}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* FEATURES GRID */}
      <section className="bzlp-sec alt">
        <div className="bzlp-wrap">
          <div className="bzlp-kicker">TUDO O QUE O BUSUP FAZ</div>
          <h2 className="bzlp-h2">Funcionalidades numa só plataforma.</h2>
          <div className="bzlp-feats">
            {FEATURES.map((f) => (
              <div className="bzlp-feat" key={f.label}>
                <div className="bzlp-fi"><f.icon size={20} /></div>
                <span>{f.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bzlp-cta">
        <div className="bzlp-wrap bzlp-cta-in">
          <div>
            <h2>Traga o BusUp para o seu município.</h2>
            <p>Comece hoje: descarregue as aplicações ou fale connosco para uma demonstração.</p>
          </div>
          <div className="bzlp-cta-btns">
            <Link to="/baixar" className="bzlp-btn white"><Download size={18} /> Baixar app</Link>
            <a href="https://updigital.co.mz" target="_blank" rel="noreferrer" className="bzlp-btn outline light">
              Falar connosco <ArrowRight size={16} />
            </a>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bzlp-foot">
        <div className="bzlp-wrap bzlp-foot-in">
          <div className="bzlp-foot-brand">
            <Wordmark url={darkLogo} alt="BusUp" height={26} />
            <p>Plataforma de bilhética cashless para transporte público. Desenvolvido em Moçambique.</p>
          </div>
          <div className="bzlp-foot-cols">
            <div>
              <h4>Produto</h4>
              <a href="#funcionalidades">Funcionalidades</a>
              <a href="#apps">Aplicações</a>
              <Link to="/baixar">Descarregar</Link>
            </div>
            <div>
              <h4>Acesso</h4>
              <Link to="/login">Portal de gestão</Link>
              <Link to="/baixar">App Passageiro</Link>
              <Link to="/baixar">App POS</Link>
            </div>
            <div>
              <h4>Contacto</h4>
              <a href="https://updigital.co.mz" target="_blank" rel="noreferrer">updigital.co.mz</a>
              <a href="mailto:comercial@updigital.co.mz">comercial@updigital.co.mz</a>
            </div>
          </div>
        </div>
        <div className="bzlp-foot-bar">© {new Date().getFullYear()} BusUp · UP Digital. Todos os direitos reservados.</div>
      </footer>
    </div>
  );
}

const CSS = `
.bzlp{--navy:#0D3B66;--navy2:#0A2E50;--blue:#2D8CF0;--blue2:#1D5FA7;--ink:#0F1B2D;--muted:#5B6B7F;--line:#E4EBF3;--bg:#F6F9FD;
  color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:#fff;}
.bzlp a{text-decoration:none;color:inherit;}
.bzlp-wrap{width:100%;max-width:1080px;margin:0 auto;padding:0 22px;}
.bzlp-btn{display:inline-flex;align-items:center;gap:9px;background:var(--blue);color:#fff;font-weight:700;font-size:15px;
  padding:13px 22px;border-radius:12px;transition:.15s;border:none;cursor:pointer;}
.bzlp-btn:hover{background:var(--blue2);}
.bzlp-btn.sm{padding:9px 16px;font-size:14px;}
.bzlp-btn.outline{background:transparent;color:var(--blue2);border:1.5px solid var(--blue);}
.bzlp-btn.outline:hover{background:#EAF3FF;}
.bzlp-btn.white{background:#fff;color:var(--navy);}
.bzlp-btn.white:hover{background:#eaf3ff;}
.bzlp-btn.outline.light{background:transparent;color:#fff;border-color:rgba(255,255,255,.55);}
.bzlp-btn.outline.light:hover{background:rgba(255,255,255,.12);}

/* NAV */
.bzlp-nav{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.92);backdrop-filter:blur(10px);border-bottom:1px solid var(--line);}
.bzlp-nav-in{max-width:1080px;margin:0 auto;padding:12px 22px;display:flex;align-items:center;justify-content:space-between;gap:16px;}
.bzlp-links{display:flex;gap:24px;font-size:14.5px;font-weight:600;color:var(--muted);}
.bzlp-links a:hover{color:var(--ink);}
.bzlp-nav-cta{display:flex;align-items:center;gap:12px;}
.bzlp-ghost{font-weight:700;font-size:14px;color:var(--navy);}
.bzlp-ghost:hover{color:var(--blue);}
@media(max-width:760px){.bzlp-links{display:none;}}

/* HERO */
.bzlp-hero{background:linear-gradient(155deg,var(--navy) 0%,var(--navy2) 60%,#08243f 100%);color:#fff;overflow:hidden;position:relative;}
.bzlp-hero::after{content:"";position:absolute;right:-12%;top:-30%;width:520px;height:520px;
  background:radial-gradient(circle,rgba(45,140,240,.4),transparent 62%);}
.bzlp-hero-in{max-width:1080px;margin:0 auto;padding:64px 22px 72px;display:grid;grid-template-columns:1.1fr .9fr;gap:40px;align-items:center;position:relative;z-index:2;}
.bzlp-badge{display:inline-block;font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#bfd8f5;
  border:1px solid rgba(191,216,245,.4);border-radius:30px;padding:6px 14px;}
.bzlp-hero h1{font-size:40px;line-height:1.08;font-weight:800;margin:20px 0 16px;}
.bzlp-hero h1 span{color:var(--blue);}
.bzlp-hero-txt p{font-size:16px;line-height:1.55;color:#d6e4f5;max-width:520px;}
.bzlp-hero-cta{display:flex;gap:12px;margin-top:26px;flex-wrap:wrap;}
.bzlp-chips{display:flex;gap:9px;margin-top:26px;flex-wrap:wrap;}
.bzlp-chips span{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);border-radius:30px;
  padding:7px 14px;font-size:13px;color:#eaf3ff;}
.bzlp-chips b{color:var(--blue);}
@media(max-width:860px){.bzlp-hero-in{grid-template-columns:1fr;}.bzlp-hero h1{font-size:30px;}.bzlp-hero-art{display:none;}}

/* HERO ART */
.bzlp-hero-art{position:relative;height:360px;}
.bzlp-phone{position:absolute;left:50%;top:0;transform:translateX(-58%);width:196px;height:360px;border-radius:30px;
  background:linear-gradient(160deg,#123a63,#0b2743);border:2px solid rgba(255,255,255,.14);
  box-shadow:0 30px 60px rgba(0,0,0,.35);padding:18px 16px;display:flex;flex-direction:column;}
.bzlp-phone-top{width:60px;height:6px;border-radius:6px;background:rgba(255,255,255,.25);margin:2px auto 18px;}
.bzlp-wallet{background:linear-gradient(135deg,var(--blue),var(--blue2));border-radius:14px;padding:14px;color:#fff;display:flex;flex-direction:column;gap:4px;}
.bzlp-wallet-l{font-size:11px;opacity:.85;}
.bzlp-wallet-v{font-size:22px;font-weight:800;}
.bzlp-qr{flex:1;display:flex;align-items:center;justify-content:center;margin:14px 0;background:rgba(255,255,255,.06);border-radius:14px;color:#eaf3ff;}
.bzlp-phone-btn{background:#fff;color:var(--navy);border-radius:10px;padding:11px;text-align:center;font-weight:700;font-size:13px;
  display:flex;align-items:center;justify-content:center;gap:6px;}
.bzlp-pos{position:absolute;right:2px;bottom:8px;width:132px;background:#fff;color:var(--navy);border-radius:16px;
  padding:16px;box-shadow:0 20px 40px rgba(0,0,0,.3);display:flex;flex-direction:column;align-items:center;gap:4px;}
.bzlp-pos span{font-size:11px;font-weight:800;letter-spacing:.1em;color:var(--muted);}
.bzlp-pos svg{color:#2E9E56;}
.bzlp-pos small{font-size:12px;font-weight:600;color:#2E9E56;}

/* SECTIONS */
.bzlp-sec{padding:60px 0;}
.bzlp-sec.alt{background:var(--bg);}
.bzlp-kicker{font-size:12px;font-weight:800;letter-spacing:.14em;color:var(--blue2);text-align:center;}
.bzlp-kicker.light{color:var(--blue);text-align:left;}
.bzlp-h2{font-size:27px;font-weight:800;text-align:center;margin:10px 0 40px;color:var(--navy);}
@media(max-width:640px){.bzlp-h2{font-size:22px;}}

.bzlp-benefits{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;}
@media(max-width:900px){.bzlp-benefits{grid-template-columns:1fr 1fr;}}
@media(max-width:520px){.bzlp-benefits{grid-template-columns:1fr;}}
.bzlp-benefit{background:#fff;border:1px solid var(--line);border-radius:16px;padding:24px;}
.bzlp-bi{width:48px;height:48px;border-radius:13px;background:linear-gradient(145deg,var(--blue),var(--blue2));
  color:#fff;display:flex;align-items:center;justify-content:center;margin-bottom:14px;}
.bzlp-benefit h3{font-size:16px;font-weight:800;margin:0 0 6px;}
.bzlp-benefit p{font-size:13.5px;line-height:1.5;color:var(--muted);margin:0;}

.bzlp-steps{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;}
@media(max-width:760px){.bzlp-steps{grid-template-columns:1fr;}}
.bzlp-step{text-align:center;padding:24px;}
.bzlp-si{width:60px;height:60px;border-radius:50%;background:#E7F1FD;color:var(--blue2);display:flex;align-items:center;justify-content:center;margin:0 auto 16px;}
.bzlp-step h3{font-size:17px;font-weight:800;margin:0 0 8px;color:var(--navy);}
.bzlp-step p{font-size:14px;line-height:1.55;color:var(--muted);margin:0;}

.bzlp-tools{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;}
@media(max-width:820px){.bzlp-tools{grid-template-columns:1fr;}}
.bzlp-tool{background:#fff;border:1px solid var(--line);border-radius:18px;overflow:hidden;box-shadow:0 6px 22px rgba(13,59,102,.05);}
.bzlp-tool-head{background:linear-gradient(135deg,var(--navy),var(--navy2));color:#fff;padding:22px;display:flex;gap:14px;align-items:center;}
.bzlp-ti{width:52px;height:52px;border-radius:14px;background:rgba(255,255,255,.14);display:flex;align-items:center;justify-content:center;}
.bzlp-tool-head h3{font-size:18px;font-weight:800;margin:0;}
.bzlp-tool-head span{font-size:12.5px;opacity:.85;}
.bzlp-tool ul{list-style:none;margin:0;padding:20px 22px;display:grid;gap:11px;}
.bzlp-tool li{position:relative;padding-left:22px;font-size:14px;color:var(--ink);}
.bzlp-tool li::before{content:"";position:absolute;left:0;top:6px;width:8px;height:8px;border-radius:50%;background:var(--blue);}
.bzlp-tools-cta{text-align:center;margin-top:36px;}

/* CITY */
.bzlp-city{padding:64px 0;background:linear-gradient(135deg,#0d3b66,#1d5fa7);color:#fff;}
.bzlp-city-in{display:grid;grid-template-columns:1fr 1fr;gap:44px;align-items:center;}
@media(max-width:820px){.bzlp-city-in{grid-template-columns:1fr;gap:28px;}}
.bzlp-city-txt h2{font-size:26px;font-weight:800;margin:12px 0 14px;line-height:1.2;}
.bzlp-city-txt p{font-size:15px;line-height:1.6;color:#d6e4f5;margin:0;}
.bzlp-city-list{display:grid;gap:14px;}
.bzlp-city-item{display:flex;gap:12px;align-items:flex-start;font-size:14.5px;line-height:1.45;}
.bzlp-tick{flex:0 0 auto;color:#7ec8ff;}
.bzlp-city-item b{color:#fff;}

/* FEATURES */
.bzlp-feats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;}
@media(max-width:760px){.bzlp-feats{grid-template-columns:1fr 1fr;}}
@media(max-width:460px){.bzlp-feats{grid-template-columns:1fr;}}
.bzlp-feat{display:flex;align-items:center;gap:13px;background:#fff;border:1px solid var(--line);border-radius:13px;padding:16px 18px;}
.bzlp-fi{flex:0 0 auto;width:40px;height:40px;border-radius:10px;background:#E7F1FD;color:var(--blue2);display:flex;align-items:center;justify-content:center;}
.bzlp-feat span{font-size:14.5px;font-weight:600;}

/* CTA */
.bzlp-cta{background:var(--navy);color:#fff;padding:52px 0;}
.bzlp-cta-in{display:flex;align-items:center;justify-content:space-between;gap:28px;flex-wrap:wrap;}
.bzlp-cta h2{font-size:25px;font-weight:800;margin:0 0 6px;}
.bzlp-cta p{font-size:15px;color:#d6e4f5;margin:0;}
.bzlp-cta-btns{display:flex;gap:12px;flex-wrap:wrap;}

/* FOOTER */
.bzlp-foot{background:#08243f;color:#a9c2dc;}
.bzlp-foot-in{display:grid;grid-template-columns:1.3fr 2fr;gap:36px;padding:48px 22px 32px;}
@media(max-width:760px){.bzlp-foot-in{grid-template-columns:1fr;gap:24px;}}
.bzlp-foot-brand p{font-size:13px;line-height:1.6;margin:14px 0 0;max-width:280px;}
.bzlp-foot-cols{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;}
@media(max-width:520px){.bzlp-foot-cols{grid-template-columns:1fr 1fr;}}
.bzlp-foot-cols h4{color:#fff;font-size:13px;letter-spacing:.06em;text-transform:uppercase;margin:0 0 12px;}
.bzlp-foot-cols a{display:block;font-size:13.5px;margin-bottom:9px;color:#a9c2dc;}
.bzlp-foot-cols a:hover{color:var(--blue);}
.bzlp-foot-bar{border-top:1px solid rgba(255,255,255,.08);text-align:center;padding:18px;font-size:12.5px;color:#7c98b4;}
`;
