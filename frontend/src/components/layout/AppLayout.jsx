import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'

/**
 * Main application shell.
 * Renders a fixed sidebar on the left, a top header, and a scrollable main area.
 * Child routes are rendered via <Outlet />.
 */
export default function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <Sidebar />

      {/* ── Content area ─────────────────────────────────────────────────── */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header />

        <main className="flex-1 overflow-y-auto px-6 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
