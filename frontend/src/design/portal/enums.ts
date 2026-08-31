/* eslint-disable */
/**
 * Rótulos PT e tom da pílula para os enums da API.
 *
 * Portado verbatim do objecto `EN` de docs/design-handoff/design/Portal BusUp v2.dc.html.
 * Regra do handoff (02-tokens-e-padroes.md §10): o valor do enum vem da API; o
 * rótulo e o tom vêm daqui. Um valor sem tradução mostra-se cru, com tom `mute`
 * — nunca rebenta.
 */

export type Tone = "ok" | "warn" | "bad" | "info" | "mute";
export type EnumEntry = [label: string, tone: Tone];
export type EnumGroup = Record<string, EnumEntry>;

export const ENUM_LABELS: Record<string, EnumGroup> = {
  trip: { scheduled: ["Agendada", "mute"], boarding: ["Embarque", "info"], departed: ["Em viagem", "info"], paused: ["Em pausa", "warn"], completed: ["Concluída", "ok"], cancelled: ["Cancelada", "bad"] },
  act3: { active: ["Activa", "ok"], inactive: ["Inactiva", "mute"], suspended: ["Suspensa", "warn"] },
  act2: { active: ["Activo", "ok"], inactive: ["Inactivo", "mute"] },
  vehicle: { active: ["Activo", "ok"], maintenance: ["Manutenção", "warn"], retired: ["Retirado", "mute"] },
  person: { active: ["Activo", "ok"], inactive: ["Inactivo", "mute"], suspended: ["Suspenso", "warn"] },
  passenger: { active: ["Activo", "ok"], blocked: ["Bloqueado", "bad"], suspended: ["Suspenso", "warn"], closed: ["Encerrado", "mute"] },
  card: { inactive: ["Inactivo", "mute"], active: ["Activo", "ok"], blocked: ["Bloqueado", "bad"], lost: ["Perdido", "warn"], replaced: ["Substituído", "info"], retired: ["Retirado", "mute"] },
  calc: { fixed: ["Fixa", "info"], origin_destination: ["Origem–destino", "info"], distance: ["Distância", "info"], zone: ["Zona", "info"] },
  product: { single_trip: ["Viagem única", "info"], daily_pass: ["Passe diário", "info"], weekly_pass: ["Passe semanal", "info"], monthly_pass: ["Passe mensal", "info"] },
  klass: { standard: ["Normal", "mute"], student: ["Estudante", "info"], senior: ["Sénior", "info"], child: ["Criança", "info"] },
  fee: { card_issuance: ["Emissão de cartão", "info"], card_recovery: ["Recuperação de cartão", "info"], fine: ["Multa", "warn"], other: ["Outro", "mute"] },
  service: { urban: ["Urbano", "info"], interprovincial: ["Interprovincial", "info"], international: ["Internacional", "info"] },
  doc: { bi: ["BI", "mute"], passport: ["Passaporte", "mute"], driving_license: ["Carta de condução", "mute"] },
  cardtype: { physical: ["Físico", "mute"], digital: ["Digital", "info"] },
  bool: { sim: ["Sim", "ok"], nao: ["Não", "mute"] },
  dayclose: { closed: ["Fechado", "ok"], open: ["Aberto", "warn"] },
  shift: { open: ["Aberto", "warn"], closed: ["Fechado", "info"], reconciled: ["Conferido", "ok"], divergent: ["Divergente", "bad"] },
  tech: { nfc_uid: ["UID NFC", "mute"], mifare_classic: ["Mifare Classic", "mute"], mifare_desfire: ["Mifare DESFire", "mute"], qr_code: ["Código QR", "mute"], other: ["Outro", "mute"] },
  wallet: { active: ["Activa", "ok"], blocked: ["Bloqueada", "bad"], closed: ["Encerrada", "mute"] },
  wtype: { topup: ["Recarga", "ok"], fare_debit: ["Débito de tarifa", "info"], refund: ["Reembolso", "warn"], reversal: ["Reversão", "warn"], adjustment: ["Ajuste", "mute"], card_transfer: ["Transferência de cartão", "info"], fee: ["Taxa", "mute"] },
  wdir: { credit: ["Crédito", "ok"], debit: ["Débito", "info"] },
  wtx: { pending: ["Pendente", "warn"], confirmed: ["Confirmada", "ok"], failed: ["Falhada", "bad"], reversed: ["Revertida", "mute"] },
  ppkg: { active: ["Activo", "ok"], expired: ["Expirado", "mute"], cancelled: ["Cancelado", "bad"], exhausted: ["Esgotado", "warn"] },
  disc: { percentage: ["Percentagem", "info"], fixed_amount: ["Valor fixo", "info"], free_trips: ["Viagens grátis", "info"] },
  guest: { draft: ["Rascunho", "mute"], payment_pending: ["Pagamento pendente", "warn"], paid: ["Pago", "info"], issued: ["Emitido", "ok"], expired: ["Expirado", "mute"], cancelled: ["Cancelado", "bad"], refunded: ["Reembolsado", "warn"] },
  vstat: { approved: ["Aprovada", "ok"], denied: ["Negada", "bad"] },
  vtype: { card_pay_as_you_go: ["Cartão", "info"], qr_pay_as_you_go: ["QR", "info"], digital_travel_pass: ["Passe digital", "info"], guest_digital_travel_pass: ["Passe de visitante", "info"] },
  vfail: { insufficient_balance: ["Saldo insuficiente", "bad"], card_blocked: ["Cartão bloqueado", "bad"], account_blocked: ["Conta bloqueada", "bad"], pass_already_used: ["Passe já usado", "warn"], pass_expired: ["Passe expirado", "warn"], invalid_token: ["Token inválido", "bad"], route_not_allowed: ["Rota não permitida", "warn"], device_blocked: ["Dispositivo bloqueado", "bad"], no_fare_found: ["Sem tarifa aplicável", "warn"], no_ticket_for_route: ["Sem bilhete para a rota", "warn"] },
  pay: { created: ["Criada", "mute"], pending: ["Pendente", "warn"], confirmed: ["Confirmada", "ok"], failed: ["Falhada", "bad"], expired: ["Expirada", "mute"], reversed: ["Revertida", "warn"] },
  purpose: { mobile_wallet_topup: ["Recarga na app", "info"], pos_card_topup: ["Recarga no POS", "info"], guest_travel_pass_purchase: ["Passe de visitante", "info"], app_travel_pass_purchase: ["Passe na app", "info"], direct_trip_payment: ["Pagamento de viagem", "info"], refund: ["Reembolso", "warn"] },
  possess: { active: ["Aberta", "warn"], closed: ["Fechada", "ok"] },
  device: { self_onboarded: ["Auto-registado", "mute"], pending_activation: ["Activação pendente", "warn"], pending_configuration: ["Configuração pendente", "warn"], active: ["Activo", "ok"], rejected: ["Rejeitado", "bad"], blocked: ["Bloqueado", "bad"], retired: ["Retirado", "mute"] },
  devtype: { urovo_i9100_pos: ["Urovo i9100", "mute"], sunmi_v2s_pos: ["Sunmi V2s", "mute"], mobile_app: ["App móvel", "mute"], admin_browser: ["Navegador", "mute"] },
  devact: { pending: ["Pendente", "warn"], approved: ["Aprovada", "ok"], rejected: ["Rejeitada", "bad"], expired: ["Expirada", "mute"] },
  devupd: { pending: ["Pendente", "warn"], prompted: ["Notificado", "info"], deferred: ["Adiado", "mute"], downloading: ["A descarregar", "info"], installed: ["Instalado", "ok"], failed: ["Falhou", "bad"], forced: ["Forçado", "warn"] },
  apptype: { pos: ["POS", "info"], passenger: ["Passageiro", "info"] },
  release: { draft: ["Rascunho", "mute"], published: ["Publicada", "ok"], suspended: ["Suspensa", "warn"], retired: ["Retirada", "mute"] },
  srq: { "new": ["Novo", "warn"], contacted: ["Contactado", "info"], qualified: ["Qualificado", "ok"], closed: ["Fechado", "mute"] },
  interest: { operator: ["Operador", "mute"], company: ["Empresa", "mute"], school: ["Escola", "mute"], other: ["Outro", "mute"] },
  imp: { queued: ["Em fila", "mute"], processing: ["A processar", "info"], completed: ["Concluída", "ok"], partial: ["Parcial", "warn"], failed: ["Falhada", "bad"] },
  sysrole: { sim: ["Sistema", "info"], nao: ["Personalizado", "mute"] },
  ticket: { valid: ["Válido", "ok"], used: ["Usado", "mute"], expired: ["Expirado", "warn"], cancelled: ["Cancelado", "bad"], refunded: ["Reembolsado", "warn"] },
  dir: { outbound: ["Ida", "info"], inbound: ["Volta", "info"] },
  weekday: { sim: ["Opera", "ok"], nao: ["Não opera", "mute"] },
  bcast: { draft: ["Rascunho", "mute"], sending: ["A enviar", "info"], sent: ["Enviada", "ok"], failed: ["Falhou", "bad"] },
  cms: { draft: ["Rascunho", "mute"], review: ["Em revisão", "warn"], scheduled: ["Agendado", "info"], published: ["Publicado", "ok"] },
  cmssched: { scheduled: ["Agendada", "info"], done: ["Publicada", "ok"], failed: ["Falhou", "bad"], cancelled: ["Cancelada", "mute"] },
  cmstpl: { landing: ["Landing", "mute"], pricing: ["Preços", "mute"], contact: ["Contactos", "mute"], apps: ["Apps", "mute"], generic: ["Genérica", "mute"] },
  audit: { create: ["Criação", "ok"], update: ["Alteração", "info"], "delete": ["Eliminação", "bad"], login: ["Sessão", "mute"], action: ["Acção", "warn"] },
};

