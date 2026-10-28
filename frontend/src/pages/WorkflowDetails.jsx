import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  ArrowLeftIcon,
  PlusIcon,
  PlayIcon,
  PencilSquareIcon,
  TrashIcon,
  ArrowPathIcon,
  ClockIcon,
  CpuChipIcon,
  CommandLineIcon,
  CodeBracketIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'
import api from '@/services/api'
import StatusBadge from '@/components/ui/StatusBadge'
import Modal from '@/components/ui/Modal'
import VisualWorkflowBuilder from '@/components/workflow/VisualWorkflowBuilder'

export default function WorkflowDetails() {
  const { id } = useParams()
  const navigate = useNavigate()

  const [workflow, setWorkflow] = useState(null)
  const [tasks, setTasks] = useState([])
  const [executions, setExecutions] = useState([])
  const [executing, setExecuting] = useState(false)
  const [taskViewMode, setTaskViewMode] = useState('visual') // 'visual' | 'table'
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [successMessage, setSuccessMessage] = useState(null)

  // Modals
  const [isAddTaskOpen, setIsAddTaskOpen] = useState(false)
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [isDeleteOpen, setIsDeleteOpen] = useState(false)
  const [modalSubmitting, setModalSubmitting] = useState(false)
  const [modalError, setModalError] = useState(null)

  // Forms state
  const [editForm, setEditForm] = useState({ name: '', description: '', status: 'draft' })
  const [taskForm, setTaskForm] = useState({
    name: '',
    task_type: 'action',
    status: 'pending',
    input_json: '{\n  "param": "value"\n}',
  })

  // Fetch workflow, tasks & recent executions
  const fetchWorkflowData = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.getWorkflow(id)
      setWorkflow(data)
      setTasks(data.tasks || [])
      setEditForm({
        name: data.name,
        description: data.description || '',
        status: data.status,
      })

      // Fetch executions history
      try {
        const execs = await api.listWorkflowExecutions(id)
        setExecutions(execs.items || execs || [])
      } catch {
        // Non-blocking if executions fail
      }
    } catch (err) {
      setError(err.message || `Failed to load workflow with ID ${id}`)
    } finally {
      setLoading(false)
    }
  }

  // Handle Run Workflow
  const handleRunWorkflow = async () => {
    try {
      setExecuting(true)
      setError(null)
      const newExec = await api.executeWorkflow(id, {
        metadata: { triggered_from: 'workflow_details' },
      })
      navigate(`/executions?execution_id=${newExec.id}&workflow_id=${id}`)
    } catch (err) {
      setError(err.message || 'Failed to start workflow execution.')
    } finally {
      setExecuting(false)
    }
  }

  useEffect(() => {
    fetchWorkflowData()
  }, [id])

  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 4000)
      return () => clearTimeout(timer)
    }
  }, [successMessage])

  // Handle Edit Workflow
  const handleEditSubmit = async (e) => {
    e.preventDefault()
    if (!editForm.name.trim()) {
      setModalError('Workflow name is required')
      return
    }
    try {
      setModalSubmitting(true)
      setModalError(null)
      const updated = await api.updateWorkflow(id, editForm)
      setWorkflow(updated)
      setIsEditOpen(false)
      setSuccessMessage('Workflow updated successfully!')
    } catch (err) {
      setModalError(err.message || 'Failed to update workflow')
    } finally {
      setModalSubmitting(false)
    }
  }

  // Handle Delete Workflow
  const handleDeleteConfirm = async () => {
    try {
      setModalSubmitting(true)
      await api.deleteWorkflow(id)
      navigate('/workflows')
    } catch (err) {
      setError(err.message || 'Failed to delete workflow')
      setModalSubmitting(false)
      setIsDeleteOpen(false)
    }
  }

  // Handle Add Task
  const handleAddTaskSubmit = async (e) => {
    e.preventDefault()
    if (!taskForm.name.trim()) {
      setModalError('Task name is required')
      return
    }

    let parsedInput = {}
    if (taskForm.input_json.trim()) {
      try {
        parsedInput = JSON.parse(taskForm.input_json)
      } catch (err) {
        setModalError('Invalid JSON in Input Data field. Please format as valid JSON.')
        return
      }
    }

    try {
      setModalSubmitting(true)
      setModalError(null)
      const newTask = await api.createTask(id, {
        name: taskForm.name.trim(),
        task_type: taskForm.task_type,
        status: taskForm.status,
        input_data: parsedInput,
        output_data: {},
      })
      setTasks((prev) => [...prev, newTask])
      setIsAddTaskOpen(false)
      setSuccessMessage(`Task "${newTask.name}" added successfully!`)
      // Reset form
      setTaskForm({
        name: '',
        task_type: 'action',
        status: 'pending',
        input_json: '{\n  "param": "value"\n}',
      })
    } catch (err) {
      setModalError(err.message || 'Failed to add task')
    } finally {
      setModalSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-6 bg-surface-border rounded w-48" />
        <div className="card p-6 space-y-4">
          <div className="h-8 bg-surface-border rounded w-1/3" />
          <div className="h-4 bg-surface-border/50 rounded w-2/3" />
        </div>
        <div className="card p-6 space-y-4">
          <div className="h-6 bg-surface-border rounded w-32" />
          <div className="h-24 bg-surface-border/40 rounded w-full" />
        </div>
      </div>
    )
  }

  if (error || !workflow) {
    return (
      <div className="card py-16 flex flex-col items-center justify-center text-center">
        <ExclamationTriangleIcon className="w-12 h-12 text-rose-400 mb-3" />
        <h3 className="text-lg font-semibold text-white">Workflow Not Found</h3>
        <p className="mt-1 text-sm text-slate-400 max-w-sm">
          {error || `Unable to find a workflow with ID ${id}.`}
        </p>
        <Link to="/workflows" className="btn-primary mt-6">
          <ArrowLeftIcon className="w-4 h-4" />
          Back to Workflows
        </Link>
      </div>
    )
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

      {/* ── Back Navigation & Title Bar ──────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <Link
            to="/workflows"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeftIcon className="w-3.5 h-3.5" />
            Back to Workflows
          </Link>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-white">{workflow.name}</h2>
            <StatusBadge status={workflow.status} />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchWorkflowData}
            title="Refresh details"
            className="p-2 rounded-lg bg-surface-card border border-surface-border text-slate-400 hover:text-white hover:bg-surface-border transition-colors"
          >
            <ArrowPathIcon className="w-5 h-5" />
          </button>
          <button
            onClick={() => setIsEditOpen(true)}
            className="btn-ghost border border-surface-border"
          >
            <PencilSquareIcon className="w-4 h-4" />
            Edit
          </button>
          <button
            onClick={() => setIsDeleteOpen(true)}
            className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-surface-border border border-surface-border transition-colors"
            title="Delete workflow"
          >
            <TrashIcon className="w-5 h-5" />
          </button>
          <button
            onClick={handleRunWorkflow}
            disabled={executing || tasks.length === 0}
            className="btn-primary"
            title={tasks.length === 0 ? "Add tasks before running workflow" : "Execute workflow tasks"}
          >
            {executing ? (
              <ArrowPathIcon className="w-4 h-4 animate-spin" />
            ) : (
              <PlayIcon className="w-4 h-4" />
            )}
            Run Workflow
          </button>
          <button onClick={() => setIsAddTaskOpen(true)} className="btn-ghost border border-surface-border">
            <PlusIcon className="w-4 h-4" />
            Add Task
          </button>
        </div>
      </div>

      {/* ── Overview & Metadata Card ─────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card md:col-span-2 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Workflow Description
          </h3>
          <p className="text-sm text-slate-300 leading-relaxed">
            {workflow.description || 'No description provided for this workflow.'}
          </p>
        </div>

        <div className="card space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Metadata
          </h3>
          <div className="space-y-2 text-xs text-slate-300">
            <div className="flex justify-between py-1 border-b border-surface-border">
              <span className="text-slate-400">Workflow ID</span>
              <span className="font-mono text-slate-200">#{workflow.id}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-surface-border">
              <span className="text-slate-400">Total Tasks</span>
              <span className="font-semibold text-primary-400">{tasks.length}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-surface-border">
              <span className="text-slate-400">Created At</span>
              <span>{new Date(workflow.created_at).toLocaleString()}</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Last Updated</span>
              <span>{new Date(workflow.updated_at).toLocaleString()}</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Associated Tasks Section (Visual Builder & Table View) ───────── */}
      <div className="card space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold text-white">Workflow Tasks & Pipeline Topology</h3>
            <p className="text-xs text-slate-400">
              Configure multi-agent steps, execution sequence, and structured input passing.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* View Mode Toggle */}
            <div className="flex rounded-lg bg-surface border border-surface-border p-0.5 text-xs">
              <button
                onClick={() => setTaskViewMode('visual')}
                className={`px-3 py-1 rounded-md transition-colors ${
                  taskViewMode === 'visual'
                    ? 'bg-primary-600 text-white font-medium'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Visual Builder
              </button>
              <button
                onClick={() => setTaskViewMode('table')}
                className={`px-3 py-1 rounded-md transition-colors ${
                  taskViewMode === 'table'
                    ? 'bg-primary-600 text-white font-medium'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Table View
              </button>
            </div>

            <button onClick={() => setIsAddTaskOpen(true)} className="btn-primary text-xs py-1.5 px-3">
              <PlusIcon className="w-4 h-4" />
              Add Task
            </button>
          </div>
        </div>

        {taskViewMode === 'visual' ? (
          <VisualWorkflowBuilder
            workflowId={workflow.id}
            tasks={tasks}
            onTasksUpdated={fetchWorkflowData}
            onRunWorkflow={handleRunWorkflow}
            isRunning={executing}
          />
        ) : tasks.length === 0 ? (
          <div className="py-12 border border-dashed border-surface-border rounded-xl flex flex-col items-center justify-center text-center">
            <div className="w-12 h-12 rounded-xl bg-primary-600/10 flex items-center justify-center mb-3 text-primary-400">
              <CommandLineIcon className="w-6 h-6" />
            </div>
            <p className="text-sm font-medium text-slate-200">No tasks defined yet</p>
            <p className="text-xs text-slate-500 max-w-sm mt-1">
              Define the first task to configure this workflow's execution steps.
            </p>
            <button
              onClick={() => setIsAddTaskOpen(true)}
              className="btn-ghost border border-surface-border text-xs mt-4"
            >
              <PlusIcon className="w-3.5 h-3.5" />
              Add First Task
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface text-xs uppercase text-slate-400 border-b border-surface-border">
                <tr>
                  <th className="px-4 py-3">Step</th>
                  <th className="px-4 py-3">Task Name</th>
                  <th className="px-4 py-3">Agent</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Input Parameters</th>
                  <th className="px-4 py-3 text-right">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {tasks.map((task, index) => (
                  <tr key={task.id} className="hover:bg-surface/50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">
                      #{task.order_index !== undefined ? task.order_index + 1 : index + 1}
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-200">
                      {task.name}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-surface border border-surface-border text-xs text-slate-300 font-mono capitalize">
                        {task.agent_type || task.task_type}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={task.status} />
                    </td>
                    <td className="px-4 py-3 text-xs max-w-xs">
                      {task.input_data && Object.keys(task.input_data).length > 0 ? (
                        <pre className="bg-surface p-2 rounded border border-surface-border font-mono text-xs text-slate-400 overflow-x-auto max-h-20">
                          {JSON.stringify(task.input_data, null, 2)}
                        </pre>
                      ) : (
                        <span className="text-slate-500 italic">None</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-slate-400">
                      {new Date(task.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Workflow Executions Section ──────────────────────────────────── */}
      <div className="card space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-white">Execution History</h3>
            <p className="text-xs text-slate-400">
              Recent runs of this workflow, sequential progress, and agent telemetry.
            </p>
          </div>
          <Link
            to={`/executions?workflow_id=${id}`}
            className="btn-ghost border border-surface-border text-xs py-1.5 px-3"
          >
            Open Execution Dashboard
          </Link>
        </div>

        {executions.length === 0 ? (
          <div className="py-8 border border-dashed border-surface-border rounded-xl flex flex-col items-center justify-center text-center">
            <p className="text-xs text-slate-400">No executions have been run for this workflow yet.</p>
            <button
              onClick={handleRunWorkflow}
              disabled={executing || tasks.length === 0}
              className="btn-primary text-xs mt-3 flex items-center gap-1.5"
            >
              <PlayIcon className="w-3.5 h-3.5" />
              Run Workflow Now
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface text-xs uppercase text-slate-400 border-b border-surface-border">
                <tr>
                  <th className="px-4 py-3">Execution ID</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Progress</th>
                  <th className="px-4 py-3">Started At</th>
                  <th className="px-4 py-3">Completed At</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {executions.map((exec) => (
                  <tr key={exec.id} className="hover:bg-surface/50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-200">
                      #{exec.id}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={exec.status} />
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-300">
                      {exec.completed_tasks || 0} / {exec.total_tasks || 0} tasks
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {exec.started_at ? new Date(exec.started_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {exec.completed_at ? new Date(exec.completed_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/executions?execution_id=${exec.id}&workflow_id=${id}`}
                        className="text-xs text-primary-400 hover:text-primary-300 font-medium"
                      >
                        View Live
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Add Task Modal ───────────────────────────────────────────────── */}
      <Modal
        isOpen={isAddTaskOpen}
        onClose={() => !modalSubmitting && setIsAddTaskOpen(false)}
        title="Add Task to Workflow"
      >
        <form onSubmit={handleAddTaskSubmit} className="space-y-4">
          {modalError && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs">
              {modalError}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Task Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Extract Entities, Validate Schema, Send Email"
              value={taskForm.name}
              onChange={(e) => setTaskForm({ ...taskForm, name: e.target.value })}
              className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Task Type
              </label>
              <select
                value={taskForm.task_type}
                onChange={(e) => setTaskForm({ ...taskForm, task_type: e.target.value })}
                className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              >
                <option value="action">Action</option>
                <option value="llm">LLM Reasoning</option>
                <option value="condition">Condition</option>
                <option value="webhook">Webhook</option>
                <option value="transform">Transform</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Initial Status
              </label>
              <select
                value={taskForm.status}
                onChange={(e) => setTaskForm({ ...taskForm, status: e.target.value })}
                className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              >
                <option value="pending">Pending</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Input Data (JSON format)
            </label>
            <textarea
              rows={4}
              value={taskForm.input_json}
              onChange={(e) => setTaskForm({ ...taskForm, input_json: e.target.value })}
              className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-xs font-mono text-slate-300 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-surface-border">
            <button
              type="button"
              disabled={modalSubmitting}
              onClick={() => setIsAddTaskOpen(false)}
              className="btn-ghost"
            >
              Cancel
            </button>
            <button type="submit" disabled={modalSubmitting} className="btn-primary">
              {modalSubmitting ? 'Adding…' : 'Add Task'}
            </button>
          </div>
        </form>
      </Modal>

      {/* ── Edit Workflow Modal ──────────────────────────────────────────── */}
      <Modal
        isOpen={isEditOpen}
        onClose={() => !modalSubmitting && setIsEditOpen(false)}
        title="Edit Workflow"
      >
        <form onSubmit={handleEditSubmit} className="space-y-4">
          {modalError && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs">
              {modalError}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Workflow Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={editForm.name}
              onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
              className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Description
            </label>
            <textarea
              rows={3}
              value={editForm.description}
              onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
              className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Status
            </label>
            <select
              value={editForm.status}
              onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
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
              disabled={modalSubmitting}
              onClick={() => setIsEditOpen(false)}
              className="btn-ghost"
            >
              Cancel
            </button>
            <button type="submit" disabled={modalSubmitting} className="btn-primary">
              {modalSubmitting ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </Modal>

      {/* ── Delete Confirmation Modal ────────────────────────────────────── */}
      <Modal
        isOpen={isDeleteOpen}
        onClose={() => !modalSubmitting && setIsDeleteOpen(false)}
        title="Delete Workflow"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-300">
            Are you sure you want to delete{' '}
            <strong className="text-white">"{workflow.name}"</strong>?
          </p>
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-amber-300 text-xs">
            ⚠️ This will delete this workflow and all {tasks.length} associated task(s) permanently.
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-surface-border">
            <button
              type="button"
              disabled={modalSubmitting}
              onClick={() => setIsDeleteOpen(false)}
              className="btn-ghost"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={modalSubmitting}
              onClick={handleDeleteConfirm}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-600 text-white text-sm font-medium hover:bg-rose-500 transition-colors"
            >
              {modalSubmitting ? 'Deleting…' : 'Delete Permanently'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
