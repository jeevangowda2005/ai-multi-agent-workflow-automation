import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  SparklesIcon,
  CpuChipIcon,
  ArrowRightIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  DocumentMagnifyingGlassIcon,
  ChartBarIcon,
  DocumentTextIcon,
  PresentationChartLineIcon,
  BoltIcon,
  ClockIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import api from '@/services/api'
import StatusBadge from '@/components/ui/StatusBadge'

const SAMPLE_PROMPTS = [
  {
    label: 'Market Research',
    category: 'research',
    icon: DocumentMagnifyingGlassIcon,
    text: 'Research top 5 enterprise competitors in AI workflow automation and summarize pricing models, core features, and target industries.',
  },
  {
    label: 'Executive Reporting',
    category: 'reporting',
    icon: PresentationChartLineIcon,
    text: 'Compile weekly engineering sprint metrics across teams and generate an executive summary highlighting delivery velocity and blockers.',
  },
  {
    label: 'Churn Data Analysis',
    category: 'data_analysis',
    icon: ChartBarIcon,
    text: 'Analyze monthly user churn dataset for SaaS customers, identify common cancellation triggers, and calculate correlation with onboarding delay.',
  },
  {
    label: 'Customer Outreach',
    category: 'content_generation',
    icon: DocumentTextIcon,
    text: 'Draft a personalized product update announcement email for enterprise tier customers introducing our new agent orchestration capabilities.',
  },
]

const CATEGORY_STYLES = {
  research: {
    bg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    icon: DocumentMagnifyingGlassIcon,
    label: 'Research',
  },
  reporting: {
    bg: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    icon: PresentationChartLineIcon,
    label: 'Reporting',
  },
  content_generation: {
    bg: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
    icon: DocumentTextIcon,
    label: 'Content Generation',
  },
  data_analysis: {
    bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    icon: ChartBarIcon,
    label: 'Data Analysis',
  },
  general: {
    bg: 'bg-slate-500/10 text-slate-300 border-slate-500/20',
    icon: BoltIcon,
    label: 'General',
  },
}

const PRIORITY_STYLES = {
  critical: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
  high: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  medium: 'bg-sky-500/10 text-sky-400 border-sky-500/30',
  low: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
}

const COMPLEXITY_STYLES = {
  complex: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
  moderate: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  simple: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
}

