import axios from 'axios'

/**
 * Configured Axios instance.
 * Base URL is taken from the VITE_API_BASE_URL env var (defaults to relative empty
 * string so Vite proxy forwards /api to http://localhost:8000).
 */
const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// ── Request interceptor (attach auth token when available) ─────────────────
axiosInstance.interceptors.request.use((config) => {
  return config
})

// ── Response interceptor (uniform error handling) ──────────────────────────
axiosInstance.interceptors.response.use(
  (response) => response.data,
  (error) => {
    let message = 'An unexpected error occurred'
    if (error?.response?.data) {
      const data = error.response.data
      if (typeof data.detail === 'string') {
        message = data.detail
      } else if (Array.isArray(data.detail)) {
        // Pydantic validation error list
        message = data.detail.map((err) => `${err.loc?.slice(-1)[0]}: ${err.msg}`).join(', ')
      } else if (data.message) {
        message = data.message
      }
    } else if (error?.message) {
      message = error.message
    }
    return Promise.reject(new Error(message))
  },
)

/** Typed API client for FastAPI backend */
const api = {
  // System
  health: () => axiosInstance.get('/api/health'),

  // Workflows
  listWorkflows: (params = {}) => axiosInstance.get('/api/workflows', { params }),
  getWorkflow: (id) => axiosInstance.get(`/api/workflows/${id}`),
  createWorkflow: (data) => axiosInstance.post('/api/workflows', data),
  updateWorkflow: (id, data) => axiosInstance.put(`/api/workflows/${id}`, data),
  deleteWorkflow: (id) => axiosInstance.delete(`/api/workflows/${id}`),

  // Tasks
  listTasks: (workflowId) => axiosInstance.get(`/api/workflows/${workflowId}/tasks`),
  createTask: (workflowId, data) => axiosInstance.post(`/api/workflows/${workflowId}/tasks`, data),
  updateTask: (workflowId, taskId, data) =>
    axiosInstance.put(`/api/workflows/${workflowId}/tasks/${taskId}`, data),
  deleteTask: (workflowId, taskId) =>
    axiosInstance.delete(`/api/workflows/${workflowId}/tasks/${taskId}`),

  // Workflow Templates
  listWorkflowTemplates: () => axiosInstance.get('/api/workflows/templates'),
  instantiateWorkflowTemplate: (templateId, params = {}) =>
    axiosInstance.post(`/api/workflows/templates/${templateId}/instantiate`, null, { params }),

  // AI Agent & Gemini Integration
  getAiHealth: () => axiosInstance.get('/api/ai/health'),
  analyzeTask: (data) =>
    axiosInstance.post('/api/ai/analyze', data, {
      timeout: 60_000, // 60s timeout for agent LLM execution
    }),

  // Multi-Agent System (Step 4)
  listAgents: () => axiosInstance.get('/api/agents'),
  executeAgentTask: (data) =>
    axiosInstance.post('/api/agents/execute', data, {
      timeout: 60_000,
    }),
  getAgentExecution: (id) => axiosInstance.get(`/api/agents/executions/${id}`),
  listAgentExecutions: (params = {}) =>
    axiosInstance.get('/api/agents/executions', { params }),

  // Step 5: Automated Workflow Executions
  executeWorkflow: (workflowId, data = {}) =>
    axiosInstance.post(`/api/workflows/${workflowId}/execute`, data),
  listWorkflowExecutions: (workflowId, params = {}) =>
    axiosInstance.get(`/api/workflows/${workflowId}/executions`, { params }),
  getExecution: (executionId) => axiosInstance.get(`/api/executions/${executionId}`),
  cancelExecution: (executionId) => axiosInstance.post(`/api/executions/${executionId}/cancel`),
  listExecutions: (params = {}) => axiosInstance.get('/api/executions', { params }),

  // Step 6: Analytics & AI Reports
  getAnalyticsOverview: () => axiosInstance.get('/api/analytics/overview'),
  getAnalyticsTrends: (params = {}) =>
    axiosInstance.get('/api/analytics/trends', { params }),
  getAnalyticsAgents: () => axiosInstance.get('/api/analytics/agents'),
  generateReport: (data) => axiosInstance.post('/api/reports/generate', data),
  listReports: (params = {}) => axiosInstance.get('/api/reports', { params }),
  getReport: (id) => axiosInstance.get(`/api/reports/${id}`),
  downloadReportPdfUrl: (id) => {
    const base = import.meta.env.VITE_API_BASE_URL ?? ''
    return `${base}/api/reports/${id}/download`
  },
}

export function getExecutionWebSocketUrl(executionId) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const baseUrl = import.meta.env.VITE_API_BASE_URL
  if (baseUrl) {
    try {
      const url = new URL(baseUrl)
      const wsProto = url.protocol === 'https:' ? 'wss:' : 'ws:'
      return `${wsProto}//${url.host}/api/ws/executions/${executionId}`
    } catch {
      // Fallback if relative or invalid URL
    }
  }
  return `${protocol}//${window.location.host}/api/ws/executions/${executionId}`
}

export default api
