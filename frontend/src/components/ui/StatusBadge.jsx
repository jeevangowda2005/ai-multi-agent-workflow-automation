import clsx from 'clsx'

const STATUS_CONFIG = {
  active: {
    bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    dot: 'bg-emerald-400',
    label: 'Active',
  },
  draft: {
    bg: 'bg-slate-500/10 text-slate-300 border-slate-500/20',
    dot: 'bg-slate-400',
    label: 'Draft',
  },
  paused: {
    bg: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    dot: 'bg-amber-400',
    label: 'Paused',
  },
  archived: {
    bg: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20',
    dot: 'bg-zinc-400',
    label: 'Archived',
  },
  // Task / execution statuses
  pending: {
    bg: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
    dot: 'bg-sky-400',
    label: 'Pending',
  },
  in_progress: {
    bg: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    dot: 'bg-indigo-400 animate-pulse',
    label: 'In Progress',
  },
  running: {
    bg: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    dot: 'bg-indigo-400 animate-pulse',
    label: 'Running',
  },
  completed: {
    bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    dot: 'bg-emerald-400',
    label: 'Completed',
  },
  failed: {
    bg: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    dot: 'bg-rose-400',
    label: 'Failed',
  },
  canceled: {
    bg: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
    dot: 'bg-slate-400',
    label: 'Canceled',
  },
}

export default function StatusBadge({ status, className }) {
  const normalized = (status || 'draft').toLowerCase()
  const cfg = STATUS_CONFIG[normalized] || {
    bg: 'bg-slate-500/10 text-slate-300 border-slate-500/20',
    dot: 'bg-slate-400',
    label: status,
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border capitalize',
        cfg.bg,
        className
      )}
    >
      <span className={clsx('w-1.5 h-1.5 rounded-full', cfg.dot)} />
      {cfg.label}
    </span>
  )
}
