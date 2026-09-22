// Session storage and the auth-related API calls. The token is a signed JWT
// (see backend/auth.py) that the backend re-checks against the account's
// CURRENT row on every request, not just its own signature/expiry -- so a
// stored token that the owner has since invalidated (changed that staff
// member's username/password) stops working immediately, not just when it
// expires. localStorage (not sessionStorage) so a login survives closing the
// browser tab, matching how the desktop app remembers its own settings.

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'
const STORAGE_KEY = 'gas-station-session'

function readSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    // Private-window / blocked storage: never let a broken localStorage
    // crash the app -- it just behaves as if nobody is logged in.
    return null
  }
}

function writeSession(session) {
  try {
    if (session) localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Same as above: storage failing to persist is not a reason to crash.
  }
}

export function getToken() {
  return readSession()?.token ?? null
}

export function getAccount() {
  return readSession()?.account ?? null
}

export function isLoggedIn() {
  return Boolean(getToken())
}

export function isOwner() {
  return Boolean(getAccount()?.is_owner)
}

export function logout() {
  writeSession(null)
}

async function parseErrorDetail(response) {
  try {
    const body = await response.json()
    return body.detail || `Request failed (${response.status})`
  } catch {
    return `Request failed (${response.status})`
  }
}

export async function login(username, password) {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response))
  }
  const session = await response.json()
  writeSession(session)
  return session.account
}

export async function changeOwnPassword(currentPassword, newPassword) {
  // Changing a password bumps the account's updated_at on the backend (see
  // backend/auth.py) so every OTHER session logged in as this account stops
  // working immediately -- but that includes the very token this request
  // was just authenticated with. Without logging in again right here, the
  // next request this tab makes would 401 and silently drop the session,
  // even though this person just proved they know both passwords.
  const account = getAccount()
  await authFetch('/api/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  })
  if (account) await login(account.username, newPassword)
}

// A fetch wrapper that attaches the bearer token and, on a 401 (missing,
// expired, or invalidated-by-an-owner-change token), clears the stored
// session so the rest of the app falls back to the logged-out state on its
// next render instead of silently refetching with a token that will never
// work again.
export async function authFetch(path, options = {}) {
  const token = getToken()
  const headers = { ...(options.headers || {}) }
  if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json'
  if (token) headers['Authorization'] = `Bearer ${token}`

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (response.status === 401) {
    writeSession(null)
  }
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response))
  }
  if (response.status === 204) return null
  return response.json()
}

export { API_BASE }
