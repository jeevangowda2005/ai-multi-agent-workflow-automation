import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from '@/components/layout/AppLayout'
import Dashboard from '@/pages/Dashboard'
import Workflows from '@/pages/Workflows'
import WorkflowDetails from '@/pages/WorkflowDetails'
import AiAnalyzer from '@/pages/AiAnalyzer'
import AgentWorkspace from '@/pages/AgentWorkspace'
import ExecutionDashboard from '@/pages/ExecutionDashboard'
import Reports from '@/pages/Reports'
import NotFound from '@/pages/NotFound'

/**
 * Root application component.
 * Defines top-level routing structure.
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* All authenticated pages share the main layout */}
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="workflows" element={<Workflows />} />
          <Route path="workflows/:id" element={<WorkflowDetails />} />
          <Route path="ai-analyzer" element={<AiAnalyzer />} />
          <Route path="agents" element={<AgentWorkspace />} />
          <Route path="executions" element={<ExecutionDashboard />} />
          <Route path="executions/:id" element={<ExecutionDashboard />} />
          <Route path="reports" element={<Reports />} />

          {/* Placeholder routes — implement in future steps */}
          <Route path="settings"   element={<ComingSoon title="Settings" />} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}

/** Temporary placeholder page for unimplemented routes */
function ComingSoon({ title }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-400">
      <span className="text-5xl">🚧</span>
      <h2 className="text-2xl font-semibold text-slate-200">{title}</h2>
      <p className="text-sm">This section will be implemented in a future step.</p>
    </div>
  )
}
