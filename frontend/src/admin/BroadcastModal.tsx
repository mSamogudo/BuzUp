import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Loader2, Send, Users } from "lucide-react";
import { apiPost } from "../lib/api";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { AdminModal } from "../ui/common";

const LIMITE = 320;

interface Previa {
  recipients: number;
  segments: number;
  messages: number;
  target: string;
  sample: { phone: string; passengers: string[]; passes: number }[];
}

/**
 * Aviso por SMS a quem vai a bordo.
 *
 * Dois passos de propósito. Cada mensagem é paga, chega a um telemóvel de uma
 * pessoa real e não se desfaz — quem envia vê quantas pessoas vai tocar, e
 * quanto custa, **antes** de tocar nelas.
 */
export default function BroadcastModal({
  open, onClose, tripId, routeId, contexto,
}: {
  open: boolean;
  onClose: () => void;
  tripId?: number;
  routeId?: number;
  /** O que se está a avisar, para o utilizador confirmar que é o alvo certo. */
  contexto?: string;
}) {
  const { token } = useAuth();
  const [texto, setTexto] = useState("");
  const [previa, setPrevia] = useState<Previa | null>(null);
  const [aCarregar, setACarregar] = useState(false);
  const [aEnviar, setAEnviar] = useState(false);
  const [erro, setErro] = useState("");

  const corpo = useCallback((extra: Record<string, unknown>) => ({
    ...(tripId ? { trip_id: tripId } : {}),
    ...(routeId ? { route_id: routeId } : {}),
    ...extra,
  }), [tripId, routeId]);

  useEffect(() => {
    if (open) { setTexto(""); setPrevia(null); setErro(""); }
  }, [open]);

  // A prévia acompanha o texto: o custo muda quando a mensagem passa dos 160
  // caracteres, e é nessa altura que interessa vê-lo.
  useEffect(() => {
    if (!open || !token) return;
    let cancelado = false;
    const id = window.setTimeout(() => {
      setACarregar(true);
      apiPost("/api/admin/broadcasts/", token, corpo({ preview: true, body: texto }))
        .then((r) => { if (!cancelado) { setPrevia(r as Previa); setErro(""); } })
        .catch((e) => { if (!cancelado) { setPrevia(null); setErro(e instanceof Error ? e.message : "Erro"); } })
        .finally(() => { if (!cancelado) setACarregar(false); });
    }, 250);
    return () => { cancelado = true; window.clearTimeout(id); };
  }, [open, token, texto, corpo]);

  const enviar = async () => {
    setAEnviar(true);
    try {
      const r = await apiPost("/api/admin/broadcasts/", token!, corpo({ body: texto }));
      const enviadas = Number(r?.sent ?? 0);
      const falhadas = Number(r?.failed ?? 0);
      showToast(falhadas > 0 ? "danger" : "success",
        falhadas > 0
          ? `${enviadas} aviso(s) enviado(s), ${falhadas} falhou/falharam.`
          : `${enviadas} aviso(s) enviado(s).`);
      onClose();
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro ao enviar.");
    } finally {
      setAEnviar(false);
    }
  };

  const ninguem = previa !== null && previa.recipients === 0;
  const pronto = texto.trim().length > 0 && !ninguem && !aCarregar;

  return (
    <AdminModal open={open} onClose={onClose}
      title="Avisar quem vai a bordo"
      description="Chega a quem tem bilhete activo ou já validado numa viagem que ainda não terminou. Quem já viajou não é incomodado.">
      <form className="admin-form" onSubmit={(e) => { e.preventDefault(); void enviar(); }}>
        {contexto ? (
          <div className="bztw-preview" style={{ minHeight: 0, marginTop: 0 }}>
            <div className="bztw-headline" style={{ marginBottom: 0 }}>
              <div className="bztw-range"><Users size={14} /> {contexto}</div>
            </div>
          </div>
        ) : null}

        <label className="field">
          <span>Mensagem</span>
          <textarea rows={4} value={texto} maxLength={LIMITE} required
            placeholder="ex.: Avaria na estrada. O autocarro segue viagem às 14h00. Pedimos desculpa."
            onChange={(e) => setTexto(e.target.value)} />
          <small style={{ opacity: 0.7 }}>
            {texto.length}/{LIMITE} caracteres
            {previa && previa.segments > 1
              ? ` · ${previa.segments} mensagens por pessoa (acima de 160 caracteres cada SMS conta como duas)`
              : ""}
          </small>
        </label>

        <div className="bztw-preview">
          {aCarregar ? (
            <div className="bztw-preview-empty"><Loader2 className="bztw-spin" size={16} /> A contar…</div>
          ) : erro ? (
            <div className="bztw-preview-empty bztw-error"><AlertTriangle size={16} /> {erro}</div>
          ) : previa ? (
            <>
              <div className="bztw-headline">
                <div className={`bztw-count${ninguem ? " is-zero" : ""}`}>
                  {ninguem ? <AlertTriangle size={20} /> : <Users size={20} />}
                  <strong>{previa.recipients}</strong>
                  <span>{previa.recipients === 1 ? "pessoa a avisar" : "pessoas a avisar"}</span>
                </div>
                {previa.messages > 0 ? (
                  <div className="bztw-range">{previa.messages} SMS no total</div>
                ) : null}
              </div>
              {ninguem ? (
                <p className="bztw-note">
                  Ninguém a bordo. Ou não há bilhetes vendidos, ou a viagem já terminou —
                  e quem já viajou não recebe avisos.
                </p>
              ) : (
                <ul className="bztw-schedules">
                  {previa.sample.map((d, i) => (
                    <li key={i}>
                      <span>{d.passengers.join(", ") || "—"}</span>
                      <strong>{d.phone}{d.passes > 1 ? ` · ${d.passes} bilhetes` : ""}</strong>
                    </li>
                  ))}
                  {previa.recipients > previa.sample.length ? (
                    <li className="bztw-more">
                      <span>+ {previa.recipients - previa.sample.length} destinatário(s)</span>
                    </li>
                  ) : null}
                </ul>
              )}
            </>
          ) : null}
        </div>

        <div className="admin-form-actions">
          <button className="primary-button" type="submit" disabled={!pronto || aEnviar}>
            {aEnviar ? "A enviar…" : (
              <><Send size={16} />{previa ? ` Enviar a ${previa.recipients}` : " Enviar"}</>
            )}
          </button>
          <button className="secondary-button" type="button" onClick={onClose}>Cancelar</button>
        </div>
        <small style={{ opacity: 0.7 }}>
          O envio fica registado com o seu nome, a mensagem e quantas chegaram.
        </small>
      </form>
    </AdminModal>
  );
}
