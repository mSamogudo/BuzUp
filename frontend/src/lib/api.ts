const API_BASE = "";

interface TokenPair {
  access: string;
  refresh: string;
}

let redirectingToLogin = false;
function handleUnauthorized() {
  if (redirectingToLogin) return;
  try {
    localStorage.removeItem("buzup_token");
    localStorage.removeItem("buzup_refresh");
  } catch {}
  const path = window.location.pathname;
  if (path !== "/login" && !path.startsWith("/checkout") && !path.startsWith("/bus/")) {
    redirectingToLogin = true;
    window.location.replace("/login");
  }
}

export interface TwoFactorChallenge {
  two_factor: true;
  challenge_id: string;
  phone_hint: string;
  expires_in: number;
}

/** Primeiro passo do login. Com verificação em dois passos activa, devolve um
 *  desafio em vez de tokens — a senha sozinha não abre o portal. */
export async function apiLogin(
  username: string, password: string,
): Promise<TokenPair | TwoFactorChallenge> {
  const res = await fetch(`${API_BASE}/api/auth/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Credenciais invalidas.");
  return data;
}

export function isTwoFactor(r: TokenPair | TwoFactorChallenge): r is TwoFactorChallenge {
  return (r as TwoFactorChallenge).two_factor === true;
}

/** Segundo passo: o código do SMS troca-se pelos tokens. */
export async function apiTwoFactorVerify(
  challenge_id: string, code: string,
): Promise<TokenPair> {
  const res = await fetch(`${API_BASE}/api/auth/2fa/verify/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ challenge_id, code }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Codigo invalido.");
  return data;
}

export async function apiRefreshToken(refresh: string): Promise<TokenPair> {
  const res = await fetch(`${API_BASE}/api/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) throw new Error("Sessao expirada.");
  return res.json();
}

export async function apiFetch(path: string, token: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options?.headers,
    },
  });
  if (res.status === 401) {
    handleUnauthorized();
    return new Promise(() => {});
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(extractApiError(data, res.status));
  }
  if (res.status === 204) return null;
  return res.json();
}

function extractApiError(data: unknown, status: number): string {
  if (!data || typeof data !== "object") return `Erro ${status}`;
  const obj = data as Record<string, unknown>;
  if (typeof obj.detail === "string") return obj.detail;
  const nfe = obj.non_field_errors;
  if (Array.isArray(nfe) && nfe.length) return String(nfe[0]);
  if (typeof nfe === "string") return nfe;
  for (const value of Object.values(obj)) {
    if (Array.isArray(value) && value.length && typeof value[0] === "string") return value[0];
    if (typeof value === "string") return value;
  }
  return `Erro ${status}`;
}

export async function apiRequest(path: string, token: string, options?: RequestInit) {
  return apiFetch(path, token, options);
}

export async function apiPost(path: string, token: string, body: unknown) {
  return apiFetch(path, token, { method: "POST", body: JSON.stringify(body) });
}

export async function apiPatch(path: string, token: string, body: unknown) {
  return apiFetch(path, token, { method: "PATCH", body: JSON.stringify(body) });
}

/// Multipart upload (e.g. APK release). Lets the browser set the multipart
/// boundary — we must NOT force a JSON Content-Type here.
export async function apiUpload(path: string, token: string, form: FormData, method: "POST" | "PATCH" = "POST") {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    body: form,
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 401) {
    handleUnauthorized();
    return new Promise(() => {});
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(extractApiError(data, res.status));
  }
  if (res.status === 204) return null;
  return res.json();
}

export async function apiDelete(path: string, token: string) {
  return apiFetch(path, token, { method: "DELETE" });
}

export async function apiOtpRequest(phone: string): Promise<{ challenge_id: string; expires_in: number; phone: string }> {
  const res = await fetch(`${API_BASE}/api/auth/otp/request/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Erro ao enviar SMS.");
  }
  return res.json();
}

export async function apiOtpVerify(
  phone: string, challenge_id: string, code: string, full_name?: string
): Promise<{ access: string; refresh: string; passenger_id?: number; driver_id?: number; agent_id?: number; is_new: boolean }> {
  const res = await fetch(`${API_BASE}/api/auth/otp/verify/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone, challenge_id, code, full_name }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Codigo invalido.");
  }
  return res.json();
}

export async function apiPublic(path: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(extractApiError(data, res.status));
  }
  if (res.status === 204) return null;
  return res.json();
}


/** Descarrega um ficheiro protegido sem pôr credenciais no URL.
 *
 * O caminho antigo era `<a href="...?token=<JWT>">`, porque um link não envia
 * o cabeçalho `Authorization`. Só que o URL fica gravado no log de acessos e
 * no histórico do browser — e o que lá ficava era o token de acesso completo,
 * que dá acesso a tudo o que o utilizador pode fazer. Pedir com `fetch` e
 * entregar o resultado como blob mantém a credencial no cabeçalho.
 */
export async function apiDownload(path: string, token: string, filename: string) {
  const res = await fetch(path, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) {
    throw new Error(`Falha ao descarregar (${res.status}).`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Igual, mas devolve um URL de objecto para mostrar num `<img>`.
 *
 * Quem chamar tem de revogar o URL quando deixar de precisar dele, senão o
 * blob fica preso em memória enquanto a página estiver aberta.
 */
export async function apiBlobUrl(path: string, token: string): Promise<string> {
  const res = await fetch(path, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) {
    throw new Error(`Falha ao carregar imagem (${res.status}).`);
  }
  return URL.createObjectURL(await res.blob());
}
