import { useState, type FormEvent } from "react";
import { RefreshCw, Save, Upload } from "lucide-react";
import { apiUpload } from "../lib/api";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { useBranding, type Branding } from "../lib/branding";
import { PageFrame, SectionCard } from "../ui/common";

type Slot = { key: keyof Branding; urlKey: keyof Branding; label: string; hint: string };

// Cada slot mapeia para um campo do backend (apps/branding/models.py LOGO_FIELDS).
const SLOTS: Slot[] = [
  { key: "primary_logo_url", urlKey: "primary_logo_url", label: "Logo principal", hint: "Fallback global quando um slot especifico nao esta definido." },
  { key: "sidebar_logo_url", urlKey: "sidebar_logo_url", label: "Logo do portal (sidebar)", hint: "Cabecalho do portal com a barra lateral expandida." },
  { key: "sidebar_mark_url", urlKey: "sidebar_mark_url", label: "Marca compacta (sidebar recolhida)", hint: "Icone quadrado para a barra lateral recolhida." },
  { key: "auth_logo_url", urlKey: "auth_logo_url", label: "Logo da pagina de login", hint: "Ecra de autenticacao do portal." },
  { key: "pos_logo_url", urlKey: "pos_logo_url", label: "Logo da app POS", hint: "Aplicacao dos terminais (motoristas/agentes)." },
  { key: "mobile_logo_url", urlKey: "mobile_logo_url", label: "Logo da app do passageiro", hint: "Aplicacao movel dos passageiros." },
  { key: "report_logo_url", urlKey: "report_logo_url", label: "Logo dos relatorios (PDF)", hint: "Cabecalho dos relatorios e documentos PDF." },
  { key: "powered_by_logo_url", urlKey: "powered_by_logo_url", label: "Logo \"powered by\" (UpDigital)", hint: "Rodape do portal e dos relatorios." },
  { key: "favicon_url", urlKey: "favicon_url", label: "Favicon do portal", hint: "Icone do separador do navegador." },
];

// keys do FormData = nomes dos FileField no backend (sem o sufixo _url)
function fieldName(urlKey: string): string {
  return urlKey.replace(/_url$/, "");
}

export default function BrandingPage() {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const { branding, reload } = useBranding();
  const [name, setName] = useState<string | null>(null);
  const [files, setFiles] = useState<Record<string, File>>({});
  const [previews, setPreviews] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const pickFile = (urlKey: string, file: File | null) => {
    setFiles((p) => {
      const next = { ...p };
      if (file) next[urlKey] = file; else delete next[urlKey];
      return next;
    });
    setPreviews((p) => ({ ...p, [urlKey]: file ? URL.createObjectURL(file) : "" }));
  };

  const dirty = name !== null || Object.keys(files).length > 0;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!dirty) return;
    setBusy(true);
    try {
      const form = new FormData();
      if (name !== null) form.append("platform_name", name);
      for (const [urlKey, file] of Object.entries(files)) {
        form.append(fieldName(urlKey), file);
      }
      await apiUpload("/api/branding/", token!, form, "PATCH");
      showToast("success", "Marca actualizada.");
      setFiles({});
      setPreviews({});
      setName(null);
      reload();
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro");
    } finally {
      setBusy(false);
    }
  };

  return (
    <PageFrame kicker={t(lc, "system")} title={t(lc, "branding")}
      action={
        <button className="icon-text-button" onClick={reload} type="button">
          <RefreshCw size={16} /><span>{t(lc, "refresh")}</span>
        </button>
      }>
      <form className="admin-form" onSubmit={submit}>
        <SectionCard title="Identidade">
          <label className="field" style={{ maxWidth: 360 }}>
            <span>Nome da plataforma</span>
            <input
              value={name ?? branding.platform_name ?? ""}
              onChange={(e) => setName(e.target.value)}
              placeholder="BuzUp"
            />
          </label>
        </SectionCard>

        <SectionCard title="Logos">
          <div className="branding-grid">
            {SLOTS.map((slot) => {
              const current = previews[slot.urlKey] || (branding[slot.urlKey] as string) || "";
              return (
                <div className="branding-slot" key={slot.urlKey}>
                  <div className="branding-slot-preview">
                    {current
                      ? <img src={current} alt={slot.label} />
                      : <span className="branding-slot-empty">Sem logo</span>}
                  </div>
                  <div className="branding-slot-meta">
                    <strong>{slot.label}</strong>
                    <span className="branding-slot-hint">{slot.hint}</span>
                    <label className="branding-slot-upload">
                      <Upload size={14} />
                      <span>{files[slot.urlKey] ? files[slot.urlKey].name : "Escolher ficheiro"}</span>
                      <input
                        type="file"
                        accept="image/png,image/jpeg,image/webp,image/svg+xml,image/gif,image/x-icon"
                        onChange={(e) => pickFile(slot.urlKey, e.target.files?.[0] ?? null)}
                      />
                    </label>
                  </div>
                </div>
              );
            })}
          </div>
        </SectionCard>

        <div className="admin-form-actions">
          <button className="primary-button" disabled={busy || !dirty} type="submit">
            <Save size={16} /> {busy ? t(lc, "saving") : t(lc, "save")}
          </button>
        </div>
      </form>
    </PageFrame>
  );
}
