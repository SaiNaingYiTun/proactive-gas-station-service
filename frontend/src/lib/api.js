const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

// Mirrors backend/main.py's vehicle_visits row shape.
export async function fetchVisits({ limit = 50, status } = {}) {
  const params = new URLSearchParams()
  params.set('limit', limit)
  if (status) params.set('status', status)

  const response = await fetch(`${API_BASE}/api/visits?${params.toString()}`)
  if (!response.ok) {
    throw new Error(`Failed to load visits (${response.status})`)
  }
  return response.json()
}
