import { useState } from "react";
import {
  LayoutDashboard,
  TriangleAlert,
  MapPinned,
  Package,
  Brain,
  Truck,
  BarChart3,
  Activity,
  Users,
  Satellite as SatelliteIcon,
  PanelLeftClose,
  PanelLeftOpen,
  X,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { BRAND_NAME, BRAND_TAGLINE } from "../../constants/branding";

const NAV_ITEMS = [
  { to: "/dashboard", end: true, icon: LayoutDashboard, label: "Dashboard" },
  { to: "/disasters", icon: TriangleAlert, label: "Disasters" },
  { to: "/satellite", icon: SatelliteIcon, label: "Satellite" },
  { to: "/zones", icon: MapPinned, label: "Zones" },
  { to: "/resources", icon: Package, label: "Resources" },
  { to: "/ai-demand", icon: Brain, label: "AI Demand" },
  { to: "/missions", icon: Activity, label: "Missions" },
  { to: "/teams", icon: Users, label: "Teams" },
  { to: "/operations", icon: Truck, label: "Allocation" },
  { to: "/reports", icon: BarChart3, label: "Reports" },
];

function SidebarNav({ effectivelyCollapsed, navItemClass, onNavigate }) {
  return (
    <>
      {!effectivelyCollapsed && (
        <p className="mb-2 px-2 text-[0.6875rem] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
          Main Menu
        </p>
      )}

      <div className="space-y-1">
        {NAV_ITEMS.map(({ to, end, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={navItemClass}
            title={effectivelyCollapsed ? label : undefined}
            aria-label={effectivelyCollapsed ? label : undefined}
            onClick={onNavigate}
          >
            <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
            {!effectivelyCollapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </div>
    </>
  );
}

function Sidebar({ collapsed, onToggle, mobileOpen = false, onMobileClose }) {
  const [hovering, setHovering] = useState(false);
  const effectivelyCollapsed = collapsed && !hovering;

  const navItemClass = ({ isActive }) =>
    `flex w-full items-center rounded-md text-sm font-medium transition-colors ${
      effectivelyCollapsed ? "justify-center px-2 py-2.5" : "gap-2.5 px-3 py-2.5"
    } ${
      isActive
        ? "bg-[var(--accent)] text-[#04231f]"
        : "text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]"
    }`;

  const mobileNavItemClass = ({ isActive }) =>
    `flex w-full items-center gap-2.5 rounded-md px-3 py-2.5 text-sm font-medium transition-colors ${
      isActive
        ? "bg-[var(--accent)] text-[#04231f]"
        : "text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]"
    }`;

  return (
    <>
      {/* Desktop / tablet sidebar */}
      <aside
        onMouseEnter={() => collapsed && setHovering(true)}
        onMouseLeave={() => setHovering(false)}
        className={`relative hidden min-h-[calc(100vh-3.5rem)] shrink-0 flex-col border-r border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] transition-all duration-200 md:flex ${
          effectivelyCollapsed ? "w-14" : "w-60"
        } ${collapsed && hovering ? "z-30 shadow-xl" : ""}`}
      >
        <div className={`min-w-0 border-b border-[var(--border)] ${effectivelyCollapsed ? "px-2 py-2.5" : "px-3 py-3"}`}>
          {!effectivelyCollapsed && (
            <div className="min-w-0 pr-1">
              <h2 className="text-sm font-bold leading-snug break-words">{BRAND_NAME}</h2>
              <p className="mt-0.5 text-[0.6875rem] leading-snug break-words text-[var(--text-secondary)]">
                {BRAND_TAGLINE}
              </p>
            </div>
          )}
          <button
            type="button"
            onClick={() => {
              setHovering(false);
              onToggle();
            }}
            className={`mt-2 flex items-center rounded-md border border-[var(--border)] text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)] ${
              effectivelyCollapsed ? "mx-auto p-2" : "gap-2 px-2 py-1.5 text-sm"
            }`}
            title={collapsed ? "Pin sidebar open" : "Collapse sidebar"}
            aria-label={collapsed ? "Pin sidebar open" : "Collapse sidebar"}
          >
            {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
            {!effectivelyCollapsed && <span>{collapsed ? "Pin open" : "Collapse"}</span>}
          </button>
        </div>

        <nav className="flex-1 px-2 py-3" aria-label="Main menu">
          <SidebarNav effectivelyCollapsed={effectivelyCollapsed} navItemClass={navItemClass} />
        </nav>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          aria-label="Dismiss navigation menu backdrop"
          onClick={onMobileClose}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 max-w-[85vw] flex-col border-r border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] transition-transform duration-200 md:hidden ${
          mobileOpen ? "translate-x-0" : "-translate-x-full pointer-events-none"
        }`}
        aria-hidden={!mobileOpen}
      >
        <div className="flex min-w-0 items-start justify-between gap-2 border-b border-[var(--border)] px-4 py-4">
          <div className="min-w-0 flex-1">
            <h2 className="text-sm font-bold leading-snug break-words">{BRAND_NAME}</h2>
            <p className="mt-0.5 text-[0.6875rem] leading-snug break-words text-[var(--text-secondary)]">
              {BRAND_TAGLINE}
            </p>
          </div>
          <button
            type="button"
            className="rounded-md border border-[var(--border)] p-2 text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]"
            onClick={onMobileClose}
            aria-label="Close navigation menu"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-3" aria-label="Main menu">
          <SidebarNav
            effectivelyCollapsed={false}
            navItemClass={mobileNavItemClass}
            onNavigate={onMobileClose}
          />
        </nav>
      </aside>
    </>
  );
}

export default Sidebar;
