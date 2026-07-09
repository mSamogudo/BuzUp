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

export async function apiLogin(username: string, password: string): Promise<TokenPair> {
  const res = await fetch(`${API_BASE}/api/auth/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Credenciais invalidas.");
  }
  return res.json();
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

export interface ContactLeadPayload {
  source: "contact" | "waitlist";
  email: string;
  name?: string;
  organization?: string;
  phone?: string;
  profile?: string;
  message?: string;
  locale?: string;
  /** Honeypot — must stay empty. Bots fill it; real users never see it. */
  website?: string;
}

export async function submitContactLead(payload: ContactLeadPayload) {
  return apiPublic("/api/public/contact/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
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
