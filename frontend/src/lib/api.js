import { API_BASE, authFetch } from './auth.js'

// Mirrors backend/main.py's vehicle_visits row shape.
export async function fetchVisits({ limit = 50, status } = {}) {
  const params = new URLSearchParams()
  params.set('limit', limit)
  if (status) params.set('status', status)
  return authFetch(`/api/visits?${params.toString()}`)
}

// The real health check this replaces a hardcoded "System Online" badge
// with -- unauthenticated on the backend, so it still works to show "the
// backend is down" even when nobody can log in. Never throws: a failed
// fetch (backend unreachable at all) is reported the same way a non-2xx
// response is, since both mean "not healthy" to whatever is showing this.
export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(4000) })
    return response.ok
  } catch {
    return false
  }
}

export async function fetchAnalyticsSummary({ days = 30 } = {}) {
  return authFetch(`/api/analytics/summary?days=${days}`)
}

export async function correctVisit(visitId, fields) {
  return authFetch(`/api/visits/${visitId}`, { method: 'PATCH', body: JSON.stringify(fields) })
}

export async function fetchVisitEvents(visitId) {
  return authFetch(`/api/visits/${visitId}/events`)
}

export async function fetchStaff() {
  return authFetch('/api/auth/staff')
}

export async function createStaff({ username, password, displayName, ownerUsername, ownerPassword }) {
  return authFetch('/api/auth/staff', {
    method: 'POST',
    body: JSON.stringify({
      username, password, display_name: displayName,
      owner_username: ownerUsername, owner_password: ownerPassword,
    }),
  })
}

export async function updateStaff(staffId, { username, password, displayName, active, ownerUsername, ownerPassword }) {
  const body = { owner_username: ownerUsername, owner_password: ownerPassword }
  if (username !== undefined) body.username = username
  if (password !== undefined) body.password = password
  if (displayName !== undefined) body.display_name = displayName
  if (active !== undefined) body.active = active
  return authFetch(`/api/auth/staff/${staffId}`, { method: 'PATCH', body: JSON.stringify(body) })
}
