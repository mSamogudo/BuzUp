import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Smartphone, ScanLine, Download, ShieldCheck, ArrowLeft,
  CheckCircle2, Info, Store,
} from "lucide-react";
import { apiPublic } from "../lib/api";
import { useBranding, pickLogo } from "../lib/branding";

interface AppInfo {
  available: boolean;
  slug: string;
  version_name?: string;
  version_code?: number;
  file_size_bytes?: number;
  release_notes?: string;
  published_at?: string;
  download_url?: string;
}
interface LatestInfo {
  passageiro: AppInfo;
  pos: AppInfo;
}

function fmtSize(bytes?: number): string {
  if (!bytes) return "";
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(1)} MB`;
}

function Wordmark({ url, alt, height = 30 }: { url: string; alt: string; height?: number }) {
  if (url) return <img src={url} alt={alt} style={{ height, display: "block" }} />;
  return (
    <span style={{ fontWeight: 800, fontSize: height * 0.8, letterSpacing: "-0.02em" }}>
      Bus<span style={{ color: "#2D8CF0" }}>Up</span>
    </span>
  );
}

function AppCard({
  info, kind,
}: {
  info: AppInfo;
  kind: "passageiro" | "pos";
}) {
  const isPsg = kind === "passageiro";
  const title = isPsg ? "App Passageiro" : "App POS";
  const tag = isPsg ? "Para passageiros · Android" : "Para agentes e motoristas · Android";
  const desc = isPsg
    ? "Carregue saldo, compre bilhetes e valide as suas viagens com o telemóvel."
    : "Venda e valide bilhetes por QR Code e cartão NFC nos terminais SUNMI / Urovo.";
  const Icon = isPsg ? Smartphone : ScanLine;
  const features = isPsg
    ? ["Carteira digital em Meticais", "Recarga por M-Pesa e e-Mola", "Bilhete por QR Code", "Histórico de viagens"]
    : ["Venda e validação de bilhetes", "Leitura QR + cartão NFC", "Sinal sonoro de confirmação", "Atualização automática (OTA)"];

  return (
    <div className="bzdl-card">
      <div className="bzdl-card-head">
        <div className="bzdl-appicon"><Icon size={30} strokeWidth={2} /></div>
        <div>
          <h2>{title}</h2>
          <div className="bzdl-tag">{tag}</div>
        </div>
      </div>
      <p className="bzdl-desc">{desc}</p>
      <ul className="bzdl-feats">
        {features.map((f) => (
          <li key={f}><CheckCircle2 size={16} /> {f}</li>
        ))}
      </ul>
      <div className="bzdl-actions">
        {info?.available ? (
          <>
            <a className="bzdl-btn" href={info.download_url} rel="nofollow">
              <Download size={18} /> Baixar APK
            </a>
            <div className="bzdl-meta">
              <span className="bzdl-ver">v{info.version_name}</span>
              {info.file_size_bytes ? <span>· {fmtSize(info.file_size_bytes)}</span> : null}
            </div>
          </>
        ) : (
          <span className="bzdl-soon">Em breve</span>
        )}
      </div>
    </div>
  );
}

export default function DownloadPage() {
  const { branding } = useBranding();
  const [info, setInfo] = useState<LatestInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    document.title = "Descarregar apps · BusUp";
    apiPublic("/api/apps/latest/")
      .then((d) => setInfo(d))
      .catch(() => setInfo(null))
      .finally(() => setLoading(false));
  }, []);

  const darkLogo = pickLogo(branding.sidebar_logo_url, branding.primary_logo_url);

  const empty: AppInfo = { available: false, slug: "" };

  return (
    <div className="bzdl">
      <style>{CSS}</style>

      <header className="bzdl-top">
        <Link to="/" className="bzdl-brand"><Wordmark url={darkLogo} alt="BusUp" height={28} /></Link>
        <Link to="/" className="bzdl-back"><ArrowLeft size={16} /> Voltar ao início</Link>
      </header>

      <main className="bzdl-main">
        <div className="bzdl-hero">
          <span className="bzdl-pill">Aplicações Android</span>
          <h1>Descarregue as aplicações <span>BusUp</span></h1>
          <p>Escolha a app certa para si. Instale em segundos, direto no seu telemóvel Android.</p>
        </div>

        <div className="bzdl-grid">
          <AppCard kind="passageiro" info={info?.passageiro ?? empty} />
          <AppCard kind="pos" info={info?.pos ?? empty} />
        </div>

        {loading && <div className="bzdl-loading">A carregar versões…</div>}

        <section className="bzdl-how">
          <h3><Info size={18} /> Como instalar no Android</h3>
          <ol>
            <li><b>Toque em “Baixar APK”</b> na app que pretende instalar.</li>
            <li>Quando o download terminar, <b>abra o ficheiro</b> transferido.</li>
            <li>Se aparecer um aviso, permita <b>“Instalar de fontes desconhecidas”</b> para o seu navegador.</li>
            <li>Confirme a instalação e <b>abra a aplicação</b>. Pronto! 🚌</li>
          </ol>
          <div className="bzdl-note">
            <ShieldCheck size={16} /> As aplicações são distribuídas diretamente pela BusUp. Baixe apenas a partir deste site oficial.
          </div>
        </section>

        <div className="bzdl-store">
          <Store size={16} /> Está a operar uma frota? Fale connosco para configurar os terminais do seu município.
        </div>
      </main>

      <footer className="bzdl-foot">
        <Wordmark url={darkLogo} alt="BusUp" height={22} />
        <span>Transporte público cashless · Moçambique</span>
        <a href="https://updigital.co.mz" target="_blank" rel="noreferrer">updigital.co.mz</a>
      </footer>
    </div>
  );
}

const CSS = `
.bzdl{--navy:#0D3B66;--navy2:#0A2E50;--blue:#2D8CF0;--blue2:#1D5FA7;--ink:#0F1B2D;--muted:#5B6B7F;--line:#E4EBF3;--bg:#F6F9FD;
  min-height:100vh;display:flex;flex-direction:column;background:var(--bg);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;}
