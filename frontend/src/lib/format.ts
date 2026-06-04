export function formatDateTime(value: string | null | undefined) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("pt-MZ", { dateStyle: "short", timeStyle: "short" });
}

export function formatDate(value: string | null | undefined) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleDateString("pt-MZ");
}

export function formatCurrency(value: string | number | null | undefined, currency = "MZN") {
  if (value === null || value === undefined) return "-";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (Number.isNaN(num)) return "-";
  return `${num.toLocaleString("pt-MZ", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
}

export function formatCount(value: number | null | undefined) {
  if (value === null || value === undefined) return "0";
  return value.toLocaleString("pt-MZ");
}

export function getInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

const STATUS_LABELS: Record<string, string> = {
  active: "Activo", inactive: "Inactivo", blocked: "Bloqueado", suspended: "Suspenso",
  closed: "Encerrado", stock: "Em Stock", lost: "Perdido", replaced: "Substituido", retired: "Retirado",
  confirmed: "Confirmado", pending: "Pendente", failed: "Falhado", expired: "Expirado",
  created: "Criado", reversed: "Revertido", cancelled: "Cancelado", refunded: "Reembolsado",
  draft: "Rascunho", published: "Publicado", payment_pending: "Pag. Pendente", issued: "Emitido",
  paid: "Pago", used: "Usado", approved: "Aprovado", denied: "Negado",
  scheduled: "Agendada", boarding: "Em Circulacao", departed: "Em Viagem", paused: "Em Repouso", completed: "Concluida",
  self_onboarded: "Self-Onboarded", pending_activation: "Pend. Activacao",
  pending_configuration: "Pend. Configuracao", rejected: "Rejeitado",
  prompted: "Notificado", deferred: "Adiado", downloading: "A Descarregar",
  installed: "Instalado", forced: "Forcado", maintenance: "Manutencao",
};

export function humanizeStatus(value: string) {
  return STATUS_LABELS[value] || value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
