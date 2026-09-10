import { clearAuthSession, getStoredToken } from "../auth/session";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function apiRequest(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (!options.skipAuth) {
    const token = getStoredToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    ...options,
    headers,
  });

  if (response.status === 401 && !options.skipAuth) {
    clearAuthSession();
    if (window.location.pathname !== "/") {
      window.location.assign("/");
    }
  }

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      const text = await response.text();
      if (text) message = text;
    }
    const error = new Error(
      typeof message === "string" ? message : JSON.stringify(message),
    );
    // Callers need the status to tell "not authorised" from "server/network hiccup".
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export { API_BASE_URL };