.bzdl a{text-decoration:none;}
.bzdl-top{background:linear-gradient(150deg,var(--navy),var(--navy2));color:#fff;
  display:flex;align-items:center;justify-content:space-between;padding:16px 24px;}
.bzdl-brand{color:#fff;}
.bzdl-back{color:#cfe0f3;display:inline-flex;align-items:center;gap:6px;font-size:14px;font-weight:600;}
.bzdl-back:hover{color:#fff;}
.bzdl-main{flex:1;width:100%;max-width:960px;margin:0 auto;padding:40px 20px 24px;}
.bzdl-hero{text-align:center;margin-bottom:32px;}
.bzdl-pill{display:inline-block;background:#E7F1FD;color:var(--blue2);font-weight:700;font-size:12px;
  letter-spacing:.08em;text-transform:uppercase;padding:6px 14px;border-radius:30px;}
.bzdl-hero h1{font-size:30px;font-weight:800;margin:14px 0 8px;line-height:1.15;}
.bzdl-hero h1 span{color:var(--blue);}
.bzdl-hero p{color:var(--muted);font-size:15px;max-width:520px;margin:0 auto;line-height:1.5;}
.bzdl-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;}
@media(max-width:720px){.bzdl-grid{grid-template-columns:1fr;}.bzdl-hero h1{font-size:24px;}}
.bzdl-card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:24px;
  box-shadow:0 6px 22px rgba(13,59,102,.06);display:flex;flex-direction:column;}
.bzdl-card-head{display:flex;gap:14px;align-items:center;margin-bottom:14px;}
.bzdl-appicon{flex:0 0 56px;height:56px;border-radius:15px;color:#fff;
  background:linear-gradient(145deg,var(--blue),var(--blue2));display:flex;align-items:center;justify-content:center;}
.bzdl-card h2{font-size:19px;font-weight:800;margin:0;}
.bzdl-tag{font-size:12.5px;color:var(--muted);margin-top:2px;}
.bzdl-desc{font-size:14px;color:var(--muted);line-height:1.5;margin:0 0 14px;}
.bzdl-feats{list-style:none;padding:0;margin:0 0 18px;display:grid;gap:9px;}
.bzdl-feats li{display:flex;align-items:center;gap:8px;font-size:13.5px;color:var(--ink);}
.bzdl-feats li svg{color:var(--blue);flex:0 0 auto;}
.bzdl-actions{margin-top:auto;display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.bzdl-btn{display:inline-flex;align-items:center;gap:9px;background:var(--blue);color:#fff;font-weight:700;font-size:15px;
  padding:13px 22px;border-radius:12px;transition:background .15s;}
.bzdl-btn:hover{background:var(--blue2);}
.bzdl-meta{font-size:13px;color:var(--muted);display:flex;gap:5px;align-items:center;}
.bzdl-ver{font-weight:700;color:var(--ink);}
.bzdl-soon{color:var(--muted);font-style:italic;font-size:14px;}
.bzdl-loading{text-align:center;color:var(--muted);font-size:13px;margin-top:16px;}
.bzdl-how{background:#fff;border:1px solid var(--line);border-radius:18px;padding:24px 26px;margin-top:28px;}
.bzdl-how h3{display:flex;align-items:center;gap:8px;font-size:16px;margin:0 0 14px;color:var(--navy);}
.bzdl-how ol{margin:0;padding-left:20px;display:grid;gap:9px;}
.bzdl-how li{font-size:14px;line-height:1.5;color:var(--ink);}
.bzdl-note{display:flex;align-items:center;gap:8px;margin-top:16px;padding:12px 14px;background:#EAF6EE;
  border-radius:10px;font-size:13px;color:#1E6B3A;}
.bzdl-note svg{flex:0 0 auto;color:#2E9E56;}
.bzdl-store{display:flex;align-items:center;gap:8px;justify-content:center;margin-top:22px;
  font-size:13px;color:var(--muted);text-align:center;}
.bzdl-foot{background:var(--navy);color:#cfe0f3;display:flex;align-items:center;justify-content:center;gap:14px;
  flex-wrap:wrap;padding:20px;font-size:12.5px;margin-top:24px;}
.bzdl-foot a{color:var(--blue);font-weight:700;}
`;
