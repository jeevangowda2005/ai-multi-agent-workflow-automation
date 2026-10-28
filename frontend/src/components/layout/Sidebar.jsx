import { NavLink } from 'react-router-dom'
import clsx from 'clsx'
import {
  Squares2X2Icon,
  BoltIcon,
  SparklesIcon,
  CpuChipIcon,
  ClipboardDocumentListIcon,
  DocumentChartBarIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline'

/** Navigation items */
const NAV_ITEMS = [
  { label: 'Analytics',   to: '/dashboard',   icon: Squares2X2Icon },
  { label: 'Workflows',   to: '/workflows',   icon: BoltIcon },
  { label: 'AI Analyzer', to: '/ai-analyzer', icon: SparklesIcon },
  { label: 'Agents',      to: '/agents',      icon: CpuChipIcon },
  { label: 'Executions',  to: '/executions',  icon: ClipboardDocumentListIcon },
  { label: 'Reports',     to: '/reports',     icon: DocumentChartBarIcon },
]

const BOTTOM_ITEMS = [
  { label: 'Settings', to: '/settings', icon: Cog6ToothIcon },
]

/**
 * Left sidebar with brand logo and navigation links.
 * Uses NavLink so the active route gets highlighted automatically.
 */
export default function Sidebar() {
  return (
    <aside className="flex flex-col w-60 shrink-0 bg-surface-card border-r border-surface-border">
      {/* ── Brand ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-surface-border">
        <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary-600 shrink-0">
          <BoltIcon className="w-5 h-5 text-white" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-white truncate leading-tight">AI Workflow</p>
          <p className="text-xs text-slate-400 truncate">Automation Platform</p>
        </div>
      </div>

      {/* ── Main navigation ────────────────────────────────────────────────── */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map((item) => (
          <NavItem key={item.to} {...item} />
        ))}
      </nav>

      {/* ── Bottom navigation ──────────────────────────────────────────────── */}
      <div className="px-3 py-4 border-t border-surface-border space-y-1">
        {BOTTOM_ITEMS.map((item) => (
          <NavItem key={item.to} {...item} />
        ))}

        {/* User avatar placeholder */}
        <div className="flex items-center gap-3 px-3 py-2 mt-2 rounded-lg">
          <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center shrink-0">
            <span className="text-xs font-semibold text-white">AI</span>
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-200 truncate">Admin User</p>
            <p className="text-xs text-slate-500 truncate">admin@platform.ai</p>
          </div>
        </div>
      </div>
    </aside>
  )
}

/** Individual nav item with active-state styling */
function NavItem({ to, label, icon: Icon }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        clsx(
          'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-150',
          isActive
            ? 'bg-primary-600/20 text-primary-400'
            : 'text-slate-400 hover:bg-surface-border hover:text-slate-200',
        )
      }
    >
      <Icon className="w-5 h-5 shrink-0" />
      {label}
    </NavLink>
  )
}
