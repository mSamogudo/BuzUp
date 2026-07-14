import { useEffect, useState } from "react";
import { Download, Smartphone, X } from "lucide-react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
}

const DISMISS_KEY = "buzup_pwa_dismissed_at";
const DISMISS_TTL_MS = 1000 * 60 * 60 * 24 * 7;
const SCROLL_GATE_PX = 600;
const TIME_GATE_MS = 8000;

export default function PwaInstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [iosEligible, setIosEligible] = useState(false);
  const [gate, setGate] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [installing, setInstalling] = useState(false);

  useEffect(() => {
    if (isStandalone()) return;
    const dismissedAt = Number(localStorage.getItem(DISMISS_KEY) || 0);
    if (dismissedAt && Date.now() - dismissedAt < DISMISS_TTL_MS) return;

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", handler);
    if (isIos() && !isStandalone()) setIosEligible(true);

    // Don't interrupt the hero: reveal only after the user scrolls past it or
    // after a grace period, whichever comes first — so the prompt never lands
    // on first paint over the landing's own CTAs.
    let opened = false;
    const open = () => {
      if (opened) return;
      opened = true;
      setGate(true);
      window.removeEventListener("scroll", onScroll);
    };
    const onScroll = () => {
      if (window.scrollY > SCROLL_GATE_PX) open();
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    const timer = setTimeout(open, TIME_GATE_MS);

    return () => {
      window.removeEventListener("beforeinstallprompt", handler);
      window.removeEventListener("scroll", onScroll);
      clearTimeout(timer);
    };
  }, []);

  async function install() {
    if (!deferred) return;
    setInstalling(true);
    try {
      await deferred.prompt();
      const choice = await deferred.userChoice;
      if (choice.outcome === "accepted") {
        setDeferred(null);
      } else {
        dismiss();
      }
    } catch {}
    finally { setInstalling(false); }
  }

  function dismiss() {
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
    setDismissed(true);
  }

  const showAndroid = gate && !dismissed && !!deferred;
  const showIos = gate && !dismissed && iosEligible && !deferred;

  if (showAndroid) {
    return (
      <div className="pwa-install-banner" role="dialog" aria-label="Adicionar a BusUp ao ecrã inicial">
        <div className="pwa-install-icon"><Smartphone size={22} /></div>
        <div className="pwa-install-text">
          <strong>BusUp no seu ecrã inicial</strong>
          <span>Acesso rápido, sem esperar pela loja de apps</span>
        </div>
        <div className="pwa-install-actions">
          <button className="pwa-install-btn" onClick={install} type="button" disabled={installing}>
            <Download size={14} /> Adicionar
          </button>
          <button className="pwa-install-close" onClick={dismiss} type="button" aria-label="Fechar">
            <X size={16} />
          </button>
        </div>
      </div>
    );
  }

  if (showIos) {
    return (
      <div className="pwa-install-banner" role="dialog" aria-label="Adicionar a BusUp ao ecrã inicial">
        <div className="pwa-install-icon"><Smartphone size={22} /></div>
        <div className="pwa-install-text">
          <strong>BusUp no seu ecrã inicial</strong>
          <span>Toque em Partilhar e depois "Adicionar ao Ecrã Inicial"</span>
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
