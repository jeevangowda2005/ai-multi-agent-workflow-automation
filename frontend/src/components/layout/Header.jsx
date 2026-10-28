import { useLocation } from 'react-router-dom'
import { BellIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import useHealthCheck from '@/hooks/useHealthCheck'

/** Map route paths to human-readable page titles */
const PAGE_TITLES = {
  '/dashboard':   'Dashboard',
  '/workflows':   'Workflows',
  '/ai-analyzer': 'AI Task Analyzer',
  '/agents':      'AI Task Analyzer',
  '/executions':  'Executions',
  '/settings':    'Settings',
}

/**
 * Top header bar showing:
 * - Current page title (derived from route)
 * - Search input
 * - Backend health indicator
 * - Notification bell
 */
export default function Header() {
  const { pathname } = useLocation()
  let pageTitle = PAGE_TITLES[pathname]
  if (!pageTitle && pathname.startsWith('/workflows/')) {
    pageTitle = 'Workflow Details'
  }
  pageTitle = pageTitle ?? 'AI Workflow Platform'
  const { healthy, loading } = useHealthCheck()

  return (
    <header className="flex items-center justify-between px-6 py-4 bg-surface-card border-b border-surface-border shrink-0">
      {/* ── Page title ───────────────────────────────────────────────────── */}
      <h1 className="text-lg font-semibold text-white">{pageTitle}</h1>

      {/* ── Right controls ───────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        {/* Search */}
        <div className="relative hidden sm:block">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
          <input
            type="search"
            placeholder="Search…"
            className="pl-9 pr-4 py-1.5 text-sm bg-surface border border-surface-border rounded-lg
                       text-slate-300 placeholder-slate-500
                       focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500/50
                       transition w-48"
          />
        </div>

        {/* Backend health badge */}
        <div
          title={loading ? 'Checking backend…' : healthy ? 'Backend healthy' : 'Backend unreachable'}
          className={`badge ${loading ? 'status-idle' : healthy ? 'status-healthy' : 'status-error'}`}
        >
          <span
            className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 ${
              loading ? 'bg-slate-400' : healthy ? 'bg-emerald-400' : 'bg-red-400'
            }`}
          />
          {loading ? 'Connecting…' : healthy ? 'API Online' : 'API Offline'}
        </div>

        {/* Notifications */}
        <button
          aria-label="Notifications"
          className="p-2 rounded-lg text-slate-400 hover:bg-surface-border hover:text-white transition-colors"
        >
          <BellIcon className="w-5 h-5" />
        </button>
      </div>
    </header>
  )
}