export type EnumGroupKey = string;

/**
 * Índice plano valor → (rótulo, tom), para quando o grupo não é conhecido.
 *
 * O tom vem junto de propósito: um `boarding` sem grupo continua a ser azul de
 * "em curso", e não cinzento de "sem estado" — que é o que acontecia quando só
 * se guardava o rótulo.
 */
export const ANY_ENUM_ENTRY: Record<string, EnumEntry> = {};
for (const group of Object.values(ENUM_LABELS)) {
  for (const [value, entry] of Object.entries(group)) {
    if (!ANY_ENUM_ENTRY[value]) ANY_ENUM_ENTRY[value] = entry as EnumEntry;
  }
}

/** Só o rótulo, para quem não precisa do tom. */
export const ANY_ENUM_LABEL: Record<string, string> = Object.fromEntries(
  Object.entries(ANY_ENUM_ENTRY).map(([value, entry]) => [value, entry[0]]),
);

/** Rótulo + tom de um valor de enum. Nunca lança. */
export function enumEntry(group: EnumGroupKey | null, value: string | null | undefined): EnumEntry {
  if (value === null || value === undefined || value === "") return ["—", "mute"];
  const table = group ? ENUM_LABELS[group] : null;
  const hit = table?.[value];
  if (hit) return hit as EnumEntry;
  const fallback = ANY_ENUM_ENTRY[value];
  return fallback ?? [value, "mute"];
}
