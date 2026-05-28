import { useEffect, useState } from 'react'
import './index.css'

type HealthStatus = 'loading' | 'ok' | 'error'

export default function App() {
  const [status, setStatus] = useState<HealthStatus>('loading')

  useEffect(() => {
    fetch('/health')
      .then((r) => r.json())
      .then((data) => setStatus(data.status === 'ok' ? 'ok' : 'error'))
      .catch(() => setStatus('error'))
  }, [])

  const badge: Record<HealthStatus, { label: string; color: string }> = {
    loading: { label: 'Checking…', color: 'bg-gray-200 text-gray-600' },
    ok: { label: 'API online', color: 'bg-green-100 text-green-700' },
    error: { label: 'API offline', color: 'bg-red-100 text-red-700' },
  }

  const { label, color } = badge[status]

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-3xl font-semibold tracking-tight" style={{ color: 'var(--accent)' }}>
        PaperTrail
      </h1>
      <span className={`rounded-full px-4 py-1 text-sm font-medium ${color}`}>
        {label}
      </span>
    </div>
  )
}
