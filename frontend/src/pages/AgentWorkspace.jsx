import { useState, useEffect } from 'react'
import {
  CpuChipIcon,
  SparklesIcon,
  DocumentMagnifyingGlassIcon,
  DocumentTextIcon,
  ChartBarIcon,
  PresentationChartLineIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  ClipboardDocumentIcon,
  ClipboardDocumentCheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  InformationCircleIcon,
  TagIcon,
} from '@heroicons/react/24/outline'
import api from '@/services/api'
import StatusBadge from '@/components/ui/StatusBadge'

const SAMPLE_TASKS = [
  {
    label: 'Market Research',
    agent: 'research',
    task: 'Research the impact of post-quantum cryptography on financial institutions, identifying current NIST standards and compliance timelines.',
    data: '',
  },
  {
    label: 'Sales CSV Analysis',
    agent: 'data_analysis',
    task: 'Analyze the regional quarterly sales dataset, compute key performance metrics, and highlight territory anomalies.',
    data: 'Region,Quarter,Revenue,Target,Units_Sold\nNorth,Q3,185000,150000,1240\nSouth,Q3,92000,110000,680\nEast,Q3,210000,180000,1490\nWest,Q3,78000,95000,530\nCentral,Q3,142000,140000,1010',
  },
  {
    label: 'Product Announcement',
    agent: 'content_generation',
    task: 'Draft an executive launch announcement email to enterprise customers introducing our autonomous multi-agent orchestration engine.',
    data: '',
    tone: 'executive',
  },
  {
    label: 'Q3 Executive Report',
    agent: 'reporting',
    task: 'Generate a comprehensive quarterly executive report on system reliability, uptime SLA metrics, and operational recommendations.',
    data: 'Overall Availability: 99.98%\nP99 Latency: 112ms (down from 170ms in Q2)\nTotal Handled Requests: 48.2 Million\nResolved Incidents: 3 minor, 0 major\nMean Time to Recovery: 4.2 minutes',
  },
]

const AGENT_CONFIGS = {
  research: {
    label: 'Research Agent',
    icon: DocumentMagnifyingGlassIcon,
    color: 'text-cyan-400',
    border: 'border-cyan-500/30',
    bg: 'bg-cyan-500/10',
    desc: 'Deep fact extraction & AI projections',
  },
  content_generation: {
    label: 'Content Generation Agent',
    icon: DocumentTextIcon,
    color: 'text-violet-400',
    border: 'border-violet-500/30',
    bg: 'bg-violet-500/10',
    desc: 'Multi-tone enterprise copy & articles',
  },
  data_analysis: {
    label: 'Data Analysis Agent',
    icon: ChartBarIcon,
    color: 'text-emerald-400',
    border: 'border-emerald-500/30',
    bg: 'bg-emerald-500/10',
    desc: 'Empirical patterns & verified metrics',
  },
  reporting: {
    label: 'Enterprise Reporting Agent',
    icon: PresentationChartLineIcon,
    color: 'text-indigo-400',
    border: 'border-indigo-500/30',
    bg: 'bg-indigo-500/10',
    desc: 'Formal briefings & strategic roadmaps',
  },
}

