import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { BRAND_NAME, PROJECT_TITLE } from "../constants/branding";

const MIN_PASSWORD_LENGTH = 6;

export default function Landing() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, loading, login, register } = useAuth();
  const [mode, setMode] = useState("signin");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const redirectTo = location.state?.from || "/dashboard";
  const isRegister = mode === "register";

  if (!loading && isAuthenticated) {
    return <Navigate to={redirectTo} replace />;
  }

  function switchMode(next) {
    setMode(next);
    setError("");
    setPassword("");
    setConfirmPassword("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    const trimmedUsername = username.trim();
    if (trimmedUsername.length < 3) {
      setError("Username must be at least 3 characters.");
      setSubmitting(false);
      return;
    }
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      setSubmitting(false);
      return;
    }
    if (isRegister && password !== confirmPassword) {
      setError("Passwords do not match.");
      setSubmitting(false);
      return;
    }

    try {
      if (isRegister) {
        await register(trimmedUsername, password);
      } else {
        await login(trimmedUsername, password);
      }
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err.message || (isRegister ? "Registration failed" : "Login failed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="landing-page dark flex min-h-screen flex-col items-center justify-center px-4 py-10 text-center sm:px-6">
      <div className="landing-bg" aria-hidden="true">
        <div className="landing-bg__image" />
      </div>
      <div className="landing-overlay" aria-hidden="true" />
      <div className="landing-content w-full max-w-xl space-y-6 sm:space-y-8">
        <div className="space-y-3 sm:space-y-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--accent)] sm:text-sm">
            {BRAND_NAME}
          </p>
          <h1 className="text-4xl font-bold leading-tight text-white sm:text-5xl">
            Disaster Response Operations
          </h1>
          <p className="mx-auto max-w-lg text-sm leading-relaxed text-slate-400 sm:text-base">
            {PROJECT_TITLE}
          </p>
          <p className="text-base text-slate-300 sm:text-lg">
            {isRegister
              ? "Create an account to access the command center."
              : "Sign in to access the command center."}
          </p>
        </div>

        <form
          className="mx-auto space-y-5 rounded-xl border border-white/15 bg-[#151b23]/75 p-6 text-left shadow-2xl backdrop-blur-md sm:space-y-6 sm:p-8"
          onSubmit={handleSubmit}
        >
          <div className="flex items-center justify-between gap-3 border-b border-white/10 pb-4">
            <h2 className="text-lg font-semibold text-white">
              {isRegister ? "Create account" : "Sign in"}
            </h2>
            <button
              type="button"
              className="text-sm font-medium text-[var(--accent)] hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
              onClick={() => switchMode(isRegister ? "signin" : "register")}
            >
              {isRegister ? "Already have an account? Sign in" : "Create account"}
            </button>
          </div>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-200">Username</span>
            <input
              className="ops-input w-full border-[var(--border)] bg-[#0b0f14]/80 px-3.5 py-2.5 text-base text-white"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              minLength={3}
              required
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-200">Password</span>
            <input
              type="password"
              className="ops-input w-full border-[var(--border)] bg-[#0b0f14]/80 px-3.5 py-2.5 text-base text-white"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={isRegister ? "new-password" : "current-password"}
              minLength={MIN_PASSWORD_LENGTH}
              required
            />
            {isRegister && (
              <span className="mt-1.5 block text-xs text-slate-400">
                At least {MIN_PASSWORD_LENGTH} characters
              </span>
            )}
          </label>

          {isRegister && (
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-200">
                Confirm password
              </span>
              <input
                type="password"
                className="ops-input w-full border-[var(--border)] bg-[#0b0f14]/80 px-3.5 py-2.5 text-base text-white"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
                minLength={MIN_PASSWORD_LENGTH}
                required
              />
            </label>
          )}

          {error && (
            <p
              className="rounded-md border border-[var(--severity-critical)]/40 bg-[var(--tint-critical)] px-3 py-2 text-sm text-[var(--severity-critical-text)]"
              role="alert"
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            className="inline-flex w-full items-center justify-center rounded-md bg-[var(--accent)] px-6 py-3 text-base font-semibold text-[#04231f] shadow-lg transition-opacity hover:opacity-90 disabled:opacity-60"
            disabled={submitting}
          >
            {submitting
              ? isRegister
                ? "Creating account..."
                : "Signing in..."
              : isRegister
                ? "Create account"
                : "Sign in to Command Center"}
          </button>
        </form>
      </div>
    </div>
  );
}
