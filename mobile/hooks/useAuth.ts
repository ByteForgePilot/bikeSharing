import { useState, useCallback } from "react";
import * as api from "../services/api";

interface User {
  id: number;
  username: string;
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const login = useCallback(async (username: string, password: string) => {
    setLoading(true);
    try {
      const result = await api.login(username, password);
      setToken(result.access_token);
      // Fetch user info
      const userData = await api.request<{ id: number; username: string }>(
        "/api/auth/me",
        { token: result.access_token }
      );
      setUser(userData);
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (username: string, password: string) => {
    setLoading(true);
    try {
      await api.register(username, password);
      await login(username, password);
    } finally {
      setLoading(false);
    }
  }, [login]);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
  }, []);

  return { user, token, loading, login, register, logout };
}
