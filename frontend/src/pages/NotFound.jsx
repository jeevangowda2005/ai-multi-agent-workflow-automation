import { Link } from 'react-router-dom'
import { ArrowLeftIcon } from '@heroicons/react/24/outline'

/** 404 Not Found page */
export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4 bg-surface text-slate-400 px-4">
      <span className="text-7xl font-bold text-slate-700">404</span>
      <h1 className="text-2xl font-semibold text-white">Page Not Found</h1>
      <p className="text-sm text-center max-w-sm">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link to="/dashboard" className="btn-primary mt-2">
        <ArrowLeftIcon className="w-4 h-4" />
        Back to Dashboard
      </Link>
    </div>
  )
}
