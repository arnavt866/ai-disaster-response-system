import { useState } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"

import Navbar from "./components/Navbar/Navbar"
import Sidebar from "./components/Sidebar/Sidebar"

import Dashboard from "./components/Dashboard/Dashboard"
import Disasters from "./pages/Disaster"
import Zones from "./pages/Zones"
import Resources from "./pages/Resources"
import Operations from "./pages/Operations"
import AIDemand from "./pages/AIDemand"
import Reports from "./pages/Reports"
import Missions from "./pages/Missions"
import Teams from "./pages/Teams"

function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true)

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[var(--bg)] text-[var(--text-primary)] transition-colors duration-200">
        <Navbar />

        <div className="flex">
          <Sidebar
            collapsed={sidebarCollapsed}
            onToggle={() => setSidebarCollapsed((prev) => !prev)}
          />

          <main className="min-h-[calc(100vh-3.5rem)] flex-1 p-2.5">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/disasters" element={<Disasters />} />
              <Route path="/zones" element={<Zones />} />
              <Route path="/resources" element={<Resources />} />
              <Route path="/operations" element={<Operations />} />
              <Route path="/Operations" element={<Navigate to="/operations" replace />} />
              <Route path="/ai-demand" element={<AIDemand />} />
              <Route path="/AIdemand" element={<Navigate to="/ai-demand" replace />} />
              <Route path="/AIDemand" element={<Navigate to="/ai-demand" replace />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/Reports" element={<Navigate to="/reports" replace />} />
              <Route path="/missions" element={<Missions />} />
              <Route path="/teams" element={<Teams />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}

export default App
