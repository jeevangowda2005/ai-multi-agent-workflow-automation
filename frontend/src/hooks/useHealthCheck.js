import { useState, useEffect } from 'react'
import api from '@/services/api'

/**
 * Polls the /api/health endpoint every 30 seconds and returns the current
 * backend health status.
 *
 * @returns {{ healthy: boolean, loading: boolean, error: string | null }}
 */
export default function useHealthCheck() {
  const [healthy, setHealthy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function check() {
      try {
        const data = await api.health()
        if (!cancelled) {
          setHealthy(data.status === 'healthy')
          setError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setHealthy(false)
          setError(err.message)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    check()
    const timer = setInterval(check, 30_000)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  return { healthy, loading, error }
}
