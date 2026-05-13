import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import * as api from "../services/api";
import { isBackendReachable } from "../services/offlineStorage";

interface User {
  id: number;
  username: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  online: boolean; // true = backend reachable, false = offline mode
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

function generateDeviceId(): string {
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  let result = "rider_";
  for (let i = 0; i < 6; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [online, setOnline] = useState(false);

  const login = useCallback(async (username: string, password: string) => {
    const result = await api.login(username, password);
    setToken(result.access_token);
    const userData = await api.request<User>("/api/auth/me", {
      token: result.access_token,
    });
    setUser(userData);
  }, []);

  const register = useCallback(
    async (username: string, password: string) => {
      await api.register(username, password);
      await login(username, password);
    },
    [login]
  );

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
  }, []);

  useEffect(() => {
    async function init() {
      const reachable = await isBackendReachable();
      setOnline(reachable);

      if (reachable) {
        try {
          const username = generateDeviceId();
          const password = "bike1234";
          await register(username, password);
        } catch {
          try {
            const username = generateDeviceId() + Date.now().toString(36);
            const password = "bike1234";
            await register(username, password);
          } catch {
            // auth failed — fall through to offline
          }
        }
      }
      setLoading(false);
    }
    init();
  }, [register]);

  return (
    <AuthContext.Provider value={{ user, token, loading, online, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext must be used within AuthProvider");
  return ctx;
}
