import { useEffect, useState } from "react";
import { Download, Smartphone, X } from "lucide-react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
}

const DISMISS_KEY = "buzup_pwa_dismissed_at";
const DISMISS_TTL_MS = 1000 * 60 * 60 * 24 * 7;

export default function PwaInstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);
  const [iosVisible, setIosVisible] = useState(false);
  const [installing, setInstalling] = useState(false);

  useEffect(() => {
    if (isStandalone()) return;
    const dismissedAt = Number(localStorage.getItem(DISMISS_KEY) || 0);
    if (dismissedAt && Date.now() - dismissedAt < DISMISS_TTL_MS) return;

    const handler = (e: Event) => {
      e.preventDefault();
      const ev = e as BeforeInstallPromptEvent;
      setDeferred(ev);
      setVisible(true);
    };
    window.addEventListener("beforeinstallprompt", handler);

    if (isIos() && !isStandalone()) {
      const t = setTimeout(() => setIosVisible(true), 1500);
      return () => { clearTimeout(t); window.removeEventListener("beforeinstallprompt", handler); };
    }

    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  async function install() {
    if (!deferred) return;
    setInstalling(true);
    try {
      await deferred.prompt();
      const choice = await deferred.userChoice;
      if (choice.outcome === "accepted") {
        setVisible(false);
      } else {
        dismiss();
      }
    } catch {}
    finally { setInstalling(false); }
  }

  function dismiss() {
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
    setVisible(false);
    setIosVisible(false);
  }

  if (visible) {
    return (
      <div className="pwa-install-banner" role="dialog" aria-label="Instalar BuzUp">
        <div className="pwa-install-icon"><Smartphone size={22} /></div>
        <div className="pwa-install-text">
          <strong>Instalar BuzUp</strong>
          <span>Acesso rapido a partir do ecra inicial</span>
        </div>
        <div className="pwa-install-actions">
          <button className="pwa-install-btn" onClick={install} type="button" disabled={installing}>
            <Download size={14} /> Instalar
          </button>
          <button className="pwa-install-close" onClick={dismiss} type="button" aria-label="Fechar">
            <X size={16} />
          </button>
        </div>
      </div>
    );
  }

  if (iosVisible) {
    return (
      <div className="pwa-install-banner" role="dialog" aria-label="Instalar BuzUp">
        <div className="pwa-install-icon"><Smartphone size={22} /></div>
        <div className="pwa-install-text">
          <strong>Instalar BuzUp</strong>
          <span>Toque em Partilhar e depois "Adicionar ao Ecra Inicial"</span>
        </div>
        <button className="pwa-install-close" onClick={dismiss} type="button" aria-label="Fechar">
          <X size={16} />
        </button>
      </div>
    );
  }

  return null;
}

function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  const matchMedia = window.matchMedia && window.matchMedia("(display-mode: standalone)").matches;
  const navStandalone = (window.navigator as Navigator & { standalone?: boolean }).standalone === true;
  return matchMedia || navStandalone;
}

function isIos(): boolean {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent || "";
  return /iPad|iPhone|iPod/.test(ua) && !(/CriOS|FxiOS/.test(ua));
}