export default function AgentWorkspace() {
  const [taskDescription, setTaskDescription] = useState('')
  const [dataInput, setDataInput] = useState('')
  const [showDataInput, setShowDataInput] = useState(false)
  const [agentOverride, setAgentOverride] = useState('')
  const [tone, setTone] = useState('professional')
  const [selectedWorkflowId, setSelectedWorkflowId] = useState('')
  const [workflows, setWorkflows] = useState([])
  const [availableAgents, setAvailableAgents] = useState([])

  // Execution states
  const [executing, setExecuting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [copied, setCopied] = useState(false)
  const [showRawJson, setShowRawJson] = useState(false)

  // Fetch metadata and history on mount
  useEffect(() => {
    fetchInitialData()
  }, [])

  const fetchInitialData = async () => {
    try {
      const [agentsData, workflowsData] = await Promise.all([
        api.listAgents().catch(() => []),
        api.listWorkflows().catch(() => []),
      ])
      setAvailableAgents(agentsData)
      setWorkflows(workflowsData)
      fetchHistory()
    } catch (_err) {
      // Graceful fallback
    }
  }

  const fetchHistory = async () => {
    setLoadingHistory(true)
    try {
      const execs = await api.listAgentExecutions({ limit: 10 })
      setHistory(execs)
    } catch (_err) {
      // Non-blocking
    } finally {
      setLoadingHistory(false)
    }
  }

  const handleExecute = async (e) => {
    e?.preventDefault()
    if (!taskDescription.trim() || taskDescription.trim().length < 3) {
      setError('Task description must be at least 3 characters long.')
      return
    }

    setExecuting(true)
    setError(null)
    setResult(null)

    const payload = {
      task_description: taskDescription.trim(),
      data_input: dataInput.trim() || null,
      agent_override: agentOverride || null,
      tone: tone || null,
      workflow_id: selectedWorkflowId ? parseInt(selectedWorkflowId, 10) : null,
    }

    try {
      const res = await api.executeAgentTask(payload)
      setResult(res)
      fetchHistory()
    } catch (err) {
      setError(err.message || 'Agent execution failed. Please check backend connection.')
    } finally {
      setExecuting(false)
    }
  }

  const handleCopyResult = () => {
    if (!result?.output) return
    navigator.clipboard.writeText(JSON.stringify(result.output, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const loadSample = (sample) => {
    setTaskDescription(sample.task)
    setDataInput(sample.data || '')
    setShowDataInput(Boolean(sample.data))
    if (sample.tone) setTone(sample.tone)
    setAgentOverride('')
    setError(null)
  }

  const loadHistoryItem = (item) => {
    setResult(item)
    setTaskDescription(item.task_input)
    setDataInput(item.data_input || '')
    setShowDataInput(Boolean(item.data_input))
    setError(null)
  }

  return (
    <div className="space-y-6">
      {/* ── Page Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2">
            <CpuChipIcon className="w-7 h-7 text-primary-400" />
            <h1 className="text-2xl font-bold text-white tracking-tight">AI Agent Workspace</h1>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Intelligent Multi-Agent Routing Engine powered by LangGraph & Google Gemini.
          </p>
        </div>

        {/* Available Agents Counter Bar */}
        <div className="flex items-center gap-2">
          {Object.entries(AGENT_CONFIGS).map(([key, config]) => {
            const Icon = config.icon
            return (
              <div
                key={key}
                className={`hidden lg:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium ${config.bg} ${config.color} ${config.border}`}
                title={config.desc}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{config.label.replace(' Agent', '')}</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Main Layout Grid ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Form Controls (5 cols) */}
        <div className="lg:col-span-5 space-y-5">
          {/* Preset Prompts */}
          <div className="bg-surface-card border border-surface-border rounded-xl p-4">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
              Quick Load Sample Tasks
            </p>
            <div className="grid grid-cols-2 gap-2">
              {SAMPLE_TASKS.map((sample) => (
                <button
                  key={sample.label}
                  type="button"
                  onClick={() => loadSample(sample)}
                  className="flex items-center justify-between text-left px-3 py-2 rounded-lg bg-surface-border/50 hover:bg-surface-border text-xs text-slate-300 hover:text-white transition-colors border border-transparent hover:border-slate-600"
                >
                  <span className="truncate font-medium">{sample.label}</span>
                  <SparklesIcon className="w-3.5 h-3.5 text-primary-400 shrink-0 ml-1" />
                </button>
              ))}
            </div>
          </div>

          {/* Execution Form */}
          <form onSubmit={handleExecute} className="bg-surface-card border border-surface-border rounded-xl p-5 space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-200 mb-1.5">
                Task Description <span className="text-rose-400">*</span>
              </label>
              <textarea
                rows={4}
                value={taskDescription}
                onChange={(e) => setTaskDescription(e.target.value)}
                placeholder="Describe your business task in natural language... (e.g. 'Analyze regional customer feedback and identify top complaints')"
                className="w-full bg-slate-900 border border-surface-border rounded-lg px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-colors resize-none"
              />
            </div>

            {/* Optional Data Input Accordion */}
            <div className="border border-surface-border rounded-lg overflow-hidden bg-slate-900/50">
              <button
                type="button"
                onClick={() => setShowDataInput(!showDataInput)}
                className="w-full flex items-center justify-between px-3.5 py-2.5 text-xs font-medium text-slate-300 hover:text-white transition-colors"
              >
                <span className="flex items-center gap-1.5">
                  <ChartBarIcon className="w-4 h-4 text-emerald-400" />
                  Attach Structured Data (CSV / JSON)
                  {dataInput.trim() && (
                    <span className="ml-1.5 px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400">
                      Attached
                    </span>
                  )}
                </span>
                {showDataInput ? (
                  <ChevronUpIcon className="w-4 h-4 text-slate-400" />
                ) : (
                  <ChevronDownIcon className="w-4 h-4 text-slate-400" />
                )}
              </button>

              {showDataInput && (
                <div className="p-3 border-t border-surface-border bg-slate-900 space-y-2">
                  <p className="text-[11px] text-slate-400">
                    Paste raw CSV lines or JSON array for empirical analysis without hallucination:
                  </p>
                  <textarea
                    rows={4}
                    value={dataInput}
                    onChange={(e) => setDataInput(e.target.value)}
                    placeholder="Region,Revenue,Target\nNorth,120000,100000\nSouth,85000,90000..."
                    className="w-full font-mono text-xs bg-slate-950 border border-surface-border rounded px-3 py-2 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-emerald-500"
                  />
                  {dataInput && (
                    <button
                      type="button"
                      onClick={() => setDataInput('')}
                      className="text-[10px] text-rose-400 hover:underline"
                    >
                      Clear Attached Data
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Routing & Controls Grid */}
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Agent Selection
                </label>
                <select
                  value={agentOverride}
                  onChange={(e) => setAgentOverride(e.target.value)}
                  className="w-full bg-slate-900 border border-surface-border rounded-lg px-2.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-primary-500"
                >
                  <option value="">Auto-Route (Intelligent)</option>
                  <option value="research">Research Agent</option>
                  <option value="content_generation">Content Generation</option>
                  <option value="data_analysis">Data Analysis</option>
                  <option value="reporting">Enterprise Reporting</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Writing Tone
                </label>
                <select
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  className="w-full bg-slate-900 border border-surface-border rounded-lg px-2.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-primary-500"
                >
                  <option value="professional">Professional</option>
                  <option value="executive">Executive</option>
                  <option value="persuasive">Persuasive</option>
                  <option value="casual">Casual</option>
                  <option value="concise">Concise</option>
                </select>
              </div>
            </div>

            {/* Optional Workflow Link */}
            {workflows.length > 0 && (
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Link Execution to Existing Workflow (Optional)
                </label>
                <select
                  value={selectedWorkflowId}
                  onChange={(e) => setSelectedWorkflowId(e.target.value)}
                  className="w-full bg-slate-900 border border-surface-border rounded-lg px-2.5 py-2 text-xs text-slate-300 focus:outline-none focus:border-primary-500"
                >
                  <option value="">None (Standalone Execution)</option>
                  {workflows.map((wf) => (
                    <option key={wf.id} value={wf.id}>
                      {wf.name} (ID: {wf.id})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={executing || !taskDescription.trim()}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-primary-600 hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium text-sm transition-colors shadow-lg shadow-primary-600/20"
            >
              {executing ? (
                <>
                  <ArrowPathIcon className="w-4 h-4 animate-spin text-white" />
                  <span>Routing & Executing Agent...</span>
                </>
              ) : (
                <>
                  <SparklesIcon className="w-4 h-4 text-white" />
                  <span>Execute Task</span>
                </>
              )}
            </button>
          </form>

          {/* Execution History */}
          <div className="bg-surface-card border border-surface-border rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Recent Executions
              </span>
              <button
                type="button"
                onClick={fetchHistory}
                disabled={loadingHistory}
                className="text-slate-500 hover:text-slate-300 transition-colors"
                title="Refresh history"
              >
                <ArrowPathIcon className={`w-3.5 h-3.5 ${loadingHistory ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {history.length === 0 ? (
              <p className="text-xs text-slate-500 py-3 text-center">No recent executions yet.</p>
            ) : (
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {history.map((item) => {
                  const cfg = AGENT_CONFIGS[item.selected_agent] || AGENT_CONFIGS.research
                  const Icon = cfg.icon
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => loadHistoryItem(item)}
                      className="w-full text-left p-2 rounded-lg bg-slate-900/60 hover:bg-surface-border/70 border border-surface-border transition-colors flex items-center justify-between gap-2"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <Icon className={`w-3 h-3 ${cfg.color} shrink-0`} />
                          <span className={`text-[11px] font-medium truncate ${cfg.color}`}>
                            {cfg.label}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 truncate mt-0.5">{item.task_input}</p>
                      </div>
                      <span className="text-[10px] text-slate-500 shrink-0 font-mono">
                        {item.execution_time_ms ? `${Math.round(item.execution_time_ms)}ms` : ''}
                      </span>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Execution Output (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {/* Error Banner */}
          {error && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-start gap-3">
              <ExclamationTriangleIcon className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-rose-200">Execution Error</p>
                <p className="text-xs mt-0.5 text-rose-300/90">{error}</p>
              </div>
            </div>
          )}

          {/* Loading Active State */}
          {executing && (
            <div className="bg-surface-card border border-surface-border rounded-xl p-8 text-center space-y-4">
              <div className="w-12 h-12 mx-auto rounded-full bg-primary-600/20 border border-primary-500/40 flex items-center justify-center">
                <ArrowPathIcon className="w-6 h-6 text-primary-400 animate-spin" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-white">LangGraph Agent Pipeline Running</h3>
                <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                  Step 1: Task Analysis Agent classifies intent. <br />
                  Step 2: Router conditionally directs to specialized agent with Pydantic validation.
                </p>
              </div>
            </div>
          )}

          {/* Completed Result Display */}
          {result && !executing && (
            <div className="bg-surface-card border border-surface-border rounded-xl overflow-hidden shadow-xl space-y-0">
              {/* Result Meta Header */}
              {(() => {
                const agentKey = result.selected_agent
                const cfg = AGENT_CONFIGS[agentKey] || AGENT_CONFIGS.research
                const Icon = cfg.icon
                return (
                  <div className="p-4 bg-slate-900 border-b border-surface-border flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${cfg.bg} border ${cfg.border}`}>
                        <Icon className={`w-5 h-5 ${cfg.color}`} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-white">{cfg.label}</span>
                          <StatusBadge status={result.status || 'completed'} />
                        </div>
                        <p className="text-xs text-slate-400 mt-0.5 max-w-lg truncate">
                          {result.routing_reasoning || 'Auto-routed by LangGraph StateGraph'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 text-xs">
                      {result.execution_time_ms && (
                        <span className="flex items-center gap-1 text-slate-400 font-mono">
                          <ClockIcon className="w-3.5 h-3.5 text-slate-500" />
                          {result.execution_time_ms} ms
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={handleCopyResult}
                        className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors border border-surface-border"
                      >
                        {copied ? (
                          <>
                            <ClipboardDocumentCheckIcon className="w-3.5 h-3.5 text-emerald-400" />
                            <span className="text-emerald-400">Copied</span>
                          </>
                        ) : (
                          <>
                            <ClipboardDocumentIcon className="w-3.5 h-3.5" />
                            <span>Copy JSON</span>
                          </>
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowRawJson(!showRawJson)}
                        className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors border border-surface-border text-[11px]"
                      >
                        {showRawJson ? 'Structured View' : 'Raw JSON'}
                      </button>
                    </div>
                  </div>
                )
              })()}

              {/* Result Body Content */}
              <div className="p-5">
                {showRawJson ? (
                  <pre className="p-4 rounded-lg bg-slate-950 font-mono text-xs text-slate-300 overflow-x-auto max-h-[600px] border border-surface-border">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                ) : (
                  <AgentResultRenderer
                    agentType={result.selected_agent}
                    output={result.output}
                    analysis={result.analysis}
                  />
                )}
              </div>
            </div>
          )}

          {/* Idle Placeholder */}
          {!result && !executing && !error && (
            <div className="bg-surface-card border border-surface-border rounded-xl p-10 text-center space-y-4">
              <div className="w-14 h-14 mx-auto rounded-xl bg-slate-900 border border-surface-border flex items-center justify-center">
                <SparklesIcon className="w-7 h-7 text-primary-400" />
              </div>
              <div className="max-w-md mx-auto">
                <h3 className="text-base font-semibold text-white">Intelligent Multi-Agent Router</h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Enter a task or load a quick sample on the left. The engine analyzes your intent and
                  routes execution directly to the specialized Research, Content, Data, or Reporting agent.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * Specialized renderer component dynamically tailoring presentation
 * to the schema of the routed agent.
 */
function AgentResultRenderer({ agentType, output }) {
  if (!output || Object.keys(output).length === 0) {
    return <p className="text-sm text-slate-400">No output data returned.</p>
  }

  // ── 1. Research Agent Renderer ──────────────────────────────────────────────
  if (agentType === 'research') {
    return (
      <div className="space-y-5">
        <div>
          <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider">
            Research Topic
          </span>
          <h2 className="text-lg font-bold text-white mt-1">{output.topic}</h2>
          <p className="text-sm text-slate-300 mt-2 bg-slate-900/60 p-3.5 rounded-lg border border-surface-border">
            {output.executive_summary}
          </p>
        </div>

        {/* Key Findings */}
        {output.key_findings?.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Key Findings
            </h4>
            <ul className="space-y-1.5">
              {output.key_findings.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-slate-200">
                  <span className="text-cyan-400 font-bold shrink-0">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Facts vs AI Projections Comparison Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          {/* Verified Facts */}
          <div className="p-3.5 rounded-lg bg-emerald-500/5 border border-emerald-500/20 space-y-2">
            <div className="flex items-center gap-1.5 text-emerald-400 text-xs font-semibold">
              <CheckCircleIcon className="w-4 h-4" />
              <span>Verified Facts (From Context)</span>
            </div>
            <ul className="space-y-1">
              {output.verified_facts?.map((fact, idx) => (
                <li key={idx} className="text-xs text-slate-300 flex items-start gap-1.5">
                  <span className="text-emerald-400 shrink-0">✓</span>
                  <span>{fact}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* AI Insights and Projections */}
          <div className="p-3.5 rounded-lg bg-cyan-500/5 border border-cyan-500/20 space-y-2">
            <div className="flex items-center gap-1.5 text-cyan-400 text-xs font-semibold">
              <SparklesIcon className="w-4 h-4" />
              <span>AI Insights & Projections</span>
            </div>
            <ul className="space-y-1">
              {output.ai_insights_and_projections?.map((item, idx) => (
                <li key={idx} className="text-xs text-slate-300 flex items-start gap-1.5">
                  <span className="text-cyan-400 shrink-0">✦</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* References */}
        {output.sources_or_references?.length > 0 && (
          <div className="pt-2 border-t border-surface-border text-xs text-slate-400">
            <span className="font-semibold text-slate-300">Cited Context / Sources: </span>
            {output.sources_or_references.join(', ')}
          </div>
        )}
      </div>
    )
  }

  // ── 2. Content Generation Agent Renderer ────────────────────────────────────
  if (agentType === 'content_generation') {
    return (
      <div className="space-y-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="px-2.5 py-1 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20 text-xs font-medium uppercase">
            {output.content_type || 'Article'}
          </span>
          <span className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 text-xs font-medium">
            Tone: {output.tone_used || 'Professional'}
          </span>
          {output.target_audience && (
            <span className="text-xs text-slate-400 flex items-center gap-1">
              <TagIcon className="w-3.5 h-3.5" /> {output.target_audience}
            </span>
          )}
        </div>

        <div>
          <h2 className="text-xl font-bold text-white">{output.title}</h2>
          <div className="mt-3 p-4 rounded-lg bg-slate-900 border border-surface-border text-sm text-slate-200 whitespace-pre-line leading-relaxed">
            {output.body}
          </div>
        </div>

        {/* Call to Action */}
        {output.call_to_action && (
          <div className="p-3 rounded-lg bg-violet-500/10 border border-violet-500/20 text-xs flex items-center gap-2">
            <span className="font-semibold text-violet-300">Call to Action:</span>
            <span className="text-slate-200">{output.call_to_action}</span>
          </div>
        )}

        {/* Alternative Headlines */}
        {output.alternative_headlines_or_hooks?.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Alternative Headlines & Hooks
            </h4>
            <ul className="space-y-1">
              {output.alternative_headlines_or_hooks.map((hook, i) => (
                <li key={i} className="text-xs text-slate-300 bg-slate-900/50 p-2 rounded border border-surface-border">
                  {hook}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    )
  }

  // ── 3. Data Analysis Agent Renderer ─────────────────────────────────────────
  if (agentType === 'data_analysis') {
    return (
      <div className="space-y-5">
        <div>
          <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
            Dataset Analysis
          </span>
          <p className="text-sm text-slate-200 mt-1 bg-slate-900 p-3 rounded-lg border border-surface-border">
            {output.dataset_overview}
          </p>
        </div>

        {/* Statistical Summary Grid */}
        {output.statistical_summary && Object.keys(output.statistical_summary).length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Calculated Metrics & Figures
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
              {Object.entries(output.statistical_summary).map(([k, v]) => (
                <div key={k} className="p-3 rounded-lg bg-slate-900/80 border border-surface-border">
                  <p className="text-[11px] text-slate-400 truncate capitalize">
                    {k.replace(/_/g, ' ')}
                  </p>
                  <p className="text-sm font-bold text-white mt-0.5">{String(v)}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Trends and Patterns */}
        {output.key_trends_and_patterns?.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Discovered Patterns & Trends
            </h4>
            <ul className="space-y-1.5">
              {output.key_trends_and_patterns.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                  <span className="text-emerald-400 font-bold shrink-0">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Anomalies and Recommendations */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {output.anomalies_or_outliers?.length > 0 && (
            <div className="p-3.5 rounded-lg bg-amber-500/5 border border-amber-500/20 space-y-1.5">
              <span className="text-amber-400 font-semibold text-xs flex items-center gap-1">
                <ExclamationTriangleIcon className="w-3.5 h-3.5" /> Anomalies & Outliers
              </span>
              <ul className="space-y-1">
                {output.anomalies_or_outliers.map((anom, i) => (
                  <li key={i} className="text-xs text-slate-300">
                    - {anom}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {output.data_backed_recommendations?.length > 0 && (
            <div className="p-3.5 rounded-lg bg-emerald-500/5 border border-emerald-500/20 space-y-1.5">
              <span className="text-emerald-400 font-semibold text-xs flex items-center gap-1">
                <CheckCircleIcon className="w-3.5 h-3.5" /> Data-Backed Recommendations
              </span>
              <ul className="space-y-1">
                {output.data_backed_recommendations.map((rec, i) => (
                  <li key={i} className="text-xs text-slate-300">
                    - {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    )
  }

  // ── 4. Reporting Agent Renderer ─────────────────────────────────────────────
  if (agentType === 'reporting') {
    return (
      <div className="space-y-5">
        <div>
          <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">
            Executive Report
          </span>
          <h2 className="text-xl font-bold text-white mt-1">{output.report_title}</h2>
          <div className="mt-2.5 p-3.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-xs text-slate-200 leading-relaxed">
            <span className="font-semibold text-indigo-300 block mb-1">Executive Summary</span>
            {output.executive_summary}
          </div>
        </div>

        {/* Key Findings */}
        {output.key_findings?.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Key Strategic Findings
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {output.key_findings.map((item, i) => (
                <div key={i} className="p-2.5 rounded-lg bg-slate-900 border border-surface-border text-xs text-slate-300">
                  {item}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Detailed Analysis Section */}
        {output.detailed_analysis && (
          <div>
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Detailed Analysis
            </h4>
            <div className="p-4 rounded-lg bg-slate-900/80 border border-surface-border text-xs text-slate-300 whitespace-pre-line leading-relaxed">
              {output.detailed_analysis}
            </div>
          </div>
        )}

        {/* Strategic Recommendations and Next Steps */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {output.strategic_recommendations?.length > 0 && (
            <div className="p-3.5 rounded-lg bg-slate-900 border border-surface-border space-y-1.5">
              <span className="text-indigo-400 font-semibold text-xs">
                Strategic Recommendations
              </span>
              <ul className="space-y-1">
                {output.strategic_recommendations.map((rec, i) => (
                  <li key={i} className="text-xs text-slate-300">
                    {i + 1}. {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {output.next_steps?.length > 0 && (
            <div className="p-3.5 rounded-lg bg-slate-900 border border-surface-border space-y-1.5">
              <span className="text-cyan-400 font-semibold text-xs">
                Tactical Milestones & Next Steps
              </span>
              <ul className="space-y-1">
                {output.next_steps.map((step, i) => (
                  <li key={i} className="text-xs text-slate-300">
                    → {step}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    )
  }

  // Fallback viewer
  return (
    <pre className="p-4 rounded-lg bg-slate-950 font-mono text-xs text-slate-300 overflow-x-auto">
      {JSON.stringify(output, null, 2)}
    </pre>
  )
}
