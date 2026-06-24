import { createContext, useContext, useState, useCallback, useMemo, type ReactNode } from "react";

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
  login: (access: string, refresh: string) => void;
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

export function AuthProvider({ children }: { children: ReactNode }) {
  const initialPayload = (() => {
    const stored = localStorage.getItem("buzup_token");
    return stored ? parseJwtPayload(stored) : {};
  })();

  const [token, setToken] = useState<string | null>(() => localStorage.getItem("buzup_token"));
  const [refresh, setRefresh] = useState<string | null>(() => localStorage.getItem("buzup_refresh"));
  const [passengerId, setPassengerId] = useState<number | null>(() => intOrNull(initialPayload.passenger_id));
  const [driverId, setDriverId] = useState<number | null>(() => intOrNull(initialPayload.driver_id));
  const [agentId, setAgentId] = useState<number | null>(() => intOrNull(initialPayload.agent_id));

  const login = useCallback((access: string, refreshToken: string) => {
    localStorage.setItem("buzup_token", access);
    localStorage.setItem("buzup_refresh", refreshToken);
    setToken(access);
    setRefresh(refreshToken);
    const payload = parseJwtPayload(access);
    setPassengerId(intOrNull(payload.passenger_id));
    setDriverId(intOrNull(payload.driver_id));
    setAgentId(intOrNull(payload.agent_id));
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("buzup_token");
    localStorage.removeItem("buzup_refresh");
    setToken(null);
    setRefresh(null);
    setPassengerId(null);
    setDriverId(null);
    setAgentId(null);
  }, []);

  // Stable value reference: consumers only re-render when auth state actually
  // changes, not on every parent render. login/logout are already useCallback.
  const value = useMemo(
    () => ({ token, refresh, passengerId, driverId, agentId, login, logout }),
    [token, refresh, passengerId, driverId, agentId, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
