import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
  Handle,
  Position,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import {
  PencilSquareIcon,
  TrashIcon,
  PlusIcon,
  PlayIcon,
  ExclamationTriangleIcon,
  MagnifyingGlassIcon,
  DocumentTextIcon,
  ChartBarIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline'
import api from '@/services/api'
import Modal from '@/components/ui/Modal'

// Agent styling config
const AGENT_CONFIG = {
  research: {
    label: 'Research Agent',
    color: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
    icon: MagnifyingGlassIcon,
  },
  content_generation: {
    label: 'Content Gen Agent',
    color: 'border-purple-500/40 bg-purple-500/10 text-purple-400',
    icon: PencilSquareIcon,
  },
  data_analysis: {
    label: 'Data Analysis Agent',
    color: 'border-amber-500/40 bg-amber-500/10 text-amber-400',
    icon: ChartBarIcon,
  },
  reporting: {
    label: 'Reporting Agent',
    color: 'border-blue-500/40 bg-blue-500/10 text-blue-400',
    icon: DocumentTextIcon,
  },
  llm: {
    label: 'LLM Agent',
    color: 'border-indigo-500/40 bg-indigo-500/10 text-indigo-400',
    icon: CpuChipIcon,
  },
}

/**
 * Custom React Flow Task Node
 */
function CustomTaskNode({ data }) {
  const agentKey = data.agent_type || 'llm'
  const cfg = AGENT_CONFIG[agentKey] || AGENT_CONFIG.llm
  const IconComponent = cfg.icon

  return (
    <div className="w-64 rounded-xl border border-surface-border bg-surface-card shadow-2xl p-3.5 space-y-2 hover:border-primary-500/50 transition-colors">
      {/* Target input handle at top */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-primary-500 !border-2 !border-surface-card"
      />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="flex items-center justify-center w-5 h-5 rounded-md bg-surface text-[10px] font-mono font-semibold text-slate-400 border border-surface-border">
            #{data.order_index + 1}
          </span>
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium border ${cfg.color}`}
          >
            <IconComponent className="w-3 h-3" />
            {cfg.label}
          </span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation()
              data.onEdit(data.task)
            }}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-surface"
            title="Edit Task"
          >
            <PencilSquareIcon className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation()
              data.onDelete(data.task)
            }}
            className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-surface"
            title="Delete Task"
          >
            <TrashIcon className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div>
        <h4 className="text-xs font-semibold text-white truncate">{data.name}</h4>
        {data.input_data?.task_description && (
          <p className="text-[11px] text-slate-400 line-clamp-2 mt-0.5 leading-snug">
            {data.input_data.task_description}
          </p>
        )}
      </div>

      <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-surface-border">
        <span>Retries: {data.max_retries || 0}</span>
        <span>Timeout: {data.timeout_seconds || 60}s</span>
      </div>

      {/* Source output handle at bottom */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-primary-500 !border-2 !border-surface-card"
      />
    </div>
  )
}

/**
 * Main Visual Workflow Builder Component
 */
export default function VisualWorkflowBuilder({
  workflowId,
  tasks = [],
  onTasksUpdated,
  onRunWorkflow,
  isRunning = false,
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [builderError, setBuilderError] = useState(null)

  // Edit/Add Task Modal
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editingTask, setEditingTask] = useState(null)
  const [taskForm, setTaskForm] = useState({
    name: '',
    agent_type: 'research',
    order_index: 0,
    max_retries: 1,
    timeout_seconds: 60,
    prompt: '',
  })
  const [modalSubmitting, setModalSubmitting] = useState(false)

  // Confirm Delete Modal
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [taskToDelete, setTaskToDelete] = useState(null)

  const nodeTypes = useMemo(() => ({ customTask: CustomTaskNode }), [])

  // ── Handlers for Node Edit / Delete ──────────────────────────────────────
  const handleEditTask = useCallback((task) => {
    setEditingTask(task)
    setTaskForm({
      name: task.name,
      agent_type: task.agent_type || 'research',
      order_index: task.order_index ?? 0,
      max_retries: task.max_retries ?? 1,
      timeout_seconds: task.timeout_seconds ?? 60,
      prompt: task.input_data?.task_description || '',
    })
    setIsEditModalOpen(true)
  }, [])

  const handleDeleteTask = useCallback((task) => {
    setTaskToDelete(task)
    setIsDeleteModalOpen(true)
  }, [])

  // ── Sync Tasks to React Flow Nodes & Edges ───────────────────────────────
  useEffect(() => {
    // Sort tasks by order_index
    const sorted = [...tasks].sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0))

    const newNodes = sorted.map((task, idx) => {
      // Horizontal or vertical auto-stagger layout
      const x = 80 + (idx % 2 === 0 ? 0 : 40)
      const y = 50 + idx * 160

      return {
        id: String(task.id),
        type: 'customTask',
        position: { x, y },
        data: {
          task,
          name: task.name,
          order_index: task.order_index ?? idx,
          agent_type: task.agent_type,
          max_retries: task.max_retries,
          timeout_seconds: task.timeout_seconds,
          input_data: task.input_data || {},
          onEdit: handleEditTask,
          onDelete: handleDeleteTask,
        },
      }
    })

    const newEdges = []
    tasks.forEach((t) => {
      if (t.depends_on_task_id) {
        newEdges.push({
          id: `e-${t.depends_on_task_id}-${t.id}`,
          source: String(t.depends_on_task_id),
          target: String(t.id),
          animated: true,
          style: { stroke: '#3B82F6', strokeWidth: 2 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#3B82F6',
          },
        })
      }
    })

    setNodes(newNodes)
    setEdges(newEdges)
  }, [tasks, handleEditTask, handleDeleteTask, setNodes, setEdges])

  // ── Cycle / Circular Dependency Check ────────────────────────────────────
  const detectCycle = (sourceId, targetId, existingEdges) => {
    if (sourceId === targetId) return true

    const adj = {}
    existingEdges.forEach((e) => {
      adj[e.source] = adj[e.source] || []
      adj[e.source].push(e.target)
    })
    adj[sourceId] = adj[sourceId] || []
    adj[sourceId].push(targetId)

    const visited = new Set()
    const recStack = new Set()

    function dfs(node) {
      visited.add(node)
      recStack.add(node)
      for (const neighbor of adj[node] || []) {
        if (!visited.has(neighbor)) {
          if (dfs(neighbor)) return true
        } else if (recStack.has(neighbor)) {
          return true
        }
      }
      recStack.delete(node)
      return false
    }

    for (const node of Object.keys(adj)) {
      if (!visited.has(node)) {
        if (dfs(node)) return true
      }
    }
    return false
  }

  // ── Handle Connecting Edges ──────────────────────────────────────────────
  const onConnect = useCallback(
    async (params) => {
      const sourceTaskId = parseInt(params.source, 10)
      const targetTaskId = parseInt(params.target, 10)

      // Prevent self connection
      if (sourceTaskId === targetTaskId) return

      // Prevent circular dependency in DAG
      if (detectCycle(params.source, params.target, edges)) {
        setBuilderError(
          `Cannot connect: Circular dependency detected between Task #${sourceTaskId} and Task #${targetTaskId}.`
        )
        return
      }

      setBuilderError(null)

      try {
        // Save dependency in backend
        await api.updateTask(workflowId, targetTaskId, {
          depends_on_task_id: sourceTaskId,
        })

        // Add edge visually
        setEdges((eds) =>
          addEdge(
            {
              ...params,
              animated: true,
              style: { stroke: '#3B82F6', strokeWidth: 2 },
              markerEnd: { type: MarkerType.ArrowClosed, color: '#3B82F6' },
            },
            eds
          )
        )

        if (onTasksUpdated) onTasksUpdated()
      } catch (err) {
        setBuilderError(err.message || 'Failed to update task dependency.')
      }
    },
    [edges, workflowId, onTasksUpdated, setEdges]
  )

  // ── Open Add Task Modal ──────────────────────────────────────────────────
  const openAddTask = () => {
    setEditingTask(null)
    setTaskForm({
      name: '',
      agent_type: 'research',
      order_index: tasks.length,
      max_retries: 1,
      timeout_seconds: 60,
      prompt: '',
    })
    setIsEditModalOpen(true)
  }

  // ── Save Task (Create or Update) ─────────────────────────────────────────
  const handleSaveTaskSubmit = async (e) => {
    e.preventDefault()
    if (!taskForm.name.trim()) return

    try {
      setModalSubmitting(true)
      setBuilderError(null)

      if (editingTask) {
        // Update task
        await api.updateTask(workflowId, editingTask.id, {
          name: taskForm.name.trim(),
          agent_type: taskForm.agent_type,
          order_index: parseInt(taskForm.order_index, 10),
          max_retries: parseInt(taskForm.max_retries, 10),
          timeout_seconds: parseInt(taskForm.timeout_seconds, 10),
          input_data: {
            ...(editingTask.input_data || {}),
            task_description: taskForm.prompt.trim(),
          },
        })
      } else {
        // Create new task
        await api.createTask(workflowId, {
          name: taskForm.name.trim(),
          agent_type: taskForm.agent_type,
          order_index: parseInt(taskForm.order_index, 10),
          max_retries: parseInt(taskForm.max_retries, 10),
          timeout_seconds: parseInt(taskForm.timeout_seconds, 10),
          task_type: 'action',
          status: 'pending',
          input_data: {
            task_description: taskForm.prompt.trim(),
          },
        })
      }

      setIsEditModalOpen(false)
      if (onTasksUpdated) onTasksUpdated()
    } catch (err) {
      setBuilderError(err.message || 'Failed to save task configuration.')
    } finally {
      setModalSubmitting(false)
    }
  }

  // ── Confirm Delete Task ──────────────────────────────────────────────────
  const handleConfirmDelete = async () => {
    if (!taskToDelete) return
    try {
      setModalSubmitting(true)
      await api.deleteTask(workflowId, taskToDelete.id)
      setIsDeleteModalOpen(false)
      setTaskToDelete(null)
      if (onTasksUpdated) onTasksUpdated()
    } catch (err) {
      setBuilderError(err.message || 'Failed to delete task.')
    } finally {
      setModalSubmitting(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* ── Builder Action Toolbar ────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Interactive Canvas
          </span>
          <span className="text-xs text-slate-500">
            ({tasks.length} task nodes • drag handles to define dependencies)
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={openAddTask}
            className="btn-ghost border border-surface-border text-xs flex items-center gap-1.5"
          >
            <PlusIcon className="w-3.5 h-3.5" />
            Add Task Node
          </button>
          <button
            onClick={onRunWorkflow}
            disabled={isRunning || tasks.length === 0}
            className="btn-primary text-xs flex items-center gap-1.5"
          >
            <PlayIcon className="w-3.5 h-3.5" />
            {isRunning ? 'Running…' : 'Run Pipeline'}
          </button>
        </div>
      </div>

      {/* ── Error Banner ──────────────────────────────────────────────────── */}
      {builderError && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="w-4 h-4 shrink-0" />
            <span>{builderError}</span>
          </div>
          <button onClick={() => setBuilderError(null)} className="text-rose-400 hover:text-rose-200">
            ✕
          </button>
        </div>
      )}

      {/* ── React Flow Canvas ────────────────────────────────────────────── */}
      <div className="w-full h-[540px] rounded-2xl border border-surface-border bg-surface/30 overflow-hidden relative shadow-inner">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          className="bg-[#0B0F19]"
        >
          <Background color="#1E293B" gap={20} size={1.5} />
          <Controls className="!bg-surface-card !border !border-surface-border !text-slate-300" />
          <MiniMap
            nodeColor="#3B82F6"
            className="!bg-surface-card !border !border-surface-border !rounded-lg"
            maskColor="rgba(11, 15, 25, 0.7)"
          />
        </ReactFlow>
      </div>

      {/* ── Add / Edit Task Modal ────────────────────────────────────────── */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => !modalSubmitting && setIsEditModalOpen(false)}
        title={editingTask ? `Configure Task #${editingTask.id}` : 'Add New Task Node'}
      >
        <form onSubmit={handleSaveTaskSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Task Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Ingest Customer Data, Draft Report"
              value={taskForm.name}
              onChange={(e) => setTaskForm({ ...taskForm, name: e.target.value })}
              className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Assigned AI Agent
              </label>
              <select
                value={taskForm.agent_type}
                onChange={(e) => setTaskForm({ ...taskForm, agent_type: e.target.value })}
                className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              >
                <option value="research">Research Agent</option>
                <option value="content_generation">Content Generation Agent</option>
                <option value="data_analysis">Data Analysis Agent</option>
                <option value="reporting">Reporting Agent</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Execution Order Index
              </label>
              <input
                type="number"
                min="0"
                value={taskForm.order_index}
                onChange={(e) => setTaskForm({ ...taskForm, order_index: e.target.value })}
                className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Max Retries
              </label>
              <input
                type="number"
                min="0"
                max="5"
                value={taskForm.max_retries}
                onChange={(e) => setTaskForm({ ...taskForm, max_retries: e.target.value })}
                className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Timeout (seconds)
              </label>
              <input
                type="number"
                min="5"
                max="300"
                value={taskForm.timeout_seconds}
                onChange={(e) => setTaskForm({ ...taskForm, timeout_seconds: e.target.value })}
                className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Task Prompt / Instructions
            </label>
            <textarea
              rows={3}
              placeholder="Instructions provided to the assigned AI agent for this step"
              value={taskForm.prompt}
              onChange={(e) => setTaskForm({ ...taskForm, prompt: e.target.value })}
              className="w-full px-3 py-2 bg-surface border border-surface-border rounded-lg text-xs text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-surface-border">
            <button
              type="button"
              disabled={modalSubmitting}
              onClick={() => setIsEditModalOpen(false)}
              className="btn-ghost"
            >
              Cancel
            </button>
            <button type="submit" disabled={modalSubmitting} className="btn-primary">
              {modalSubmitting ? 'Saving…' : 'Save Node'}
            </button>
          </div>
        </form>
      </Modal>

      {/* ── Confirm Delete Task Modal ────────────────────────────────────── */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => !modalSubmitting && setIsDeleteModalOpen(false)}
        title="Delete Task Node"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-300">
            Are you sure you want to delete task{' '}
            <strong className="text-white">"{taskToDelete?.name}"</strong>?
          </p>
          <p className="text-xs text-amber-400">
            Any downstream tasks depending on this step will have their dependency reset.
          </p>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-surface-border">
            <button
              type="button"
              disabled={modalSubmitting}
              onClick={() => setIsDeleteModalOpen(false)}
              className="btn-ghost"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={modalSubmitting}
              onClick={handleConfirmDelete}
              className="px-4 py-2 rounded-lg bg-rose-600 text-white text-xs font-medium hover:bg-rose-500 transition-colors"
            >
              {modalSubmitting ? 'Deleting…' : 'Delete Task'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
