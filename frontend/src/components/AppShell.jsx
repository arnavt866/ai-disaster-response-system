import { useState } from "react";
import { Outlet } from "react-router-dom";
import Navbar from "./Navbar/Navbar";
import Sidebar from "./Sidebar/Sidebar";

export default function AppShell({ sidebarCollapsed, onToggleSidebar }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="min-h-screen overflow-x-hidden bg-[var(--bg)] text-[var(--text-primary)] transition-colors duration-200">
      <Navbar onOpenMobileNav={() => setMobileNavOpen(true)} />
      <div className="flex">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={onToggleSidebar}
          mobileOpen={mobileNavOpen}
          onMobileClose={() => setMobileNavOpen(false)}
        />
        <main className="flex min-h-[calc(100vh-3.5rem)] min-w-0 flex-1 flex-col p-3 md:p-4">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
