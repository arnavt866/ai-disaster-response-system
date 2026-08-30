import { useState } from "react"
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
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react"
import { NavLink } from "react-router-dom"

const NAV_ITEMS = [
  { to: "/", end: true, icon: LayoutDashboard, label: "Dashboard" },
  { to: "/disasters", icon: TriangleAlert, label: "Disasters" },
  { to: "/zones", icon: MapPinned, label: "Zones" },
  { to: "/resources", icon: Package, label: "Resources" },
  { to: "/ai-demand", icon: Brain, label: "AI Demand" },
  { to: "/missions", icon: Activity, label: "Missions" },
  { to: "/teams", icon: Users, label: "Teams" },
  { to: "/operations", icon: Truck, label: "Allocation" },
  { to: "/reports", icon: BarChart3, label: "Reports" },
]

function Sidebar({ collapsed, onToggle }) {
  const [hovering, setHovering] = useState(false)
  const effectivelyCollapsed = collapsed && !hovering

  const navItemClass = ({ isActive }) =>
    `flex w-full items-center rounded-md text-sm font-medium transition-colors ${
      effectivelyCollapsed ? "justify-center px-2 py-2.5" : "gap-2.5 px-3 py-2.5"
    } ${
      isActive
        ? "bg-[var(--primary)] text-white"
        : "text-slate-300 hover:bg-slate-800 hover:text-white"
    }`

  return (
    <aside
      onMouseEnter={() => collapsed && setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      className={`relative flex min-h-[calc(100vh-3.5rem)] shrink-0 flex-col border-r border-slate-800 bg-slate-900 text-white transition-all duration-200 ${
        effectivelyCollapsed ? "w-14" : "w-56"
      } ${collapsed && hovering ? "z-30 shadow-xl" : ""}`}
    >
      <div className={`border-b border-slate-700 ${effectivelyCollapsed ? "px-2 py-3" : "px-4 py-4"}`}>
        {!effectivelyCollapsed && (
          <>
            <h2 className="text-lg font-bold leading-tight">Disaster AI</h2>
            <p className="mt-0.5 text-sm text-slate-400">Response Management</p>
          </>
        )}
        <button
          type="button"
          onClick={() => {
            setHovering(false)
            onToggle()
          }}
          className={`mt-2 flex items-center rounded-md border border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white ${
            effectivelyCollapsed ? "mx-auto p-2" : "gap-2 px-2 py-1.5 text-sm"
          }`}
          title={collapsed ? "Pin sidebar open" : "Collapse sidebar"}
        >
          {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
          {!effectivelyCollapsed && <span>{collapsed ? "Pin open" : "Collapse"}</span>}
        </button>
      </div>

      <nav className="flex-1 px-2 py-3">
        {!effectivelyCollapsed && (
          <p className="mb-2 px-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
            Main Menu
          </p>
        )}

        <div className="space-y-1">
          {NAV_ITEMS.map(({ to, end, icon: Icon, label }) => (
            <NavLink key={to} to={to} end={end} className={navItemClass} title={effectivelyCollapsed ? label : undefined}>
              <Icon className="h-4 w-4 shrink-0" />
              {!effectivelyCollapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </div>
      </nav>
    </aside>
  )
}

export default Sidebar
