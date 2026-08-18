import { useCallback, useEffect, useState } from "react";
import {
  ChevronDown, ChevronUp, Eye, FileText, Plus, RefreshCw, Save, Trash2, X,
} from "lucide-react";
import { apiFetch, apiPatch } from "../lib/api";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { PageFrame, SectionCard } from "../ui/common";
import TermsDialog from "../public/booking/TermsDialog";

interface Seccao { title: string; items: string[] }

const VAZIA: Seccao = { title: "", items: [""] };

/**
 * Termos e Condições, e a identificação do operador.
 *
 * Editam-se aqui porque mudam — uma política de cancelamento não devia precisar
 * de um programador. Gravam-se em **estrutura** (título + parágrafos) e nunca
 * como HTML: este texto vai parar à página de compra pública, e um campo de
 * HTML editável seria um campo por onde entra qualquer coisa no browser de
 * quem compra.
 *
 * Cada gravação que toque no texto sobe a versão. A versão viaja com cada
 * compra: sem a subir, uma alteração feita hoje passaria a valer para quem
 * aceitou os termos de ontem, e ninguém conseguiria dizer o que essa pessoa leu.
 */
export default function TermsPage() {
  const { token } = useAuth();

  const [empresa, setEmpresa] = useState({
    company_name: "", company_address: "", company_website: "",
    support_email: "", support_phone: "", emergency_phone: "",
  });
  const [telefones, setTelefones] = useState<string[]>([]);
  // Duas línguas, dois conjuntos. O passageiro lê os termos na língua que
  // escolheu; a inglesa vazia cai para a portuguesa no site — mais vale
  // mostrá-los na língua errada do que não mostrar termos nenhuns.
  const [lingua, setLingua] = useState<"pt" | "en">("pt");
  const [intro, setIntro] = useState("");
  const [fecho, setFecho] = useState("");
  const [seccoes, setSeccoes] = useState<Seccao[]>([]);
  const [introEn, setIntroEn] = useState("");
  const [fechoEn, setFechoEn] = useState("");
  const [seccoesEn, setSeccoesEn] = useState<Seccao[]>([]);

  const pt = lingua === "pt";
  const introActual = pt ? intro : introEn;
  const fechoActual = pt ? fecho : fechoEn;
  const seccoesActuais = pt ? seccoes : seccoesEn;
  const setIntroActual = pt ? setIntro : setIntroEn;
  const setFechoActual = pt ? setFecho : setFechoEn;
  const setSeccoesActuais = pt ? setSeccoes : setSeccoesEn;
  const [versao, setVersao] = useState("");
  const [actualizado, setActualizado] = useState<string | null>(null);

  const [carregado, setCarregado] = useState(false);
  const [aGravar, setAGravar] = useState(false);
  const [previa, setPrevia] = useState(false);

  const carregar = useCallback(() => {
    apiFetch("/api/branding/", token!)
      .then((d) => {
        setEmpresa({
          company_name: d?.company_name || "", company_address: d?.company_address || "",
          company_website: d?.company_website || "", support_email: d?.support_email || "",
          support_phone: d?.support_phone || "", emergency_phone: d?.emergency_phone || "",
        });
        setTelefones(d?.contact_phones || []);
        setIntro(d?.terms_intro || "");
        setFecho(d?.terms_closing || "");
        setSeccoes(d?.terms_sections || []);
        setIntroEn(d?.terms_intro_en || "");
        setFechoEn(d?.terms_closing_en || "");
        setSeccoesEn(d?.terms_sections_en || []);
        setVersao(d?.terms_version || "");
        setActualizado(d?.terms_updated_at || null);
        setCarregado(true);
      })
      .catch((e) => showToast("danger", e instanceof Error ? e.message : "Erro"));
  }, [token]);

  useEffect(() => { carregar(); }, [carregar]);

  const mexerSeccao = (i: number, mudanca: Partial<Seccao>) =>
    setSeccoesActuais((p) => p.map((s, j) => (j === i ? { ...s, ...mudanca } : s)));

  const mover = (i: number, delta: number) => setSeccoesActuais((p) => {
    const j = i + delta;
    if (j < 0 || j >= p.length) return p;
    const copia = [...p];
    [copia[i], copia[j]] = [copia[j], copia[i]];
    return copia;
  });

  const gravar = async () => {
    // Secções e parágrafos vazios não vão: um título sem nada por baixo
    // aparecia na página de compra como um buraco nos termos.
    const limpar = (lista: Seccao[]) => lista
      .map((s) => ({ title: s.title.trim(), items: s.items.map((i) => i.trim()).filter(Boolean) }))
      .filter((s) => s.title && s.items.length > 0);
    const limpas = limpar(seccoes);
    const limpasEn = limpar(seccoesEn);

    if (seccoes.length > 0 && limpas.length === 0) {
      showToast("danger", "Cada secção precisa de um título e de pelo menos um parágrafo.");
      return;
    }

    setAGravar(true);
    try {
      const r = await apiPatch("/api/branding/", token!, {
        ...empresa,
        contact_phones: telefones.map((t) => t.trim()).filter(Boolean),
        terms_intro: intro.trim(),
        terms_closing: fecho.trim(),
        terms_sections: limpas,
        terms_intro_en: introEn.trim(),
        terms_closing_en: fechoEn.trim(),
        terms_sections_en: limpasEn,
      });
      setSeccoes(limpas);
      setSeccoesEn(limpasEn);
      setVersao(r?.terms_version || versao);
      setActualizado(r?.terms_updated_at || actualizado);
      showToast("success", "Termos e contactos gravados.");
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro ao gravar.");
    } finally {
      setAGravar(false);
    }
  };

  return (
    <PageFrame
      kicker="Definições"
      title="Termos e Condições"
      description="O que o passageiro aceita ao comprar. Cada alteração sobe a versão, e a versão fica registada em cada compra."
      action={<>
        <button className="icon-text-button" type="button" onClick={() => setPrevia(true)}>
          <Eye size={16} /><span>Pré-visualizar</span>
        </button>
        <button className="icon-text-button" type="button" onClick={carregar}>
          <RefreshCw size={16} /><span>Recarregar</span>
        </button>
        <button className="primary-button" type="button" disabled={aGravar || !carregado} onClick={gravar}>
          <Save size={16} /> {aGravar ? "A gravar…" : "Gravar"}
        </button>
      </>}
    >
      <SectionCard title="Operador"
        description="Sai no rodapé da compra, no bilhete e nas apps. É a quem o passageiro liga quando algo corre mal.">
        <div className="admin-form-grid">
          <label className="field"><span>Nome da empresa</span>
            <input value={empresa.company_name} placeholder="TPM-TUR (PTY) — Transporte e Turismo"
              onChange={(e) => setEmpresa((p) => ({ ...p, company_name: e.target.value }))} />
          </label>
          <label className="field"><span>Sítio na internet</span>
            <input value={empresa.company_website} placeholder="www.tpmtur.co.mz"
              onChange={(e) => setEmpresa((p) => ({ ...p, company_website: e.target.value }))} />
          </label>
          <label className="field" style={{ gridColumn: "1 / -1" }}><span>Morada</span>
            <input value={empresa.company_address} placeholder="Rua da Resistência, Parcela 24, 1º Andar, Maputo"
              onChange={(e) => setEmpresa((p) => ({ ...p, company_address: e.target.value }))} />
          </label>
          <label className="field"><span>Email de apoio</span>
            <input type="email" value={empresa.support_email} placeholder="info@tpmtur.co.mz"
              onChange={(e) => setEmpresa((p) => ({ ...p, support_email: e.target.value }))} />
          </label>
          <label className="field"><span>Telefone de apoio</span>
            <input value={empresa.support_phone}
              onChange={(e) => setEmpresa((p) => ({ ...p, support_phone: e.target.value }))} />
          </label>
          <label className="field"><span>Linha de emergência</span>
            <input value={empresa.emergency_phone}
              onChange={(e) => setEmpresa((p) => ({ ...p, emergency_phone: e.target.value }))} />
            <small style={{ color: "var(--app-text-muted)", fontSize: 12 }}>
              Impressa no bilhete. Fica vazia para usar o telefone de apoio.
            </small>
          </label>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <span>Outros contactos</span>
            <div className="bzterms-phones">
              {telefones.map((n, i) => (
                <div className="bzterms-phone" key={i}>
                  <input value={n} placeholder="+258 …"
                    onChange={(e) => setTelefones(telefones.map((x, j) => (j === i ? e.target.value : x)))} />
                  <button type="button" className="bzsched-time-x" aria-label="Remover"
                    onClick={() => setTelefones(telefones.filter((_, j) => j !== i))}>
                    <X size={13} />
                  </button>
                </div>
              ))}
              <button type="button" className="bzsched-add" onClick={() => setTelefones([...telefones, ""])}>
                <Plus size={14} /> número
              </button>
            </div>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Texto dos termos"
        description={versao
          ? `Versão em vigor: ${versao}${actualizado ? ` · actualizada a ${new Date(actualizado).toLocaleDateString("pt-PT")}` : ""}`
          : "Ainda sem versão publicada."}>
        <div className="bzterms-langs" role="tablist" aria-label="Língua dos termos">
          {(["pt", "en"] as const).map((l) => (
            <button key={l} type="button" role="tab" aria-selected={lingua === l}
              className={`bzterms-lang${lingua === l ? " is-on" : ""}`}
              onClick={() => setLingua(l)}>
              {l === "pt" ? "Português" : "English"}
              <small>
                {(l === "pt" ? seccoes : seccoesEn).length} secção(ões)
              </small>
            </button>
          ))}
        </div>
        {!pt && seccoesEn.length === 0 ? (
          <p className="bzsched-note">
            Sem versão inglesa, o site mostra a portuguesa a quem escolher English —
            mais vale os termos na língua errada do que termos nenhuns.
          </p>
        ) : null}

        <label className="field"><span>Introdução</span>
          <textarea rows={2} value={introActual}
            placeholder={pt
              ? "Os passageiros embarcam sujeitos a certos requerimentos das nossas condições de embarque."
              : "Passengers are subject to the following terms:"}
            onChange={(e) => setIntroActual(e.target.value)} />
        </label>

        <div className="bzterms-sections">
          {seccoesActuais.map((s, i) => (
            <div className="bzterms-editor" key={i}>
              <div className="bzterms-editor-head">
                <span className="bzterms-num">{i + 1}</span>
                <input className="bzterms-title" value={s.title} placeholder="Título da secção (ex.: Bilhetes)"
                  onChange={(e) => mexerSeccao(i, { title: e.target.value })} />
                <div className="bzterms-editor-actions">
                  <button type="button" className="bzsched-time-x" aria-label="Subir"
                    disabled={i === 0} onClick={() => mover(i, -1)}><ChevronUp size={13} /></button>
                  <button type="button" className="bzsched-time-x" aria-label="Descer"
                    disabled={i === seccoesActuais.length - 1} onClick={() => mover(i, 1)}><ChevronDown size={13} /></button>
                  <button type="button" className="bzsched-time-x" aria-label="Eliminar secção"
                    onClick={() => setSeccoesActuais(seccoesActuais.filter((_, j) => j !== i))}><Trash2 size={13} /></button>
                </div>
              </div>
              {s.items.map((item, j) => (
                <div className="bzterms-item" key={j}>
                  <textarea rows={2} value={item} placeholder="Parágrafo"
                    onChange={(e) => mexerSeccao(i, {
                      items: s.items.map((x, k) => (k === j ? e.target.value : x)),
                    })} />
                  {s.items.length > 1 ? (
                    <button type="button" className="bzsched-time-x" aria-label="Remover parágrafo"
                      onClick={() => mexerSeccao(i, { items: s.items.filter((_, k) => k !== j) })}>
                      <X size={13} />
                    </button>
                  ) : null}
                </div>
              ))}
              <button type="button" className="bzsched-add"
                onClick={() => mexerSeccao(i, { items: [...s.items, ""] })}>
                <Plus size={14} /> parágrafo
              </button>
            </div>
          ))}
        </div>

        <button type="button" className="icon-text-button" style={{ marginTop: 12 }}
          onClick={() => setSeccoesActuais([...seccoesActuais, { ...VAZIA, items: [""] }])}>
          <FileText size={15} /><span>Nova secção</span>
        </button>

        <label className="field" style={{ marginTop: 16 }}><span>Fecho</span>
          <input value={fechoActual}
            placeholder={pt
              ? "A TPM-TUR deseja-lhe uma viagem segura e confortável."
              : "We wish you a safe and pleasant journey."}
            onChange={(e) => setFechoActual(e.target.value)} />
        </label>
      </SectionCard>

      <TermsDialog
        open={previa}
        onClose={() => setPrevia(false)}
        sections={seccoesActuais.filter((s) => s.title.trim() && s.items.some((i) => i.trim()))}
        intro={introActual}
        closing={fechoActual}
        company={empresa.company_name}
        version={versao}
        updatedAt={actualizado || undefined}
      />
    </PageFrame>
  );
}
