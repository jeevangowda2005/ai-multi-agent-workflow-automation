import clsx from 'clsx'

/** Color variant → Tailwind class maps (must be complete strings for purge safety) */
const COLOR_MAP = {
  indigo:  { bg: 'bg-indigo-500/10',  icon: 'text-indigo-400',  border: 'border-indigo-500/20' },
  violet:  { bg: 'bg-violet-500/10',  icon: 'text-violet-400',  border: 'border-violet-500/20' },
  sky:     { bg: 'bg-sky-500/10',     icon: 'text-sky-400',     border: 'border-sky-500/20' },
  emerald: { bg: 'bg-emerald-500/10', icon: 'text-emerald-400', border: 'border-emerald-500/20' },
}

/**
 * Stat card displayed in the dashboard summary strip.
 *
 * @param {object} props
 * @param {string}   props.label  - Stat label text
 * @param {string}   props.value  - Current value (string to allow "—")
 * @param {React.ElementType} props.icon - Heroicon component
 * @param {string}   props.color  - One of: indigo | violet | sky | emerald
 */
export default function StatCard({ label, value, icon: Icon, color = 'indigo' }) {
  const c = COLOR_MAP[color] ?? COLOR_MAP.indigo

  return (
    <div className={clsx('card flex items-center gap-4 border', c.border)}>
      <div className={clsx('flex items-center justify-center w-11 h-11 rounded-xl shrink-0', c.bg)}>
        <Icon className={clsx('w-6 h-6', c.icon)} />
      </div>
      <div className="min-w-0">
        <p className="text-2xl font-bold text-white leading-none">{value}</p>
        <p className="mt-1 text-xs text-slate-400 truncate">{label}</p>
      </div>
    </div>
  )
}
