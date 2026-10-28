import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  BoltIcon,
  CpuChipIcon,
  ClipboardDocumentListIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ArrowRightIcon,
  ArrowPathIcon,
  DocumentChartBarIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import StatCard from '@/components/ui/StatCard'
import StatusBadge from '@/components/ui/StatusBadge'
import api from '@/services/api'

export default function Dashboard() {
  const navigate = useNavigate()

  // State
  const [overview, setOverview] = useState(null)
  const [trends, setTrends] = useState([])
  const [agents, setAgents] = useState([])
  const [recentWorkflows, setRecentWorkflows] = useState([])
  const [trendDays, setTrendDays] = useState(7)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const [hoveredTrend, setHoveredTrend] = useState(null)

  // Fetch all analytics data concurrently
  const fetchDashboardData = useCallback(async () => {
    try {
      setError(null)
      const [ovData, trData, agData, wfData] = await Promise.all([
        api.getAnalyticsOverview(),
        api.getAnalyticsTrends({ days: trendDays }),
        api.getAnalyticsAgents(),
        api.listWorkflows({ limit: 5 }),
      ])
      setOverview(ovData)
      setTrends(trData.data_points || [])
      setAgents(agData.agents || [])
      setRecentWorkflows(wfData.items || wfData || [])
    } catch (err) {
      console.error('Failed to load analytics dashboard data:', err)
      setError(err.message || 'Failed to load analytics metrics.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [trendDays])

  useEffect(() => {
    fetchDashboardData()
  }, [fetchDashboardData])

  const handleRefresh = () => {
    setRefreshing(true)
    fetchDashboardData()
  }

  // Calculate maximum total in trends for chart scaling
  const maxTrendTotal = Math.max(1, ...(trends.map((t) => t.total || 0)))

  return (
    <div className="space-y-6">
      {/* ── Top Header & Controls ────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Platform Analytics & Telemetry</h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time execution analytics, agent efficiency metrics, and workflow telemetry from PostgreSQL.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Trend Period Selector */}
          <div className="flex rounded-lg bg-surface border border-surface-border p-0.5 text-xs">
            {[7, 14, 30].map((d) => (
              <button
                key={d}
                onClick={() => setTrendDays(d)}
                className={`px-2.5 py-1 rounded-md transition-colors ${
                  trendDays === d
                    ? 'bg-primary-600 text-white font-medium'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {d}D
              </button>
            ))}
          </div>

          <button
            onClick={handleRefresh}
            disabled={refreshing}
            title="Refresh analytics metrics"
            className="p-2 rounded-lg bg-surface-card border border-surface-border text-slate-400 hover:text-white hover:bg-surface-border transition-colors"
          >
            <ArrowPathIcon className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>

          <Link to="/reports" className="btn-primary text-xs flex items-center gap-1.5">
            <DocumentChartBarIcon className="w-4 h-4" />
            AI Reports
          </Link>
        </div>
      </div>

      {/* ── Error Banner ─────────────────────────────────────────────────── */}
      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-200">
            ✕
          </button>
        </div>
      )}

      {/* ── Summary Stat Cards ───────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="Total Executions"
          value={loading ? '—' : String(overview?.total_executions ?? 0)}
          icon={ClipboardDocumentListIcon}
          color="indigo"
          subtext={
            overview
              ? `${overview.completed_executions} completed, ${overview.failed_executions} failed`
              : 'All historical runs'
          }
        />
        <StatCard
          label="Success Rate"
          value={loading ? '—' : `${overview?.success_rate ?? 0}%`}
          icon={CheckCircleIcon}
          color="emerald"
          subtext={
            overview && overview.total_executions > 0
              ? `${overview.completed_executions} of ${overview.total_executions} successful`
              : 'No executions yet'
          }
        />
        <StatCard
          label="Avg Duration"
          value={loading ? '—' : `${overview?.avg_duration_seconds ?? 0}s`}
          icon={ClockIcon}
          color="sky"
          subtext="Per automated execution"
        />
        <StatCard
          label="Configured Workflows"
          value={loading ? '—' : String(overview?.total_workflows ?? 0)}
          icon={BoltIcon}
          color="violet"
          subtext={overview ? `${overview.total_tasks} total tasks` : 'Total active workflows'}
        />
      </div>

      {/* ── Main Analytics Section: Trends & Agent Distribution ──────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Execution Trends Chart */}
        <div className="card lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-white">Execution Trends ({trendDays} Days)</h3>
              <p className="text-xs text-slate-400">
                Daily volume of workflow executions and completion outcomes.
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-sm bg-primary-500 inline-block" />
                Completed
              </span>
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-sm bg-rose-500 inline-block" />
                Failed
              </span>
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-sm bg-slate-500 inline-block" />
                Canceled
              </span>
            </div>
          </div>

          {/* Interactive SVG Bar / Trend Chart */}
          <div className="pt-4 pb-2">
            {trends.length === 0 ? (
              <div className="h-56 flex items-center justify-center text-xs text-slate-500 border border-dashed border-surface-border rounded-xl">
                No trend data available for this timeframe.
              </div>
            ) : (
              <div className="relative">
                {/* Tooltip */}
                {hoveredTrend && (
                  <div className="absolute top-0 right-0 p-2.5 bg-surface border border-surface-border rounded-lg text-xs text-slate-200 shadow-xl pointer-events-none z-10 space-y-0.5">
                    <p className="font-semibold text-white">{hoveredTrend.date}</p>
                    <p className="text-primary-400">Completed: {hoveredTrend.completed}</p>
                    <p className="text-rose-400">Failed: {hoveredTrend.failed}</p>
                    <p className="text-slate-400">Total: {hoveredTrend.total}</p>
                  </div>
                )}

                <div className="h-56 flex items-end gap-2 sm:gap-4 px-2 border-b border-surface-border">
                  {trends.map((item, idx) => {
                    const completedHeight = Math.max(4, (item.completed / maxTrendTotal) * 180)
                    const failedHeight = Math.max(0, (item.failed / maxTrendTotal) * 180)
                    const isHovered = hoveredTrend?.date === item.date

                    return (
                      <div
                        key={item.date || idx}
                        onMouseEnter={() => setHoveredTrend(item)}
                        onMouseLeave={() => setHoveredTrend(null)}
                        className="flex-1 flex flex-col items-center gap-1 group cursor-pointer"
                      >
                        <div className="w-full flex flex-col justify-end items-center gap-0.5 h-48">
                          {/* Stacked Bars */}
                          {item.failed > 0 && (
                            <div
                              style={{ height: `${failedHeight}px` }}
                              className="w-full max-w-[28px] bg-rose-500 rounded-t-sm transition-all group-hover:brightness-125"
                            />
                          )}
                          <div
                            style={{ height: `${completedHeight}px` }}
                            className={`w-full max-w-[28px] transition-all rounded-sm ${
                              item.completed > 0 ? 'bg-primary-500 group-hover:bg-primary-400' : 'bg-surface-border/50'
                            }`}
                          />
                        </div>
                        <span
                          className={`text-[10px] truncate max-w-[36px] font-mono mt-1 ${
                            isHovered ? 'text-primary-400 font-semibold' : 'text-slate-500'
                          }`}
                        >
                          {item.date.slice(5)}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column (1 Col): Status Breakdown & Actions */}
        <div className="card space-y-4">
          <h3 className="text-base font-semibold text-white">Execution Health</h3>
          <p className="text-xs text-slate-400">Outcome ratio across all executed pipelines.</p>

          <div className="space-y-3 pt-2">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-emerald-400 font-medium">Completed</span>
                <span className="font-mono text-slate-300">{overview?.completed_executions ?? 0}</span>
              </div>
              <div className="w-full h-2 bg-surface rounded-full overflow-hidden border border-surface-border">
                <div
                  className="h-full bg-emerald-500 rounded-full"
                  style={{
                    width: `${
                      overview?.total_executions
                        ? (overview.completed_executions / overview.total_executions) * 100
                        : 0
                    }%`,
                  }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-rose-400 font-medium">Failed</span>
                <span className="font-mono text-slate-300">{overview?.failed_executions ?? 0}</span>
              </div>
              <div className="w-full h-2 bg-surface rounded-full overflow-hidden border border-surface-border">
                <div
                  className="h-full bg-rose-500 rounded-full"
                  style={{
                    width: `${
                      overview?.total_executions
                        ? (overview.failed_executions / overview.total_executions) * 100
                        : 0
                    }%`,
                  }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-400 font-medium">Canceled</span>
                <span className="font-mono text-slate-300">{overview?.canceled_executions ?? 0}</span>
              </div>
              <div className="w-full h-2 bg-surface rounded-full overflow-hidden border border-surface-border">
                <div
                  className="h-full bg-slate-500 rounded-full"
                  style={{
                    width: `${
                      overview?.total_executions
                        ? (overview.canceled_executions / overview.total_executions) * 100
                        : 0
                    }%`,
                  }}
                />
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-surface-border space-y-2">
            <Link
              to="/executions"
              className="btn-ghost border border-surface-border w-full flex items-center justify-center gap-1.5 text-xs py-2"
            >
              <ClipboardDocumentListIcon className="w-4 h-4" />
              Open Execution History
            </Link>
            <Link
              to="/reports"
              className="btn-primary w-full flex items-center justify-center gap-1.5 text-xs py-2"
            >
              <SparklesIcon className="w-4 h-4" />
              Generate AI Report
            </Link>
          </div>
        </div>
      </div>

      {/* ── Specialized AI Agent Efficiency & Usage Table ───────────────── */}
      <div className="card space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-white">Specialized AI Agent Performance</h3>
            <p className="text-xs text-slate-400">
              Workload allocation, success reliability, and processing speeds per agent.
            </p>
          </div>
          <Link
            to="/agents"
            className="text-xs text-primary-400 hover:text-primary-300 flex items-center gap-1 font-medium"
          >
            Agent Workspace
            <ArrowRightIcon className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-1">
          {agents.map((agent) => (
            <div
              key={agent.agent_type}
              className="p-4 rounded-xl border border-surface-border bg-surface/40 hover:bg-surface/70 transition-colors space-y-3"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-white">{agent.name}</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface border border-surface-border text-slate-400">
                  {agent.agent_type}
                </span>
              </div>

              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between text-slate-400">
                  <span>Total Runs:</span>
                  <span className="font-semibold text-slate-200">{agent.total_runs}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Success Rate:</span>
                  <span className="font-semibold text-emerald-400">{agent.success_rate}%</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Avg Latency:</span>
                  <span className="font-mono text-slate-200">
                    {agent.avg_time_ms > 0 ? `${(agent.avg_time_ms / 1000).toFixed(2)}s` : '—'}
                  </span>
                </div>
              </div>

              {/* Progress bar of success */}
              <div className="w-full h-1.5 bg-surface rounded-full overflow-hidden border border-surface-border">
                <div
                  className="h-full bg-primary-500 rounded-full"
                  style={{ width: `${agent.success_rate}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Recent Workflows ─────────────────────────────────────────────── */}
      <div className="card space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-white">Recent Workflows</h3>
          <Link
            to="/workflows"
            className="text-xs text-primary-400 hover:text-primary-300 flex items-center gap-1 font-medium"
          >
            View all
            <ArrowRightIcon className="w-3.5 h-3.5" />
          </Link>
        </div>

        {recentWorkflows.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-500 border border-dashed border-surface-border rounded-xl">
            No workflows created yet. Create a workflow to start orchestrating tasks.
          </div>
        ) : (
          <div className="divide-y divide-surface-border">
            {recentWorkflows.map((wf) => (
              <div
                key={wf.id}
                className="py-3 flex items-center justify-between hover:bg-surface/40 px-2 rounded-lg transition-colors"
              >
                <div className="min-w-0 pr-4">
                  <Link
                    to={`/workflows/${wf.id}`}
                    className="text-sm font-medium text-white hover:text-primary-400 truncate block"
                  >
                    {wf.name}
                  </Link>
                  <p className="text-xs text-slate-400 truncate mt-0.5">
                    {wf.description || 'No description provided'}
                  </p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <StatusBadge status={wf.status} />
                  <Link
                    to={`/workflows/${wf.id}`}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-border"
                  >
                    <ArrowRightIcon className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