export default function AiAnalyzer() {
  const [taskDescription, setTaskDescription] = useState('')
  const [selectedWorkflowId, setSelectedWorkflowId] = useState('')
  const [workflows, setWorkflows] = useState([])
  const [aiHealth, setAiHealth] = useState(null)

  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // Fetch AI health and available workflows on mount
  useEffect(() => {
    let cancelled = false
    async function loadInitial() {
      try {
        const [healthData, wfData] = await Promise.all([
          api.getAiHealth().catch(() => null),
          api.listWorkflows().catch(() => []),
        ])
        if (!cancelled) {
          if (healthData) setAiHealth(healthData)
          if (wfData) setWorkflows(wfData)
        }
      } catch (err) {
        console.error('Error loading AI setup:', err)
      }
    }
    loadInitial()
    return () => {
      cancelled = true
    }
  }, [])

  const handleAnalyze = async (e) => {
    e.preventDefault()
    if (!taskDescription.trim()) {
      setError('Please provide a task description to analyze.')
      return
    }

    try {
      setAnalyzing(true)
      setError(null)
      setResult(null)

      const payload = {
        task_description: taskDescription.trim(),
        workflow_id: selectedWorkflowId ? Number(selectedWorkflowId) : null,
      }

      const res = await api.analyzeTask(payload)
      setResult(res)
    } catch (err) {
      setError(err.message || 'An error occurred while analyzing the task.')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleSampleClick = (text) => {
    setTaskDescription(text)
    setError(null)
  }

  const catStyle = result?.analysis
    ? CATEGORY_STYLES[result.analysis.category] || CATEGORY_STYLES.general
    : null
  const CatIcon = catStyle?.icon || SparklesIcon

  return (
    <div className="space-y-6 max-w-5xl">
      {/* ── Page Header ──────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-2xl font-bold text-white">Intelligent Task Analysis Agent</h2>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-600/20 text-primary-400 border border-primary-500/30">
              <SparklesIcon className="w-3.5 h-3.5" />
              LangGraph + Gemini
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Analyze business tasks, infer intent, evaluate complexity & priority, and determine agent execution pipelines.
          </p>
        </div>

        {/* AI Readiness Status */}
        {aiHealth && (
          <div
            className={`badge border ${
              aiHealth.status === 'ready'
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
                aiHealth.status === 'ready' ? 'bg-emerald-400' : 'bg-amber-400'
              }`}
            />
            {aiHealth.status === 'ready' ? `Model: ${aiHealth.model}` : 'Gemini Key Pending'}
          </div>
        )}
      </div>

      {/* ── Setup Notice if Gemini Key is unconfigured ─────────────────────── */}
      {aiHealth && !aiHealth.api_key_configured && (
        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-300 text-sm flex items-start gap-3">
          <ExclamationTriangleIcon className="w-5 h-5 shrink-0 mt-0.5 text-amber-400" />
          <div className="space-y-1">
            <p className="font-medium text-white">Gemini API Key Setup Required for Live Analysis</p>
            <p className="text-xs text-amber-300/90 leading-relaxed">
              To trigger real live analysis with Google Gemini, set your key in{' '}
              <code className="bg-surface px-1.5 py-0.5 rounded border border-surface-border text-amber-200">
                backend/.env
              </code>{' '}
              under <code className="text-amber-200 font-semibold">GEMINI_API_KEY</code>.
            </p>
          </div>
        </div>
      )}

      {/* ── Task Input Card ──────────────────────────────────────────────── */}
      <div className="card space-y-4">
        <form onSubmit={handleAnalyze} className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Business Task Description
              </label>
              <span className="text-xs text-slate-500">Natural language input</span>
            </div>
            <textarea
              rows={4}
              required
              placeholder="Describe the task you want to automate or analyze, e.g.:
'Conduct an in-depth competitive analysis of top 3 CRM systems in North America and output a feature gap table.'"
              value={taskDescription}
              onChange={(e) => setTaskDescription(e.target.value)}
              className="w-full px-4 py-3 bg-surface border border-surface-border rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50 transition-all font-sans"
            />
          </div>

          {/* Quick Sample Prompts */}
          <div>
            <p className="text-xs text-slate-400 mb-2">Try an enterprise example:</p>
            <div className="flex flex-wrap gap-2">
              {SAMPLE_PROMPTS.map((sample) => {
                const Icon = sample.icon
                return (
                  <button
                    key={sample.label}
                    type="button"
                    onClick={() => handleSampleClick(sample.text)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface border border-surface-border text-xs text-slate-300 hover:text-white hover:border-slate-500 transition-colors"
                  >
                    <Icon className="w-3.5 h-3.5 text-primary-400" />
                    {sample.label}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Workflow Association Dropdown */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-surface-border">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Associate with Workflow (Optional)
              </label>
              <select
                value={selectedWorkflowId}
                onChange={(e) => setSelectedWorkflowId(e.target.value)}
                className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              >
                <option value="">None (Analyze without saving)</option>
                {workflows.map((wf) => (
                  <option key={wf.id} value={wf.id}>
                    #{wf.id} — {wf.name} ({wf.status})
                  </option>
                ))}
              </select>
              <p className="text-xs text-slate-500 mt-1">
                If chosen, the analysis result will be stored as an actionable task node in PostgreSQL.
              </p>
            </div>

            <div className="flex items-end justify-end">
              <button
                type="submit"
                disabled={analyzing || !taskDescription.trim()}
                className="btn-primary w-full sm:w-auto px-6 py-2.5 text-sm"
              >
                {analyzing ? (
                  <>
                    <ArrowPathIcon className="w-4 h-4 animate-spin" />
                    Analyzing with LangGraph Agent…
                  </>
                ) : (
                  <>
                    <SparklesIcon className="w-4 h-4" />
                    Analyze Task
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* ── Error Banner ─────────────────────────────────────────────────── */}
      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-sm flex items-start gap-3 animate-in fade-in">
          <ExclamationTriangleIcon className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-rose-300">Analysis Request Failed</p>
            <p className="text-xs text-rose-400/90 leading-relaxed">{error}</p>
          </div>
        </div>
      )}

      {/* ── Loading Skeleton ─────────────────────────────────────────────── */}
      {analyzing && (
        <div className="card p-6 space-y-4 animate-pulse">
          <div className="flex items-center justify-between">
            <div className="h-6 bg-surface-border rounded w-48" />
            <div className="h-4 bg-surface-border rounded w-24" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="h-10 bg-surface rounded-lg" />
            <div className="h-10 bg-surface rounded-lg" />
            <div className="h-10 bg-surface rounded-lg" />
          </div>
          <div className="h-20 bg-surface rounded-lg" />
          <div className="h-24 bg-surface rounded-lg" />
        </div>
      )}

      {/* ── Analysis Results Display ─────────────────────────────────────── */}
      {result && result.analysis && (
        <div className="space-y-4 animate-in fade-in duration-200">
          {/* Top metadata pill bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 px-1 text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <span className="font-medium text-slate-200">Agent Execution Complete</span>
              <span>•</span>
              <span className="font-mono text-primary-400">{result.model_used}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1 font-mono">
                <ClockIcon className="w-3.5 h-3.5 text-slate-500" />
                {result.execution_time_ms} ms
              </span>
            </div>
          </div>

          {/* Workflow association confirmation */}
          {result.saved_task_id && (
            <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-sm flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <CheckCircleIcon className="w-5 h-5 shrink-0" />
                <span>
                  Analysis saved to Workflow <strong>#{result.workflow_id}</strong> as Task{' '}
                  <strong>#{result.saved_task_id}</strong> in PostgreSQL.
                </span>
              </div>
              <Link
                to={`/workflows/${result.workflow_id}`}
                className="btn-ghost text-xs py-1 px-3 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/20"
              >
                View in Workflow →
              </Link>
            </div>
          )}

          {/* Core Decision Summary Card */}
          <div className="card space-y-6">
            {/* Attribute Badges */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Category */}
              <div className={`p-3 rounded-xl border flex items-center gap-3 ${catStyle.bg}`}>
                <CatIcon className="w-6 h-6 shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs uppercase tracking-wider opacity-75 font-medium">Category</p>
                  <p className="text-sm font-bold capitalize truncate">{catStyle.label}</p>
                </div>
              </div>

              {/* Priority */}
              <div
                className={`p-3 rounded-xl border flex items-center gap-3 ${
                  PRIORITY_STYLES[result.analysis.priority] || PRIORITY_STYLES.medium
                }`}
              >
                <div className="w-2.5 h-2.5 rounded-full bg-current shrink-0 ml-1" />
                <div className="min-w-0">
                  <p className="text-xs uppercase tracking-wider opacity-75 font-medium">Priority</p>
                  <p className="text-sm font-bold capitalize truncate">
                    {result.analysis.priority}
                  </p>
                </div>
              </div>

              {/* Complexity */}
              <div
                className={`p-3 rounded-xl border flex items-center gap-3 ${
                  COMPLEXITY_STYLES[result.analysis.complexity] || COMPLEXITY_STYLES.moderate
                }`}
              >
                <CpuChipIcon className="w-6 h-6 shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs uppercase tracking-wider opacity-75 font-medium">Complexity</p>
                  <p className="text-sm font-bold capitalize truncate">
                    {result.analysis.complexity}
                  </p>
                </div>
              </div>
            </div>

            {/* Inferred Intent */}
            <div className="space-y-1.5">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Inferred User Intent
              </h4>
              <p className="text-base font-medium text-white leading-relaxed bg-surface p-4 rounded-xl border border-surface-border">
                {result.analysis.task_intent}
              </p>
            </div>

            {/* Recommended Action */}
            <div className="space-y-1.5">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Recommended Execution Action
              </h4>
              <div className="p-4 rounded-xl bg-primary-600/10 border border-primary-500/30 text-primary-200 flex items-start gap-3">
                <ArrowRightIcon className="w-5 h-5 text-primary-400 shrink-0 mt-0.5" />
                <p className="text-sm font-semibold">{result.analysis.recommended_action}</p>
              </div>
            </div>

            {/* Explanation & Rationale */}
            <div className="space-y-1.5">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Decision Explanation
              </h4>
              <p className="text-sm text-slate-300 leading-relaxed bg-surface/50 p-4 rounded-xl border border-surface-border">
                {result.analysis.explanation}
              </p>
            </div>

            {/* Suggested Subtasks */}
            {result.analysis.suggested_subtasks?.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-surface-border">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Recommended Subtask Breakdown
                </h4>
                <div className="space-y-2">
                  {result.analysis.suggested_subtasks.map((subtask, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-3 p-3 bg-surface rounded-lg border border-surface-border text-sm text-slate-200"
                    >
                      <span className="flex items-center justify-center w-5 h-5 rounded-full bg-primary-600/20 text-primary-400 text-xs font-bold shrink-0 mt-0.5">
                        {idx + 1}
                      </span>
                      <span>{subtask}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
