import { useEffect, useState } from 'react'

import { checkHealth } from './api.js'

// Shared by the sidebar's status panel and the header's badge so both reflect
// the same real check (see checkHealth) instead of two different hardcoded
// "online" claims that never actually tested anything.
export function useBackendHealth(intervalMs = 15000) {
  const [healthy, setHealthy] = useState(null)

  useEffect(() => {
    let cancelled = false
    function poll() {
      checkHealth().then((ok) => { if (!cancelled) setHealthy(ok) })
    }
    poll()
    const interval = setInterval(poll, intervalMs)
    return () => { cancelled = true; clearInterval(interval) }
  }, [intervalMs])

  return healthy
}
