import { useNavigate } from "react-router-dom";
import { Menu } from "lucide-react";

import ThemeToggle from "../Theme/ThemeToggle";
import { useAuth } from "../../auth/AuthContext";
import { BRAND_NAME } from "../../constants/branding";

function Navbar({ onOpenMobileNav }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/", { replace: true });
  }

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-[var(--border)] bg-[var(--surface)] px-3 shadow-sm sm:px-4">
      <div className="flex min-w-0 items-center gap-2">
        <button
          type="button"
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-[var(--border)] bg-[var(--surface-elevated)] text-[var(--text-primary)] md:hidden"
          onClick={onOpenMobileNav}
          aria-label="Open navigation menu"
        >
          <Menu className="h-4 w-4" aria-hidden="true" />
        </button>
        <span className="inline-flex h-2 w-2 shrink-0 rounded-full bg-[var(--success)]" aria-hidden />
        <p
          className="truncate text-sm font-semibold text-[var(--text-primary)] sm:text-base"
          aria-label={`${BRAND_NAME} application`}
        >
          {BRAND_NAME}
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        {user && (
          <p className="hidden max-w-[10rem] truncate text-sm text-[var(--text-muted)] sm:block">
            {user.username}
            <span className="text-[var(--text-secondary)]"> · {user.role}</span>
          </p>
        )}
        <button
          type="button"
          className="ops-btn border border-[var(--border)] bg-[var(--surface-elevated)] px-2.5 text-sm text-[var(--text-primary)] sm:px-3"
          onClick={handleLogout}
        >
          Log out
        </button>
        <ThemeToggle />
      </div>
    </header>
  );
}

export default Navbar;
