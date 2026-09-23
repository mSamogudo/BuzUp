/** O que a compra sabe, sem saber desenhar nada.
 *
 *  Tipos, regras de documento e normalizacao vivem aqui porque agora ha duas
 *  paginas na mesma jornada — o `/comprar` escolhe percurso, partida e lugar,
 *  o `/checkout` recolhe quem viaja e cobra. Duas copias destas regras
 *  deixariam de concordar num dia qualquer, e o campo passaria a aceitar o
 *  que a compra recusa.
 */

export interface StopOpt { id: number; code: string; name: string }
export interface TripOpt {
  trip_id: number; route_id: number; route_code: string; route_name: string;
  origin_stop: string; destination_stop: string;
  vehicle: string | null; departure: string | null; fare_amount: string | null;
  /** Urbana, interprovincial ou internacional — decide que documentos servem. */
  service_type?: string;
  seats_available: number | null; on_sale: boolean; sale_unavailable_reason: string;
}
export interface Passenger { name: string; document_type: string; document_number: string; seat: string; return_seat: string }
export interface CheckoutResult {
  checkout_reference: string; payment_reference: string; total_amount: string;
  status: string; payment_status: string; detail_message: string; ticket_url: string;
  redirect_url?: string;
}

/// Forma de cada tipo de documento. Vem de `/api/public/document-types/`, o
/// mesmo sítio que o servidor usa para validar — escrever as regras outra vez
/// aqui garantia que um dia deixavam de concordar, e o campo passava a aceitar
/// o que a compra recusa.
export interface DocRule {
  value: string; label: string; pattern: string; max_length: number;
  placeholder: string; help: string; digits_only: boolean;
}

/// Usada só até as regras chegarem do servidor (e se a rede falhar): deixa o
/// formulário utilizável em vez de o bloquear.
/// Regras usadas enquanto `/api/public/document-types/` não responde.
///
/// Eram todas `4 a 32 caracteres` com ajuda vazia — mais FROUXAS do que as do
/// servidor. O campo aceitava 13 dígitos num BI (que precisa de 12 + letra),
/// deixava avançar, e a compra rebentava no fim com um erro que o comprador
/// nem via. Um recurso mais permissivo do que a regra real não é um recurso: é
/// uma armadilha que só aparece quando a rede está lenta.
///
/// Espelham agora as regras do servidor. Ele continua a ser a autoridade — isto
/// é só para o campo não mentir enquanto elas não chegam.
export const DOC_FALLBACK: DocRule[] = [
  { value: "bi", label: "Bilhete de Identidade", pattern: "^\\d{12}[A-Z]$",
    max_length: 13, placeholder: "110100123456A",
    help: "13 caracteres: 12 dígitos seguidos de uma letra.", digits_only: false },
  { value: "passport", label: "Passaporte", pattern: "^[A-Z0-9]{6,9}$",
    max_length: 9, placeholder: "AB1234567",
    help: "6 a 9 caracteres, só letras e números.", digits_only: false },
  { value: "dire", label: "DIRE", pattern: "^\\d{12}$",
    max_length: 12, placeholder: "123456789012",
    help: "12 dígitos.", digits_only: true },
  { value: "cedula", label: "Cédula", pattern: "^\\d{9}$",
    max_length: 9, placeholder: "123456789",
    help: "9 dígitos.", digits_only: true },
  { value: "other", label: "Outro", pattern: "^[A-Z0-9]{4,32}$",
    max_length: 32, placeholder: "Número do documento",
    help: "4 a 32 caracteres, só letras e números.", digits_only: false },
];

/// Um número moçambicano tem 9 dígitos (8X XXX XXXX). O campo passa a aceitar
/// só isso: deixar escrever 15 dígitos e recusar no fim é fazer o comprador
/// descobrir o erro depois de preencher tudo o resto.
export const TELEFONE_DIGITOS = 9;
export function filterPhone(raw: string) {
  return String(raw || "").replace(/\D/g, "").slice(0, TELEFONE_DIGITOS);
}

/// A mensagem que o servidor devolve, seja qual for a forma em que vem.
///
/// O DRF aninha os erros de campo — `{"passengers":[{"document_number":["..."]}]}`
/// — e o portal só olhava para `detail`. Um erro de documento chegava como
/// `undefined` e caía numa frase genérica: o comprador via "não foi possível
/// concluir a compra" sem saber que bastava corrigir um dígito.
export function readServerError(body: unknown, fallback: string): string {
  const primeira = (v: unknown, prefixo = ""): string => {
    if (typeof v === "string") return prefixo + v;
    if (Array.isArray(v)) {
      for (let i = 0; i < v.length; i += 1) {
        const achado = primeira(v[i], v.length > 1 ? `Passageiro ${i + 1}: ` : prefixo);
        if (achado) return achado;
      }
      return "";
    }
    if (v && typeof v === "object") {
      for (const val of Object.values(v as Record<string, unknown>)) {
        const achado = primeira(val, prefixo);
        if (achado) return achado;
      }
    }
    return "";
  };
  const b = body as Record<string, unknown> | null;
  if (b && typeof b.detail === "string" && b.detail) return b.detail;
  return primeira(body) || fallback;
}

/// Tira o que é só aspecto (espaços, traços) e põe em maiúsculas — a mesma
/// normalização que o servidor faz antes de gravar.
export function normalizeDoc(raw: string) {
  return raw.replace(/[\s.\-/]/g, "").toUpperCase();
}

/// O que o campo deixa mesmo escrever. Num documento só de dígitos (DIRE,
/// cédula) as letras nem entram: mais vale o campo não as aceitar do que
/// aceitá-las para depois reclamar.
export function filterDoc(raw: string, rule: DocRule) {
  const limpo = normalizeDoc(raw);
  return (rule.digits_only ? limpo.replace(/\D/g, "") : limpo)
    .slice(0, rule.max_length);
}

export async function getJson(path: string) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" } });
  const body = await res.json().catch(() => ({}));
  // Sem mensagem própria: quem chama tem uma traduzida para o caso. Esta
  // função vive fora do componente e não alcança o dicionário.
  if (!res.ok) throw new Error(body.detail || "");
  return body;
}

export function money(v: string | number | null | undefined) {
  const n = Number(v || 0);
  return n.toLocaleString("pt-PT", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function timeOf(iso: string | null) {
  if (!iso) return "--:--";
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function longDate(iso: string) {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString("pt-PT", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}
