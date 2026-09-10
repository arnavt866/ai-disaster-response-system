import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { getCurrentUser, login as loginRequest, logout as logoutRequest, register as registerRequest } from "../api/auth";
import { clearAuthSession, getStoredToken, getStoredUser, storeAuthSession } from "./session";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => getStoredToken());
  const [user, setUser] = useState(() => getStoredUser());
  const [loading, setLoading] = useState(Boolean(getStoredToken()));

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return undefined;
    }

    let cancelled = false;
    setLoading(true);
    getCurrentUser()
      .then((profile) => {
        if (!cancelled) {
          setUser(profile);
        }
      })
      .catch((error) => {
        if (cancelled) return;
        // Only a real auth rejection ends the session. A network blip or a 5xx
        // must not silently sign the commander out mid-operation.
        if (error?.status === 401 || error?.status === 403) {
          clearAuthSession();
          setToken(null);
          setUser(null);
          return;
        }
        setUser((current) => current ?? getStoredUser());
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  const value = useMemo(
    () => ({
      token,
      user,
      loading,
      isAuthenticated: Boolean(token && user),
      async login(username, password) {
        const session = await loginRequest(username, password);
        storeAuthSession(session);
        setToken(session.access_token);
        setUser({ username: session.username, role: session.role });
        return session;
      },
      async register(username, password) {
        const session = await registerRequest(username, password);
        storeAuthSession(session);
        setToken(session.access_token);
        setUser({ username: session.username, role: session.role });
        return session;
      },
      async logout() {
        try {
          if (getStoredToken()) {
            await logoutRequest();
          }
        } catch {
          // Client-side logout still clears local session.
        } finally {
          clearAuthSession();
          setToken(null);
          setUser(null);
        }
      },
    }),
    [token, user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
