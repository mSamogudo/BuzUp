import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

function parseJwtPayload(token: string): Record<string, unknown> {
  try {
    const base64 = token.split(".")[1];
    return JSON.parse(atob(base64));
  } catch { return {}; }
}

function intOrNull(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

interface AuthState {
  token: string | null;
  refresh: string | null;
  passengerId: number | null;
  driverId: number | null;
  agentId: number | null;
  login: (access: string, refresh: string, manter?: boolean) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  token: null,
  refresh: null,
  passengerId: null,
  driverId: null,
  agentId: null,
  login: () => {},
  logout: () => {},
});

/* Onde a sessao fica guardada.
 *
 * "Manter sessão iniciada" e uma escolha real e nao um visto decorativo: com
 * ela, o token vai para `localStorage` e sobrevive a fechar o browser — e o
 * que se quer no computador da direccao. Sem ela vai para `sessionStorage` e
 * morre com o separador, que e o que tem de acontecer num terminal partilhado
 * do balcao, onde o turno seguinte nao pode herdar a sessao do anterior.
 *
 * Ler procura nos dois: quem ja tinha sessao antes desta opcao existir tinha-a
 * em `localStorage` e nao pode ser posto fora por causa disto.
 */
const CHAVES = ["buzup_token", "buzup_refresh"] as const;

function leSessao(chave: string): string | null {
  try {
    return localStorage.getItem(chave) ?? sessionStorage.getItem(chave);
  } catch {
    return null;
  }
}

function guardarSessao(chave: string, valor: string, manter: boolean) {
  try {
    (manter ? localStorage : sessionStorage).setItem(chave, valor);
    // Nunca deixar a chave nos dois sitios: senao "não manter" deixava rasto.
    (manter ? sessionStorage : localStorage).removeItem(chave);
  } catch {
    /* armazenamento bloqueado: a sessao vive so em memoria nesta aba */
  }
}

function limparSessao() {
  for (const chave of CHAVES) {
    try {
      localStorage.removeItem(chave);
      sessionStorage.removeItem(chave);
    } catch {
      /* nada a fazer */
    }
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const initialPayload = (() => {
    const stored = leSessao("buzup_token");
    return stored ? parseJwtPayload(stored) : {};
  })();

  const [token, setToken] = useState<string | null>(() => leSessao("buzup_token"));
  const [refresh, setRefresh] = useState<string | null>(() => leSessao("buzup_refresh"));
  const [passengerId, setPassengerId] = useState<number | null>(() => intOrNull(initialPayload.passenger_id));
  const [driverId, setDriverId] = useState<number | null>(() => intOrNull(initialPayload.driver_id));
  const [agentId, setAgentId] = useState<number | null>(() => intOrNull(initialPayload.agent_id));

  const login = useCallback((access: string, refreshToken: string, manter = true) => {
    guardarSessao("buzup_token", access, manter);
    guardarSessao("buzup_refresh", refreshToken, manter);
    setToken(access);
    setRefresh(refreshToken);
    const payload = parseJwtPayload(access);
    setPassengerId(intOrNull(payload.passenger_id));
    setDriverId(intOrNull(payload.driver_id));
    setAgentId(intOrNull(payload.agent_id));
  }, []);

  const logout = useCallback(() => {
    limparSessao();
    setToken(null);
    setRefresh(null);
    setPassengerId(null);
    setDriverId(null);
    setAgentId(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, refresh, passengerId, driverId, agentId, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
