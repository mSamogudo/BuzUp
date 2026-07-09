import { useEffect, useRef, useState, type FormEvent } from "react";
import { X, ArrowRight, Check, Loader2, BellRing } from "lucide-react";
import { submitContactLead } from "../../lib/api";
import { useMkt } from "./mkt-i18n";
import { onOpenWaitlist } from "./waitlist";

/** Single app-waitlist dialog, mounted once by PublicLayout. Opened from any
    "Baixar a app" / store-badge CTA while the app is pre-launch ("Em breve"). */
export function WaitlistModal() {
  const { t, locale } = useMkt();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const [emailErr, setEmailErr] = useState("");

  useEffect(() => onOpenWaitlist(() => {
    setDone(false);
    setError("");
    setEmailErr("");
    const dlg = dialogRef.current;
    if (dlg && !dlg.open) dlg.showModal();
  }), []);

  const close = () => dialogRef.current?.close();

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = formRef.current;
    if (!form || submitting) return;
    const data = new FormData(form);
    const email = String(data.get("email") ?? "").trim();
    if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      setEmailErr(t("Email inválido. Verifique o endereço."));
      form.querySelector<HTMLElement>('[name="email"]')?.focus();
      return;
    }
    setEmailErr("");
    setError("");
    setSubmitting(true);
    try {
      await submitContactLead({
        source: "waitlist",
        email,
        phone: String(data.get("phone") ?? "").trim(),
        locale,
        website: String(data.get("website") ?? ""),
      });
      setDone(true);
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : t("Não foi possível registar. Tente novamente."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <dialog
      ref={dialogRef}
      className="wl-dialog"
      onClick={(e) => { if (e.target === dialogRef.current) close(); }}
      aria-labelledby="wl-title"
    >
      <div className="wl-panel">
        <button type="button" className="wl-close" onClick={close} aria-label={t("Fechar")}><X /></button>

        {done ? (
          <div className="wl-success">
            <div className="wl-ico ok"><Check /></div>
            <h3 id="wl-title">{t("Está na lista!")}</h3>
            <p>{t("Avisamos assim que a app BusUp estiver disponível para descarregar.")}</p>
            <button type="button" className="btn btn-primary" onClick={close}>{t("Fechar")}</button>
          </div>
        ) : (
          <>
            <div className="wl-ico"><BellRing /></div>
            <h3 id="wl-title">{t("A app BusUp está quase a chegar.")}</h3>
            <p className="wl-lead">{t("Deixe o seu email e será dos primeiros a saber quando estiver disponível na App Store e Google Play.")}</p>
            <form ref={formRef} onSubmit={onSubmit} noValidate className="wl-form">
              <div className="hp-field" aria-hidden="true">
                <label htmlFor="wl-website">Website</label>
                <input type="text" id="wl-website" name="website" tabIndex={-1} autoComplete="off" />
              </div>
              <div className={`field${emailErr ? " err" : ""}`}>
                <label htmlFor="wl-email">{t("Email")}</label>
                <input
                  type="email" id="wl-email" name="email" placeholder={t("email@empresa.com")}
                  required inputMode="email" autoComplete="email"
                  aria-invalid={emailErr ? true : undefined}
                  aria-describedby={emailErr ? "wl-err-email" : undefined}
                  onInput={() => emailErr && setEmailErr("")}
                />
                {emailErr && <span className="err-msg" id="wl-err-email" role="alert">{emailErr}</span>}
              </div>
              <div className="field">
                <label htmlFor="wl-phone">{t("Telefone")} <span className="opt">({t("opcional")})</span></label>
                <input type="tel" id="wl-phone" name="phone" placeholder="+258 ..." autoComplete="tel" />
              </div>
              {error && <p className="form-error" role="alert">{error}</p>}
              <button type="submit" className="btn btn-primary btn-lg" disabled={submitting}>
                {submitting
                  ? <>{t("A registar…")} <Loader2 className="spin" /></>
                  : <>{t("Avisem-me")} <ArrowRight /></>}
              </button>
            </form>
          </>
        )}
      </div>
    </dialog>
  );
}
