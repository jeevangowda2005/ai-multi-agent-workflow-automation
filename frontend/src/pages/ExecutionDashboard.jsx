import { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import {
  PlayIcon,
  StopIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  BoltIcon,
  CpuChipIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
  ChartBarIcon,
  PencilSquareIcon,
  MagnifyingGlassIcon,
  SignalIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import api, { getExecutionWebSocketUrl } from '@/services/api'
import StatusBadge from '@/components/ui/StatusBadge'

// Agent visual badge configuration
const AGENT_CONFIG = {
  research: {
    label: 'Research Agent',
    color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    icon: MagnifyingGlassIcon,
  },
  content_generation: {
    label: 'Content Generation Agent',
    color: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
    icon: PencilSquareIcon,
  },
  data_analysis: {
    label: 'Data Analysis Agent',
    color: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    icon: ChartBarIcon,
  },
  reporting: {
    label: 'Reporting Agent',
    color: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    icon: DocumentTextIcon,
  },
  llm: {
    label: 'LLM Agent',
    color: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
    icon: CpuChipIcon,
  },
}

export default function ExecutionDashboard() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialExecutionId = searchParams.get('execution_id')
  const initialWorkflowId = searchParams.get('workflow_id')

  // Data state
  const [workflows, setWorkflows] = useState([])
  const [selectedWorkflowId, setSelectedWorkflowId] = useState(
    initialWorkflowId ? parseInt(initialWorkflowId, 10) : ''
  )
  const [executionHistory, setExecutionHistory] = useState([])
  const [activeExecution, setActiveExecution] = useState(null)
  const [loadingWorkflows, setLoadingWorkflows] = useState(true)
  const [loadingExecution, setLoadingExecution] = useState(false)
  const [triggering, setTriggering] = useState(false)
  const [canceling, setCanceling] = useState(false)
  const [actionError, setActionError] = useState(null)
  const [expandedTasks, setExpandedTasks] = useState({})
  const [historyFilterStatus, setHistoryFilterStatus] = useState('all')
  const [historySearch, setHistorySearch] = useState('')

  // Real-time connection state
  const [connectionMode, setConnectionMode] = useState('idle') // 'ws' | 'polling' | 'idle'
  const wsRef = useRef(null)
  const pingIntervalRef = useRef(null)
  const pollIntervalRef = useRef(null)

  // ── Load available workflows on mount ───────────────────────────────────
  useEffect(() => {
    async function loadWorkflows() {
      try {
        setLoadingWorkflows(true)
        const res = await api.listWorkflows()
        const items = res.items || res || []
        setWorkflows(items)
        if (!selectedWorkflowId && items.length > 0) {
          setSelectedWorkflowId(items[0].id)
        }
      } catch (err) {
        console.error('Failed to load workflows', err)
      } finally {
        setLoadingWorkflows(false)
      }
    }
    loadWorkflows()
  }, [])

  // ── Load execution history whenever workflow changes ─────────────────────
  const loadHistory = useCallback(async (workflowId) => {
    if (!workflowId) return
    try {
      const res = await api.listWorkflowExecutions(workflowId)
      const list = res.items || res || []
      setExecutionHistory(list)
    } catch (err) {
      console.error('Failed to load workflow execution history', err)
    }
  }, [])

  useEffect(() => {
    if (selectedWorkflowId) {
      loadHistory(selectedWorkflowId)
    }
  }, [selectedWorkflowId, loadHistory])

  // ── Fetch single execution details ──────────────────────────────────────
  const fetchExecution = useCallback(async (executionId) => {
    try {
      setLoadingExecution(true)
      const exec = await api.getExecution(executionId)
      setActiveExecution(exec)
      if (exec.workflow_id && exec.workflow_id !== selectedWorkflowId) {
        setSelectedWorkflowId(exec.workflow_id)
      }
      return exec
    } catch (err) {
      console.error(`Failed to fetch execution ${executionId}`, err)
      setActionError(err.message || 'Failed to fetch execution details.')
      return null
    } finally {
      setLoadingExecution(false)
    }
  }, [selectedWorkflowId])

  // Initial load if query param present
  useEffect(() => {
    if (initialExecutionId) {
      fetchExecution(initialExecutionId)
    }
  }, [initialExecutionId, fetchExecution])

  // ── Toggle task card accordion ──────────────────────────────────────────
  const toggleTaskAccordion = (taskId) => {
    setExpandedTasks((prev) => ({
      ...prev,
      [taskId]: !prev[taskId],
    }))
  }

  // ── Setup WebSocket / Polling for Active Execution ──────────────────────
  useEffect(() => {
    if (!activeExecution?.id) {
      setConnectionMode('idle')
      return
    }

    const execId = activeExecution.id
    const isTerminal = ['completed', 'failed', 'canceled'].includes(
      activeExecution.status
    )

    // Stop previous sockets/timers
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
      pingIntervalRef.current = null
    }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }

    // If already terminal, we don't need real-time streaming
    if (isTerminal) {
      setConnectionMode('idle')
      return
    }

    // Attempt WebSocket connection
    let fallbackToPolling = false
    const wsUrl = getExecutionWebSocketUrl(execId)

    try {
      const socket = new WebSocket(wsUrl)
      wsRef.current = socket

      socket.onopen = () => {
        setConnectionMode('ws')
        // Keep-alive ping every 20s
        pingIntervalRef.current = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send('ping')
          }
        }, 20_000)
      }

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          handleWebSocketEvent(payload)
        } catch {
          // Plain text or ping/pong
        }
      }

      socket.onerror = () => {
        // Will trigger onclose and fallback
        fallbackToPolling = true
      }

      socket.onclose = () => {
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
          pingIntervalRef.current = null
        }
        // If closed while still running, switch to REST polling fallback
        if (fallbackToPolling || !['completed', 'failed', 'canceled'].includes(activeExecution?.status)) {
          startPollingFallback(execId)
        }
      }
    } catch {
      startPollingFallback(execId)
    }

    function startPollingFallback(id) {
      setConnectionMode('polling')
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)

      pollIntervalRef.current = setInterval(async () => {
        try {
          const updated = await api.getExecution(id)
          setActiveExecution(updated)
          if (['completed', 'failed', 'canceled'].includes(updated.status)) {
            clearInterval(pollIntervalRef.current)
            pollIntervalRef.current = null
            setConnectionMode('idle')
            if (updated.workflow_id) loadHistory(updated.workflow_id)
          }
        } catch (err) {
          console.warn('Polling error:', err)
        }
      }, 2000)
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current)
        pingIntervalRef.current = null
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
    }
  }, [activeExecution?.id, activeExecution?.status, loadHistory])

  // Handle incoming live websocket events
  const handleWebSocketEvent = (payload) => {
    const { event, execution, task_execution, error } = payload

    if (execution) {
      setActiveExecution(execution)
      if (['completed', 'failed', 'canceled'].includes(execution.status)) {
        if (execution.workflow_id) loadHistory(execution.workflow_id)
      }
    } else if (task_execution) {
      setActiveExecution((prev) => {
        if (!prev) return prev
        const existingList = prev.task_executions || []
        const exists = existingList.some((t) => t.id === task_execution.id)
        const updatedList = exists
          ? existingList.map((t) => (t.id === task_execution.id ? task_execution : t))
          : [...existingList, task_execution]

        // Auto expand if error
        if (task_execution.status === 'failed') {
          setExpandedTasks((e) => ({ ...e, [task_execution.task_id]: true }))
        }

        return {
          ...prev,
          task_executions: updatedList,
          completed_tasks:
            task_execution.status === 'completed'
              ? (prev.completed_tasks || 0) + 1
              : prev.completed_tasks,
        }
      })
    } else if (event === 'workflow_completed' || event === 'workflow_canceled') {
      if (activeExecution?.id) fetchExecution(activeExecution.id)
      if (selectedWorkflowId) loadHistory(selectedWorkflowId)
    } else if (event === 'task_failed' && error) {
      setActionError(`Task error: ${error}`)
    }
  }

  // ── Trigger Workflow Execution ──────────────────────────────────────────
  const handleRunWorkflow = async () => {
    if (!selectedWorkflowId) return
    try {
      setTriggering(true)
      setActionError(null)
      const newExecution = await api.executeWorkflow(selectedWorkflowId, {
        metadata: { triggered_by: 'Dashboard UI', trigger_source: 'manual' },
      })
      setActiveExecution(newExecution)
      setSearchParams({ execution_id: newExecution.id, workflow_id: selectedWorkflowId })
      loadHistory(selectedWorkflowId)
    } catch (err) {
      setActionError(err.message || 'Failed to start workflow execution.')
    } finally {
      setTriggering(false)
    }
  }

  // ── Cancel Active Execution ─────────────────────────────────────────────
  const handleCancelExecution = async () => {
    if (!activeExecution?.id) return
    try {
      setCanceling(true)
      setActionError(null)
      const res = await api.cancelExecution(activeExecution.id)
      setActiveExecution(res)
      loadHistory(selectedWorkflowId)
    } catch (err) {
      setActionError(err.message || 'Failed to cancel execution.')
    } finally {
      setCanceling(false)
    }
  }

  // Progress calculations
  const totalTasks = activeExecution?.total_tasks || 0
  const completedTasks = activeExecution?.completed_tasks || 0
  const progressPercent = totalTasks > 0 ? Math.min(100, Math.round((completedTasks / totalTasks) * 100)) : 0

  return (
    <div className="space-y-6">
      {/* ── Top Header Bar ──────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white">Workflow Execution Dashboard</h1>
            {connectionMode === 'ws' && (
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <SignalIcon className="w-3.5 h-3.5 animate-pulse" />
                Live WebSocket
              </span>
            )}
            {connectionMode === 'polling' && (
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <ArrowPathIcon className="w-3.5 h-3.5 animate-spin" />
                REST Polling Fallback
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time execution monitoring, sequential task routing, and agent lifecycle telemetry.
          </p>
        </div>

        {/* Workflow selector & Run button */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <select
              value={selectedWorkflowId}
              onChange={(e) => {
                const wid = parseInt(e.target.value, 10)
                setSelectedWorkflowId(wid)
                setSearchParams({ workflow_id: wid })
              }}
              disabled={loadingWorkflows || triggering}
              className="px-3 py-2 bg-surface-card border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            >
              {workflows.length === 0 ? (
                <option value="">No workflows available</option>
              ) : (
                workflows.map((wf) => (
                  <option key={wf.id} value={wf.id}>
                    {wf.name} (#{wf.id})
                  </option>
                ))
              )}
            </select>
          </div>

          <button
            onClick={handleRunWorkflow}
            disabled={triggering || !selectedWorkflowId || activeExecution?.status === 'running'}
            className="btn-primary"
            title="Execute workflow tasks sequentially"
          >
            {triggering ? (
              <>
                <ArrowPathIcon className="w-4 h-4 animate-spin" />
                Starting…
              </>
            ) : (
              <>
                <PlayIcon className="w-4 h-4" />
                Run Workflow
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── Error Banner ────────────────────────────────────────────────── */}
      {actionError && (
        <div className="flex items-center justify-between p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-sm">
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="w-5 h-5 shrink-0" />
            <span>{actionError}</span>
          </div>
          <button onClick={() => setActionError(null)} className="text-rose-400 hover:text-rose-200">
            ✕
          </button>
        </div>
      )}

      {/* ── Main Layout Grid ────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Active Execution Details & Timeline */}
        <div className="lg:col-span-2 space-y-6">
          {activeExecution ? (
            <div className="card space-y-6">
              {/* Execution Summary Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-surface-border">
                <div className="space-y-1">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-sm text-slate-400">
                      Execution #{activeExecution.id}
                    </span>
                    <StatusBadge status={activeExecution.status} />
                  </div>
                  <p className="text-xs text-slate-400">
                    Workflow:{' '}
                    <Link
                      to={`/workflows/${activeExecution.workflow_id}`}
                      className="text-primary-400 hover:underline font-medium"
                    >
                      {workflows.find((w) => w.id === activeExecution.workflow_id)?.name ||
                        `Workflow #${activeExecution.workflow_id}`}
                    </Link>
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {/* Cancel Execution Button */}
                  {['pending', 'running'].includes(activeExecution.status) && (
                    <button
                      onClick={handleCancelExecution}
                      disabled={canceling}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-600/20 text-rose-400 border border-rose-500/30 hover:bg-rose-600/30 text-xs font-medium transition-colors"
                    >
                      {canceling ? (
                        <ArrowPathIcon className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <StopIcon className="w-3.5 h-3.5" />
                      )}
                      Cancel Execution
                    </button>
                  )}

                  {/* Generate AI Report Button */}
                  {activeExecution.status === 'completed' && (
                    <Link
                      to={`/reports?execution_id=${activeExecution.id}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-600 text-white hover:bg-primary-500 text-xs font-medium transition-colors"
                    >
                      <SparklesIcon className="w-3.5 h-3.5" />
                      Generate AI Report
                    </Link>
                  )}
                </div>
              </div>

              {/* Progress Bar */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-300 font-medium">Task Progress</span>
                  <span className="text-slate-400 font-mono">
                    {completedTasks} / {totalTasks} Completed ({progressPercent}%)
                  </span>
                </div>
                <div className="w-full h-2.5 bg-surface rounded-full overflow-hidden border border-surface-border">
                  <div
                    className={`h-full transition-all duration-500 rounded-full ${
                      activeExecution.status === 'failed'
                        ? 'bg-rose-500'
                        : activeExecution.status === 'canceled'
                        ? 'bg-slate-500'
                        : 'bg-primary-500'
                    }`}
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>

              {/* Execution Metadata Pills */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-2.5 rounded-lg bg-surface border border-surface-border">
                  <p className="text-slate-500">Status</p>
                  <p className="font-semibold text-slate-200 capitalize mt-0.5">
                    {activeExecution.status}
                  </p>
                </div>
                <div className="p-2.5 rounded-lg bg-surface border border-surface-border">
                  <p className="text-slate-500">Started</p>
                  <p className="font-mono text-slate-200 mt-0.5">
                    {activeExecution.started_at
                      ? new Date(activeExecution.started_at).toLocaleTimeString()
                      : '—'}
                  </p>
                </div>
                <div className="p-2.5 rounded-lg bg-surface border border-surface-border">
                  <p className="text-slate-500">Completed</p>
                  <p className="font-mono text-slate-200 mt-0.5">
                    {activeExecution.completed_at
                      ? new Date(activeExecution.completed_at).toLocaleTimeString()
                      : '—'}
                  </p>
                </div>
                <div className="p-2.5 rounded-lg bg-surface border border-surface-border">
                  <p className="text-slate-500">Duration</p>
                  <p className="font-mono text-slate-200 mt-0.5">
                    {activeExecution.started_at && activeExecution.completed_at
                      ? `${(
                          (new Date(activeExecution.completed_at) -
                            new Date(activeExecution.started_at)) /
                          1000
                        ).toFixed(1)}s`
                      : activeExecution.started_at
                      ? 'In progress…'
                      : '—'}
                  </p>
                </div>
              </div>

              {/* Execution Error Banner (if workflow failed) */}
              {activeExecution.error_message && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs">
                  <p className="font-semibold mb-0.5">Execution Error:</p>
                  <p className="font-mono">{activeExecution.error_message}</p>
                </div>
              )}

              {/* Visual Execution Timeline */}
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white">Visual Execution Timeline</h3>
                  <span className="text-xs text-slate-400">
                    {activeExecution.task_executions?.length || 0} task steps recorded
                  </span>
                </div>

                {(!activeExecution.task_executions ||
                  activeExecution.task_executions.length === 0) && (
                  <div className="py-8 text-center text-xs text-slate-500 border border-dashed border-surface-border rounded-xl">
                    No task execution records yet. The engine is dispatching tasks…
                  </div>
                )}

                <div className="space-y-3">
                  {(activeExecution.task_executions || [])
                    .sort((a, b) => a.order_index - b.order_index)
                    .map((taskExec, idx) => {
                      const agentCfg =
                        AGENT_CONFIG[taskExec.agent_type] || AGENT_CONFIG.llm
                      const AgentIcon = agentCfg.icon
                      const isExpanded = !!expandedTasks[taskExec.task_id]

                      return (
                        <div
                          key={taskExec.id || idx}
                          className="rounded-xl border border-surface-border bg-surface/50 overflow-hidden"
                        >
                          {/* Task Step Card Header */}
                          <div
                            onClick={() => toggleTaskAccordion(taskExec.task_id)}
                            className="p-3.5 flex items-center justify-between cursor-pointer hover:bg-surface transition-colors"
                          >
                            <div className="flex items-center gap-3">
                              {/* Step indicator */}
                              <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-surface border border-surface-border text-xs font-mono font-semibold text-slate-300">
                                {taskExec.order_index + 1}
                              </div>

                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="text-sm font-medium text-slate-200">
                                    {taskExec.task_name}
                                  </span>
                                  <StatusBadge status={taskExec.status} />
                                </div>
                                <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                                  {/* AI Agent Badge */}
                                  <span
                                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-xs font-medium ${agentCfg.color}`}
                                  >
                                    <AgentIcon className="w-3.5 h-3.5" />
                                    {agentCfg.label}
                                  </span>

                                  {taskExec.retry_count > 0 && (
                                    <span className="text-amber-400">
                                      {taskExec.retry_count} retries
                                    </span>
                                  )}

                                  {taskExec.duration_seconds && (
                                    <span className="font-mono">
                                      {taskExec.duration_seconds.toFixed(2)}s
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>

                            <button className="text-slate-400 hover:text-white p-1">
                              {isExpanded ? (
                                <ChevronUpIcon className="w-4 h-4" />
                              ) : (
                                <ChevronDownIcon className="w-4 h-4" />
                              )}
                            </button>
                          </div>

                          {/* Accordion Content: Task Output & Error Details */}
                          {isExpanded && (
                            <div className="p-4 border-t border-surface-border bg-surface-card/60 space-y-3">
                              {taskExec.error_message && (
                                <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs">
                                  <span className="font-semibold">Task Error:</span>{' '}
                                  {taskExec.error_message}
                                </div>
                              )}

                              <div>
                                <p className="text-xs font-medium text-slate-400 mb-1">
                                  Task Output:
                                </p>
                                {taskExec.output_data &&
                                Object.keys(taskExec.output_data).length > 0 ? (
                                  <pre className="p-3 rounded-lg bg-surface border border-surface-border text-xs font-mono text-slate-300 overflow-x-auto max-h-60 leading-relaxed">
                                    {JSON.stringify(taskExec.output_data, null, 2)}
                                  </pre>
                                ) : (
                                  <p className="text-xs text-slate-500 italic">
                                    No output generated yet.
                                  </p>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })}
                </div>
              </div>
            </div>
          ) : (
            <div className="card py-16 flex flex-col items-center justify-center text-center">
              <BoltIcon className="w-12 h-12 text-slate-600 mb-3" />
              <h3 className="text-base font-semibold text-slate-200">No Execution Selected</h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1">
                Select a workflow above and click "Run Workflow", or choose an execution from the
                history list on the right.
              </p>
            </div>
          )}
        </div>

        {/* Right Column (1 Col): Execution History */}
        <div className="space-y-4">
          <div className="card space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-surface-border">
              <h3 className="text-sm font-semibold text-white">Execution History</h3>
              <button
                onClick={() => selectedWorkflowId && loadHistory(selectedWorkflowId)}
                title="Refresh history"
                className="p-1 rounded text-slate-400 hover:text-white"
              >
                <ArrowPathIcon className="w-4 h-4" />
              </button>
            </div>

            {/* Filter controls */}
            <div className="space-y-2">
              <input
                type="text"
                placeholder="Search execution #..."
                value={historySearch}
                onChange={(e) => setHistorySearch(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-surface border border-surface-border rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-primary-500/50"
              />
              <div className="flex rounded-lg bg-surface border border-surface-border p-0.5 text-[11px]">
                {['all', 'completed', 'failed', 'running'].map((st) => (
                  <button
                    key={st}
                    onClick={() => setHistoryFilterStatus(st)}
                    className={`flex-1 py-1 rounded capitalize transition-colors ${
                      historyFilterStatus === st
                        ? 'bg-primary-600 text-white font-medium'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>

            {(() => {
              const filteredHistory = executionHistory.filter((exec) => {
                const matchesStatus =
                  historyFilterStatus === 'all' || exec.status.toLowerCase() === historyFilterStatus
                const matchesSearch =
                  !historySearch.trim() ||
                  String(exec.id).includes(historySearch.trim())
                return matchesStatus && matchesSearch
              })

              if (filteredHistory.length === 0) {
                return (
                  <p className="py-6 text-center text-xs text-slate-500">
                    No executions match the filter criteria.
                  </p>
                )
              }

              return (
                <div className="space-y-2 max-h-[540px] overflow-y-auto pr-1">
                  {filteredHistory.map((exec) => {
                    const isSelected = activeExecution?.id === exec.id
                    return (
                      <div
                        key={exec.id}
                        onClick={() => fetchExecution(exec.id)}
                        className={`p-3 rounded-xl border cursor-pointer transition-colors ${
                          isSelected
                            ? 'border-primary-500/50 bg-primary-600/10'
                            : 'border-surface-border bg-surface/40 hover:bg-surface'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-mono text-xs font-semibold text-slate-200">
                            #{exec.id}
                          </span>
                          <StatusBadge status={exec.status} />
                        </div>
                        <div className="flex items-center justify-between text-xs text-slate-400 mt-2">
                          <span>
                            {exec.completed_tasks || 0}/{exec.total_tasks || 0} tasks
                          </span>
                          <span>
                            {exec.started_at
                              ? new Date(exec.started_at).toLocaleTimeString([], {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })
                              : '—'}
                          </span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )
            })()}
          </div>
        </div>
      </div>
    </div>
  )
}
