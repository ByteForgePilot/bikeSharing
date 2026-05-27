import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from "react";
import * as api from "../services/api";
import { isBackendReachable } from "../services/offlineStorage";
import * as SecureStore from "expo-secure-store";
import NetInfo from "@react-native-community/netinfo";
import { syncPendingRides as doSync } from "../services/syncService";

interface User {
  id: number;
  username: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  online: boolean;
  isSyncing: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
  syncPendingRides: () => Promise<{ uploaded: number; failed: number }>;
}

const AuthContext = createContext<AuthState | null>(null);

const TOKEN_KEY = "auth_token";

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
  const [isSyncing, setIsSyncing] = useState(false);
  const wasOffline = useRef(false);

  const login = useCallback(async (username: string, password: string) => {
    const result = await api.login(username, password);
    setToken(result.access_token);
    await SecureStore.setItemAsync(TOKEN_KEY, result.access_token);
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

  const logout = useCallback(async () => {
    setUser(null);
    setToken(null);
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  }, []);

  const syncPendingRides = useCallback(async (): Promise<{ uploaded: number; failed: number }> => {
    if (isSyncing || !token) return { uploaded: 0, failed: 0 };
    setIsSyncing(true);
    try {
      return await doSync(token);
    } finally {
      setIsSyncing(false);
    }
  }, [token, isSyncing]);

  // Init: restore token + auto-register if needed
  useEffect(() => {
    async function init() {
      const reachable = await isBackendReachable();
      setOnline(reachable);
      wasOffline.current = !reachable;

      if (reachable) {
        // Try restore existing token
        const savedToken = await SecureStore.getItemAsync(TOKEN_KEY);
        if (savedToken) {
          try {
            const userData = await api.request<User>("/api/auth/me", { token: savedToken });
            setToken(savedToken);
            setUser(userData);
            setLoading(false);
            return; // Token valid, done
          } catch {
            // Token expired — remove and fall through to re-register
            await SecureStore.deleteItemAsync(TOKEN_KEY);
          }
        }

        // Auto-register new device account
        try {
          const username = generateDeviceId();
          await register(username, "bike1234");
        } catch {
          try {
            const username = generateDeviceId() + Date.now().toString(36);
            await register(username, "bike1234");
          } catch {
            // auth failed — fall through to offline
          }
        }
      }
      setLoading(false);
    }
    init();
  }, [register]);

  // NetInfo listener for real-time connectivity
  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((state) => {
      const isConnected = !!(state.isConnected && state.isInternetReachable !== false);

      if (isConnected && !online) {
        // Debounce: wait 2s then verify backend
        const timer = setTimeout(async () => {
          const reachable = await isBackendReachable();
          if (reachable) {
            setOnline(true);
            // Trigger sync if we were previously offline
            if (wasOffline.current) {
              wasOffline.current = false;
              syncPendingRides();
            }
          }
        }, 2000);
        return () => clearTimeout(timer);
      } else if (!isConnected && online) {
        setOnline(false);
        wasOffline.current = true;
      }
    });

    return unsubscribe;
  }, [online, syncPendingRides]);

  return (
    <AuthContext.Provider value={{ user, token, loading, online, isSyncing, login, register, logout, syncPendingRides }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext must be used within AuthProvider");
  return ctx;
}
