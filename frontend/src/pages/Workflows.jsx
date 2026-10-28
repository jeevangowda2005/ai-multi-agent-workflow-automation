import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  PlusIcon,
  MagnifyingGlassIcon,
  Squares2X2Icon,
  ListBulletIcon,
  PencilSquareIcon,
  TrashIcon,
  ArrowRightIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  BoltIcon,
  CalendarIcon,
  QueueListIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import api from '@/services/api'
import StatusBadge from '@/components/ui/StatusBadge'
import Modal from '@/components/ui/Modal'

export default function Workflows() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [workflows, setWorkflows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [successMessage, setSuccessMessage] = useState(null)

  // Filters & display
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [viewMode, setViewMode] = useState('grid') // 'grid' | 'table'

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(searchParams.get('create') === 'true')
  const [editingWorkflow, setEditingWorkflow] = useState(null)
  const [deletingWorkflow, setDeletingWorkflow] = useState(null)
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false)
  const [templates, setTemplates] = useState([])
  const [instantiating, setInstantiating] = useState(false)

  // Form states
  const [formData, setFormData] = useState({ name: '', description: '', status: 'draft' })
  const [formSubmitting, setFormSubmitting] = useState(false)
  const [formError, setFormError] = useState(null)

  // Load templates on mount
  useEffect(() => {
    async function loadTemplates() {
      try {
        const tmpls = await api.listWorkflowTemplates()
        setTemplates(tmpls || [])
      } catch (err) {
        console.error('Failed to load templates:', err)
      }
    }
    loadTemplates()
  }, [])

  const handleInstantiateTemplate = async (templateId) => {
    try {
      setInstantiating(true)
      const newWf = await api.instantiateWorkflowTemplate(templateId)
      setIsTemplateModalOpen(false)
      navigate(`/workflows/${newWf.id}`)
    } catch (err) {
      setError(err.message || 'Failed to instantiate template')
    } finally {
      setInstantiating(false)
    }
  }

  // Fetch workflows
  const fetchWorkflows = async () => {
    try {
      setLoading(true)
      setError(null)
      const params = {}
      if (statusFilter !== 'all') params.status = statusFilter
      if (search.trim()) params.search = search.trim()

      const data = await api.listWorkflows(params)
      setWorkflows(data)
    } catch (err) {
      setError(err.message || 'Failed to load workflows')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchWorkflows()
    }, 200)
    return () => clearTimeout(timer)
  }, [statusFilter, search])

  // Clear query param after modal opened
  useEffect(() => {
    if (searchParams.get('create') === 'true') {
      setIsCreateOpen(true)
      searchParams.delete('create')
      setSearchParams(searchParams, { replace: true })
    }
  }, [searchParams])

  // Clear success notification after 4s
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 4000)
      return () => clearTimeout(timer)
    }
  }, [successMessage])

  // Handle Create
  const handleOpenCreate = () => {
    setFormData({ name: '', description: '', status: 'draft' })
    setFormError(null)
    setIsCreateOpen(true)
  }

  const handleCreateSubmit = async (e) => {
    e.preventDefault()
    if (!formData.name.trim()) {
      setFormError('Workflow name is required')
      return
    }
    try {
      setFormSubmitting(true)
      setFormError(null)
      const created = await api.createWorkflow(formData)
      setIsCreateOpen(false)
      setSuccessMessage(`Workflow "${created.name}" created successfully!`)
      fetchWorkflows()
    } catch (err) {
      setFormError(err.message || 'Failed to create workflow')
    } finally {
      setFormSubmitting(false)
    }
  }

  // Handle Edit
  const handleOpenEdit = (workflow) => {
    setEditingWorkflow(workflow)
    setFormData({
      name: workflow.name,
      description: workflow.description || '',
      status: workflow.status,
    })
    setFormError(null)
  }

  const handleEditSubmit = async (e) => {
    e.preventDefault()
    if (!formData.name.trim()) {
      setFormError('Workflow name is required')
      return
    }
    try {
      setFormSubmitting(true)
      setFormError(null)
      const updated = await api.updateWorkflow(editingWorkflow.id, formData)
      setEditingWorkflow(null)
      setSuccessMessage(`Workflow "${updated.name}" updated successfully!`)
      fetchWorkflows()
    } catch (err) {
      setFormError(err.message || 'Failed to update workflow')
    } finally {
      setFormSubmitting(false)
    }
  }

  // Handle Delete
  const handleDeleteConfirm = async () => {
    if (!deletingWorkflow) return
    try {
      setFormSubmitting(true)
      await api.deleteWorkflow(deletingWorkflow.id)
      setSuccessMessage(`Workflow "${deletingWorkflow.name}" deleted successfully.`)
      setDeletingWorkflow(null)
      fetchWorkflows()
    } catch (err) {
      setError(err.message || 'Failed to delete workflow')
    } finally {
      setFormSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* ── Top Feedback Alerts ──────────────────────────────────────────── */}
      {successMessage && (
        <div className="flex items-center justify-between p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-sm animate-in fade-in">
          <span>{successMessage}</span>
          <button onClick={() => setSuccessMessage(null)} className="text-emerald-400 hover:text-emerald-200">
            ✕
          </button>
        </div>
      )}

      {error && (
        <div className="flex items-center justify-between p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-sm">
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={fetchWorkflows} className="underline hover:no-underline text-xs">
            Retry
          </button>
        </div>
      )}

      {/* ── Action Header & Controls ─────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Workflows</h2>
          <p className="text-sm text-slate-400">
            Design, configure, and manage agentic automation pipelines.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsTemplateModalOpen(true)}
            className="btn-ghost border border-surface-border flex items-center gap-1.5 text-xs py-2 px-3"
          >
            <SparklesIcon className="w-4 h-4 text-primary-400" />
            Explore Templates
          </button>
          <button
            onClick={fetchWorkflows}
            title="Refresh workflows"
            className="p-2 rounded-lg bg-surface-card border border-surface-border text-slate-400 hover:text-white hover:bg-surface-border transition-colors"
          >
            <ArrowPathIcon className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button onClick={handleOpenCreate} className="btn-primary">
            <PlusIcon className="w-4 h-4" />
            Create Workflow
          </button>
        </div>
      </div>

      {/* ── Search, Filters & View Toggle ─────────────────────────────────── */}
      <div className="card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3 flex-1">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search workflows by name…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="draft">Draft</option>
            <option value="paused">Paused</option>
            <option value="archived">Archived</option>
          </select>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-1 border border-surface-border rounded-lg p-1 bg-surface self-end sm:self-auto">
          <button
            onClick={() => setViewMode('grid')}
            title="Grid view"
            className={`p-1.5 rounded ${
              viewMode === 'grid'
                ? 'bg-primary-600 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Squares2X2Icon className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('table')}
            title="Table view"
            className={`p-1.5 rounded ${
              viewMode === 'table'
                ? 'bg-primary-600 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <ListBulletIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ── Content Area: Loading / Empty / Grid / Table ──────────────────── */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((n) => (
            <div key={n} className="card p-5 space-y-4 animate-pulse">
              <div className="flex justify-between items-start">
                <div className="h-5 bg-surface-border rounded w-1/2" />
                <div className="h-4 bg-surface-border rounded w-16" />
              </div>
              <div className="h-10 bg-surface-border/50 rounded w-full" />
              <div className="pt-3 border-t border-surface-border flex justify-between">
                <div className="h-4 bg-surface-border rounded w-20" />
                <div className="h-4 bg-surface-border rounded w-24" />
              </div>
            </div>
          ))}
        </div>
      ) : workflows.length === 0 ? (
        <div className="card py-16 flex flex-col items-center justify-center text-center">
          <div className="w-16 h-16 rounded-2xl bg-primary-600/10 flex items-center justify-center mb-4 text-primary-400">
            <BoltIcon className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-semibold text-white">No workflows found</h3>
          <p className="mt-1 text-sm text-slate-400 max-w-sm">
            {search || statusFilter !== 'all'
              ? 'No workflows match your search or filter criteria.'
              : 'Get started by creating your first workflow to orchestrate automated tasks.'}
          </p>
          <button onClick={handleOpenCreate} className="btn-primary mt-6">
            <PlusIcon className="w-4 h-4" />
            Create Workflow
          </button>
        </div>
      ) : viewMode === 'grid' ? (
        /* Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {workflows.map((wf) => (
            <div
              key={wf.id}
              className="card flex flex-col justify-between hover:border-slate-600 transition-all duration-150 group"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <Link
                    to={`/workflows/${wf.id}`}
                    className="text-base font-semibold text-white group-hover:text-primary-400 transition-colors line-clamp-1"
                  >
                    {wf.name}
                  </Link>
                  <StatusBadge status={wf.status} />
                </div>
                <p className="mt-2 text-sm text-slate-400 line-clamp-2 min-h-[40px]">
                  {wf.description || 'No description provided.'}
                </p>
              </div>

              <div className="mt-5 pt-4 border-t border-surface-border space-y-3">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <QueueListIcon className="w-4 h-4 text-slate-500" />
                    {wf.tasks_count || 0} {wf.tasks_count === 1 ? 'task' : 'tasks'}
                  </span>
                  <span className="flex items-center gap-1">
                    <CalendarIcon className="w-4 h-4 text-slate-500" />
                    {new Date(wf.created_at).toLocaleDateString()}
                  </span>
                </div>

                <div className="flex items-center justify-between pt-1">
                  <Link
                    to={`/workflows/${wf.id}`}
                    className="inline-flex items-center gap-1 text-xs font-medium text-primary-400 hover:text-primary-300"
                  >
                    View Details
                    <ArrowRightIcon className="w-3.5 h-3.5" />
                  </Link>

                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleOpenEdit(wf)}
                      title="Edit workflow"
                      className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-border transition-colors"
                    >
                      <PencilSquareIcon className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setDeletingWorkflow(wf)}
                      title="Delete workflow"
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-surface-border transition-colors"
                    >
                      <TrashIcon className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Table View */
        <div className="card p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface text-xs uppercase text-slate-400 border-b border-surface-border">
                <tr>
                  <th className="px-6 py-3.5">Name</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Tasks</th>
                  <th className="px-6 py-3.5">Created</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {workflows.map((wf) => (
                  <tr key={wf.id} className="hover:bg-surface/50 transition-colors">
                    <td className="px-6 py-4">
                      <Link
                        to={`/workflows/${wf.id}`}
                        className="font-medium text-white hover:text-primary-400 transition-colors"
                      >
                        {wf.name}
                      </Link>
                      {wf.description && (
                        <p className="text-xs text-slate-400 mt-0.5 line-clamp-1 max-w-md">
                          {wf.description}
                        </p>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={wf.status} />
                    </td>
                    <td className="px-6 py-4 text-slate-300">
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-surface border border-surface-border text-xs">
                        {wf.tasks_count || 0}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-400">
                      {new Date(wf.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          to={`/workflows/${wf.id}`}
                          className="btn-ghost text-xs py-1 px-2.5"
                        >
                          View
                        </Link>
                        <button
                          onClick={() => handleOpenEdit(wf)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-border"
                        >
                          <PencilSquareIcon className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setDeletingWorkflow(wf)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-surface-border"
                        >
                          <TrashIcon className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Create Workflow Modal ────────────────────────────────────────── */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => !formSubmitting && setIsCreateOpen(false)}
        title="Create New Workflow"
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          {formError && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs">
              {formError}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Workflow Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Lead Qualification Pipeline"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Description
            </label>
            <textarea
              rows={3}
              placeholder="Brief description of the goals and triggers for this workflow…"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Initial Status
            </label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            >
              <option value="draft">Draft (in development)</option>
              <option value="active">Active (ready to execute)</option>
              <option value="paused">Paused (temporarily halted)</option>
            </select>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-surface-border">
            <button
              type="button"
              disabled={formSubmitting}
              onClick={() => setIsCreateOpen(false)}
              className="btn-ghost"
            >
              Cancel
            </button>
            <button type="submit" disabled={formSubmitting} className="btn-primary">
              {formSubmitting ? 'Creating…' : 'Create Workflow'}
            </button>
          </div>
        </form>
      </Modal>

      {/* ── Edit Workflow Modal ──────────────────────────────────────────── */}
      <Modal
        isOpen={Boolean(editingWorkflow)}
        onClose={() => !formSubmitting && setEditingWorkflow(null)}
        title="Edit Workflow"
      >
        <form onSubmit={handleEditSubmit} className="space-y-4">
          {formError && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs">
              {formError}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Workflow Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Description
            </label>
            <textarea
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Status
            </label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            >
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="archived">Archived</option>
            </select>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-surface-border">
            <button
              type="button"
              disabled={formSubmitting}
              onClick={() => setEditingWorkflow(null)}
              className="btn-ghost"
            >
              Cancel
            </button>
            <button type="submit" disabled={formSubmitting} className="btn-primary">
              {formSubmitting ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </Modal>

      {/* ── Delete Confirmation Modal ────────────────────────────────────── */}
      <Modal
        isOpen={Boolean(deletingWorkflow)}
        onClose={() => !formSubmitting && setDeletingWorkflow(null)}
        title="Delete Workflow"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-300">
            Are you sure you want to delete{' '}
            <strong className="text-white">"{deletingWorkflow?.name}"</strong>?
          </p>
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-amber-300 text-xs">
            ⚠️ This will permanently remove the workflow and all of its associated tasks and execution records.
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-surface-border">
            <button
              type="button"
              disabled={formSubmitting}
              onClick={() => setDeletingWorkflow(null)}
              className="btn-ghost"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={formSubmitting}
              onClick={handleDeleteConfirm}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-600 text-white text-sm font-medium hover:bg-rose-500 transition-colors"
            >
              {formSubmitting ? 'Deleting…' : 'Delete Permanently'}
            </button>
          </div>
        </div>
      </Modal>

      {/* ── Workflow Templates Gallery Modal ──────────────────────────────── */}
      <Modal
        isOpen={isTemplateModalOpen}
        onClose={() => !instantiating && setIsTemplateModalOpen(false)}
        title="Pre-Built Multi-Agent Workflow Templates"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-400">
            Select an enterprise-ready pipeline template to immediately instantiate configured task nodes, agent assignments, and inter-task dependencies.
          </p>

          <div className="space-y-3 pt-1">
            {templates.map((tmpl) => (
              <div
                key={tmpl.id}
                className="p-4 rounded-xl border border-surface-border bg-surface/50 hover:bg-surface hover:border-primary-500/40 transition-all space-y-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-semibold text-white">{tmpl.name}</h4>
                    <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                      {tmpl.description}
                    </p>
                  </div>
                  <button
                    onClick={() => handleInstantiateTemplate(tmpl.id)}
                    disabled={instantiating}
                    className="btn-primary shrink-0 text-xs py-1.5 px-3 flex items-center gap-1.5"
                  >
                    <SparklesIcon className="w-3.5 h-3.5" />
                    {instantiating ? 'Building…' : 'Use Template'}
                  </button>
                </div>

                {/* Steps Preview */}
                <div className="pt-2 border-t border-surface-border/60 flex flex-wrap gap-2 text-[10px]">
                  {tmpl.tasks.map((task, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface border border-surface-border font-mono text-slate-400"
                    >
                      <span className="text-primary-400">#{idx + 1}</span>
                      <span>{task.name}</span>
                      <span className="text-slate-500">({task.agent_type})</span>
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="flex justify-end pt-3 border-t border-surface-border">
            <button
              onClick={() => setIsTemplateModalOpen(false)}
              className="btn-ghost text-xs"
            >
              Close
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
