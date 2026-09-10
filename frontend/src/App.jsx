import { useState } from "react"

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"



import { AuthProvider } from "./auth/AuthContext"

import RequireAuth from "./auth/RequireAuth"

import AppShell from "./components/AppShell"

import Landing from "./pages/Landing"

import Dashboard from "./components/Dashboard/Dashboard"

import Disasters from "./pages/Disaster"

import Zones from "./pages/Zones"

import Resources from "./pages/Resources"

import Operations from "./pages/Operations"

import AIDemand from "./pages/AIDemand"

import Reports from "./pages/Reports"

import SituationReport from "./pages/SituationReport"

import Missions from "./pages/Missions"

import Teams from "./pages/Teams"

import Satellite from "./pages/Satellite"



function App() {

  const [sidebarCollapsed, setSidebarCollapsed] = useState(true)



  return (

    <AuthProvider>

      <BrowserRouter>

        <Routes>

          <Route path="/" element={<Landing />} />

          <Route

            element={(

              <RequireAuth>

                <AppShell

                  sidebarCollapsed={sidebarCollapsed}

                  onToggleSidebar={() => setSidebarCollapsed((prev) => !prev)}

                />

              </RequireAuth>

            )}

          >

            <Route path="/dashboard" element={<Dashboard />} />

            <Route path="/disasters" element={<Disasters />} />

            <Route path="/zones" element={<Zones />} />

            <Route path="/resources" element={<Resources />} />

            <Route path="/operations" element={<Operations />} />

            <Route path="/Operations" element={<Navigate to="/operations" replace />} />

            <Route path="/ai-demand" element={<AIDemand />} />

            <Route path="/AIdemand" element={<Navigate to="/ai-demand" replace />} />

            <Route path="/AIDemand" element={<Navigate to="/ai-demand" replace />} />

            <Route path="/reports" element={<Reports />} />

            <Route path="/reports/disaster/:disasterId" element={<SituationReport />} />

            <Route path="/Reports" element={<Navigate to="/reports" replace />} />

            <Route path="/missions" element={<Missions />} />

            <Route path="/teams" element={<Teams />} />

            <Route path="/satellite" element={<Satellite />} />

          </Route>

        </Routes>

      </BrowserRouter>

    </AuthProvider>

  )

}



export default App

