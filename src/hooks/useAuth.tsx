import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, refreshSession, setSessionLostHandler } from "@/api/client";
import { tokens } from "@/api/tokens";
import type { Role, TokenPair, User } from "@/api/types";

interface AuthState {
  user: User | null;
  /** True until the first attempt to restore a saved session has finished. */
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  can: (...roles: Role[]) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const clearSession = useCallback(() => {
    tokens.clear();
    client.clear();
    setUser(null);
  }, [client]);

  useEffect(() => {
    setSessionLostHandler(clearSession);
    return () => setSessionLostHandler(null);
  }, [clearSession]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        if (await refreshSession()) {
          const me = await api<User>("/auth/me");
          if (!cancelled) setUser(me);
        }
      } catch {
        /* an unreachable server or expired session just shows the sign-in page */
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const pair = await api<TokenPair>("/auth/login", { method: "POST", body: { email, password }, auth: false });
    tokens.set(pair.accessToken, pair.refreshToken);
    setUser(await api<User>("/auth/me"));
  }, []);

  const signOut = useCallback(async () => {
    const refresh = tokens.refresh;
    try {
      if (refresh) await api<void>("/auth/logout", { method: "POST", body: { refreshToken: refresh }, auth: false });
    } catch {
      /* signing out locally is enough if the server cannot be reached */
    }
    clearSession();
  }, [clearSession]);

  const value = useMemo<AuthState>(
    () => ({ user, loading, signIn, signOut, can: (...roles) => user !== null && roles.includes(user.role) }),
    [user, loading, signIn, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
