import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  DocumentChartBarIcon,
  ArrowDownTrayIcon,
  SparklesIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ClipboardDocumentCheckIcon,
  DocumentTextIcon,
  CalendarIcon,
  ExclamationTriangleIcon,
  EyeIcon,
} from '@heroicons/react/24/outline'
import api from '@/services/api'
import Modal from '@/components/ui/Modal'

export default function Reports() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialReportId = searchParams.get('report_id')

  // State
  const [reports, setReports] = useState([])
  const [selectedReport, setSelectedReport] = useState(null)
  const [loadingList, setLoadingList] = useState(true)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState(null)
  const [copiedMd, setCopiedMd] = useState(false)
  const [viewMode, setViewMode] = useState('formatted') // 'formatted' | 'markdown'

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [workflows, setWorkflows] = useState([])
  const [executions, setExecutions] = useState([])
  const [modalWorkflowId, setModalWorkflowId] = useState('')
  const [modalExecutionId, setModalExecutionId] = useState('')
  const [modalTitle, setModalTitle] = useState('')
  const [modalNotes, setModalNotes] = useState('')
  const [modalError, setModalError] = useState(null)

  // ── Load Reports List ───────────────────────────────────────────────────
  const fetchReportsList = useCallback(async () => {
    try {
      setLoadingList(true)
      const list = await api.listReports()
      setReports(list)
      if (list.length > 0 && !selectedReport) {
        const targetId = initialReportId ? parseInt(initialReportId, 10) : list[0].id
        loadReportDetail(targetId)
      }
    } catch (err) {
      console.error('Failed to load reports:', err)
      setError(err.message || 'Failed to load report list.')
    } finally {
      setLoadingList(false)
    }
  }, [initialReportId])

  useEffect(() => {
    fetchReportsList()
  }, [fetchReportsList])

  // ── Load Single Report ──────────────────────────────────────────────────
  const loadReportDetail = async (id) => {
    try {
      setLoadingDetail(true)
      const detail = await api.getReport(id)
      setSelectedReport(detail)
      setSearchParams({ report_id: id })
    } catch (err) {
      console.error(`Failed to load report #${id}:`, err)
    } finally {
      setLoadingDetail(false)
    }
  }

  // ── Modal Workflows & Executions Loading ─────────────────────────────────
  const openGenerateModal = async () => {
    setIsModalOpen(true)
    setModalError(null)
    try {
      const wfList = await api.listWorkflows()
      const items = wfList.items || wfList || []
      setWorkflows(items)
      if (items.length > 0) {
        setModalWorkflowId(items[0].id)
        loadModalExecutions(items[0].id)
      }
    } catch (err) {
      setModalError('Failed to load workflows.')
    }
  }

  const loadModalExecutions = async (wfId) => {
    try {
      const execs = await api.listWorkflowExecutions(wfId)
      const list = execs.items || execs || []
      // Filter to completed or finished executions
      setExecutions(list)
      if (list.length > 0) {
        setModalExecutionId(list[0].id)
      } else {
        setModalExecutionId('')
      }
    } catch {
      setExecutions([])
    }
  }

  const handleModalWorkflowChange = (wfId) => {
    setModalWorkflowId(wfId)
    loadModalExecutions(wfId)
  }

  const handleGenerateSubmit = async (e) => {
    e.preventDefault()
    if (!modalExecutionId) {
      setModalError('Please select a completed execution to report on.')
      return
    }

    try {
      setGenerating(true)
      setModalError(null)
      const newReport = await api.generateReport({
        execution_id: parseInt(modalExecutionId, 10),
        title: modalTitle.trim() || undefined,
        notes: modalNotes.trim() || undefined,
      })

      setIsModalOpen(false)
      setSelectedReport(newReport)
      setModalTitle('')
      setModalNotes('')
      fetchReportsList()
    } catch (err) {
      setModalError(err.message || 'Report generation failed.')
    } finally {
      setGenerating(false)
    }
  }

  // ── Copy Markdown to Clipboard ──────────────────────────────────────────
  const handleCopyMarkdown = () => {
    if (!selectedReport?.raw_markdown) return
    navigator.clipboard.writeText(selectedReport.raw_markdown)
    setCopiedMd(true)
    setTimeout(() => setCopiedMd(false), 2500)
  }

  // ── Download PDF ────────────────────────────────────────────────────────
  const handleDownloadPdf = () => {
    if (!selectedReport?.id) return
    window.open(api.downloadReportPdfUrl(selectedReport.id), '_blank')
  }

  return (
    <div className="space-y-6">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">AI Reports & Executive Intelligence</h1>
          <p className="text-xs text-slate-400 mt-1">
            Automated intelligence briefings, strategic insights, task outcomes, and publication-ready PDF exports.
          </p>
        </div>

        <button
          onClick={openGenerateModal}
          className="btn-primary text-xs flex items-center gap-1.5"
        >
          <SparklesIcon className="w-4 h-4" />
          Generate AI Report
        </button>
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

      {/* ── Main Layout: Sidebar & Document Viewer ───────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (1 Col): Reports List */}
        <div className="space-y-4">
          <div className="card space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-surface-border">
              <h3 className="text-sm font-semibold text-white">Generated Reports</h3>
              <button
                onClick={fetchReportsList}
                title="Refresh reports"
                className="p-1 rounded text-slate-400 hover:text-white"
              >
                <ArrowPathIcon className={`w-4 h-4 ${loadingList ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {loadingList ? (
              <div className="space-y-2 animate-pulse">
                {[1, 2, 3].map((n) => (
                  <div key={n} className="h-20 bg-surface rounded-xl" />
                ))}
              </div>
            ) : reports.length === 0 ? (
              <div className="py-10 text-center text-xs text-slate-500 space-y-2">
                <DocumentChartBarIcon className="w-10 h-10 mx-auto text-slate-600" />
                <p>No AI reports generated yet.</p>
                <button
                  onClick={openGenerateModal}
                  className="btn-ghost border border-surface-border text-xs mt-2"
                >
                  Generate First Report
                </button>
              </div>
            ) : (
              <div className="space-y-2 max-h-[680px] overflow-y-auto pr-1">
                {reports.map((r) => {
                  const isSelected = selectedReport?.id === r.id
                  return (
                    <div
                      key={r.id}
                      onClick={() => loadReportDetail(r.id)}
                      className={`p-3 rounded-xl border cursor-pointer transition-colors ${
                        isSelected
                          ? 'border-primary-500/50 bg-primary-600/10'
                          : 'border-surface-border bg-surface/40 hover:bg-surface'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="text-xs font-semibold text-slate-200 line-clamp-1">
                          {r.title}
                        </h4>
                        <span className="font-mono text-[10px] text-slate-500">#{r.id}</span>
                      </div>
                      <p className="text-[11px] text-slate-400 line-clamp-2 mt-1">
                        {r.executive_summary}
                      </p>
                      <div className="flex items-center justify-between text-[10px] text-slate-500 mt-2">
                        <span>{r.workflow_name}</span>
                        <span>{new Date(r.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Column (2 Cols): Active Report Document Viewer */}
        <div className="lg:col-span-2 space-y-6">
          {selectedReport ? (
            <div className="card space-y-6">
              {/* Document Action Bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-surface-border">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-slate-400">
                      Report #{selectedReport.id}
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-primary-500/10 text-primary-400 border border-primary-500/20">
                      Execution #{selectedReport.execution_id}
                    </span>
                  </div>
                  <h2 className="text-xl font-bold text-white">{selectedReport.title}</h2>
                  <p className="text-xs text-slate-400">
                    Workflow: <span className="text-slate-300 font-medium">{selectedReport.workflow_name}</span> | Generated:{' '}
                    {new Date(selectedReport.created_at).toLocaleString()}
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {/* View mode toggle */}
                  <div className="flex rounded-lg bg-surface border border-surface-border p-0.5 text-xs">
                    <button
                      onClick={() => setViewMode('formatted')}
                      className={`px-2.5 py-1 rounded-md transition-colors ${
                        viewMode === 'formatted'
                          ? 'bg-primary-600 text-white font-medium'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Briefing
                    </button>
                    <button
                      onClick={() => setViewMode('markdown')}
                      className={`px-2.5 py-1 rounded-md transition-colors ${
                        viewMode === 'markdown'
                          ? 'bg-primary-600 text-white font-medium'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Markdown
                    </button>
                  </div>

                  <button
                    onClick={handleCopyMarkdown}
                    className="p-2 rounded-lg bg-surface border border-surface-border text-slate-400 hover:text-white transition-colors"
                    title="Copy Markdown"
                  >
                    {copiedMd ? (
                      <CheckCircleIcon className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <ClipboardDocumentCheckIcon className="w-4 h-4" />
                    )}
                  </button>

                  <button
                    onClick={handleDownloadPdf}
                    className="btn-primary text-xs flex items-center gap-1.5 py-1.5"
                    title="Download binary PDF document"
                  >
                    <ArrowDownTrayIcon className="w-4 h-4" />
                    Download PDF
                  </button>
                </div>
              </div>

              {/* View Mode 1: Formatted Executive Briefing */}
              {viewMode === 'formatted' && (
                <div className="space-y-6">
                  {/* Executive Summary Card */}
                  <div className="p-4 rounded-xl bg-surface border border-surface-border space-y-1.5">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-primary-400">
                      Executive Summary
                    </h3>
                    <p className="text-sm text-slate-200 leading-relaxed">
                      {selectedReport.executive_summary}
                    </p>
                  </div>

                  {/* Key Findings */}
                  {selectedReport.findings && selectedReport.findings.length > 0 && (
                    <div className="space-y-3">
                      <h3 className="text-sm font-semibold text-white">
                        Key Findings & Analytical Insights
                      </h3>
                      <div className="space-y-2">
                        {selectedReport.findings.map((item, idx) => (
                          <div
                            key={idx}
                            className="p-3 rounded-lg bg-surface/50 border border-surface-border flex items-start gap-2.5 text-xs text-slate-300"
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-primary-400 mt-1.5 shrink-0" />
                            <span>{item}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Strategic Recommendations */}
                  {selectedReport.recommendations && selectedReport.recommendations.length > 0 && (
                    <div className="space-y-3">
                      <h3 className="text-sm font-semibold text-white">
                        Strategic Recommendations
                      </h3>
                      <div className="space-y-2">
                        {selectedReport.recommendations.map((rec, idx) => (
                          <div
                            key={idx}
                            className="p-3 rounded-lg bg-surface/50 border border-surface-border flex items-start gap-3 text-xs text-slate-300"
                          >
                            <span className="flex items-center justify-center w-5 h-5 rounded-full bg-primary-600/20 text-primary-400 font-semibold text-[11px] shrink-0">
                              {idx + 1}
                            </span>
                            <span className="pt-0.5">{rec}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Roadmap & Next Steps */}
                  {selectedReport.next_steps && selectedReport.next_steps.length > 0 && (
                    <div className="space-y-3">
                      <h3 className="text-sm font-semibold text-white">Roadmap & Next Steps</h3>
                      <div className="space-y-1.5">
                        {selectedReport.next_steps.map((step, idx) => (
                          <div
                            key={idx}
                            className="p-2.5 rounded-lg bg-surface/30 border border-surface-border flex items-center gap-2 text-xs text-slate-300"
                          >
                            <CheckCircleIcon className="w-4 h-4 text-emerald-400 shrink-0" />
                            <span>{step}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Detailed Analysis (if available) */}
                  {selectedReport.detailed_analysis && (
                    <div className="space-y-2 pt-2">
                      <h3 className="text-sm font-semibold text-white">Detailed Analysis</h3>
                      <div className="p-4 rounded-xl bg-surface/40 border border-surface-border text-xs text-slate-300 space-y-2 leading-relaxed">
                        {selectedReport.detailed_analysis.split('\n\n').map((para, i) => (
                          <p key={i}>{para}</p>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Task Execution Outcomes Telemetry */}
                  {selectedReport.task_outcomes && selectedReport.task_outcomes.length > 0 && (
                    <div className="space-y-3 pt-2">
                      <h3 className="text-sm font-semibold text-white">
                        Execution Telemetry Audit
                      </h3>
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-surface text-[10px] uppercase text-slate-400 border-b border-surface-border">
                            <tr>
                              <th className="px-3 py-2">Step</th>
                              <th className="px-3 py-2">Task</th>
                              <th className="px-3 py-2">Agent</th>
                              <th className="px-3 py-2">Status</th>
                              <th className="px-3 py-2 text-right">Duration</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-surface-border">
                            {selectedReport.task_outcomes.map((t, idx) => (
                              <tr key={idx} className="hover:bg-surface/50">
                                <td className="px-3 py-2 font-mono text-slate-500">#{idx + 1}</td>
                                <td className="px-3 py-2 font-medium text-slate-200">
                                  {t.task_name}
                                </td>
                                <td className="px-3 py-2 capitalize text-slate-300">
                                  {t.agent_type}
                                </td>
                                <td className="px-3 py-2">
                                  <span className="text-emerald-400 font-medium capitalize">
                                    {t.status}
                                  </span>
                                </td>
                                <td className="px-3 py-2 text-right font-mono text-slate-400">
                                  {t.duration_seconds ? `${t.duration_seconds.toFixed(2)}s` : '—'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* View Mode 2: Raw Markdown Editor/Viewer */}
              {viewMode === 'markdown' && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>Raw Markdown Export</span>
                    <button
                      onClick={handleCopyMarkdown}
                      className="text-primary-400 hover:text-primary-300 font-medium"
                    >
                      {copiedMd ? 'Copied!' : 'Copy to Clipboard'}
                    </button>
                  </div>
                  <pre className="p-4 rounded-xl bg-surface border border-surface-border text-xs font-mono text-slate-300 overflow-x-auto max-h-[600px] leading-relaxed whitespace-pre-wrap">
                    {selectedReport.raw_markdown}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="card py-20 flex flex-col items-center justify-center text-center">
              <DocumentChartBarIcon className="w-12 h-12 text-slate-600 mb-3" />
              <h3 className="text-base font-semibold text-slate-200">No Report Selected</h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1">
                Select a report from the list on the left, or click "Generate AI Report" to create a
                briefing from a completed workflow execution.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ── Generate Report Modal ────────────────────────────────────────── */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => !generating && setIsModalOpen(false)}
        title="Generate AI Executive Report"
      >
        <form onSubmit={handleGenerateSubmit} className="space-y-4">
          {modalError && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs">
              {modalError}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Select Workflow
            </label>
            <select
              value={modalWorkflowId}
              onChange={(e) => handleModalWorkflowChange(e.target.value)}
              className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            >
              {workflows.map((wf) => (
                <option key={wf.id} value={wf.id}>
                  {wf.name} (#{wf.id})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Select Completed Execution <span className="text-rose-400">*</span>
            </label>
            <select
              required
              value={modalExecutionId}
              onChange={(e) => setModalExecutionId(e.target.value)}
              className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            >
              {executions.length === 0 ? (
                <option value="">No executions found for this workflow</option>
              ) : (
                executions.map((exec) => (
                  <option key={exec.id} value={exec.id}>
                    Execution #{exec.id} — Status: {exec.status} ({exec.completed_tasks || 0}/{exec.total_tasks || 0} tasks)
                  </option>
                ))
              )}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Custom Report Title (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. Q4 Executive Intelligence Briefing"
              value={modalTitle}
              onChange={(e) => setModalTitle(e.target.value)}
              className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Stakeholder Focus Notes (Optional)
            </label>
            <textarea
              rows={3}
              placeholder="e.g. Highlight risk factors, customer retention metrics, and budget impact"
              value={modalNotes}
              onChange={(e) => setModalNotes(e.target.value)}
              className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-surface-border">
            <button
              type="button"
              disabled={generating}
              onClick={() => setIsModalOpen(false)}
              className="btn-ghost"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={generating || !modalExecutionId}
              className="btn-primary flex items-center gap-2"
            >
              {generating ? (
                <>
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                  Synthesizing with Reporting Agent…
                </>
              ) : (
                <>
                  <SparklesIcon className="w-4 h-4" />
                  Generate Report
                </>
              )}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
