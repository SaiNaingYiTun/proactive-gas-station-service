import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router'

import { login } from '../lib/auth.js'

function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(username.trim(), password)
      const redirectTo = location.state?.from ?? '/'
      navigate(redirectTo, { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0B0D10] px-4">
      <div className="w-full max-w-sm">

        <div className="mb-8 text-center">
          <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-[#D98A32]">
            JUST
          </p>
          <h1 className="mt-3 text-2xl font-semibold text-[#F4F5F6]">
            RCVCI
          </h1>
          <p className="mt-2 text-sm text-[#656D77]">
            Sign in to the operations console
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-[#252A30] bg-[#111419] p-6"
        >
          <label className="block">
            <span className="text-xs font-medium text-[#8B929B]">Username</span>
            <input
              type="text"
              autoFocus
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="mt-1.5 w-full rounded-lg border border-[#292E34] bg-[#0D1013] px-3.5 py-2.5 text-sm text-[#D9DCDF] outline-none placeholder:text-[#505861] focus:border-[#D98A32]/60"
            />
          </label>

          <label className="mt-4 block">
            <span className="text-xs font-medium text-[#8B929B]">Password</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1.5 w-full rounded-lg border border-[#292E34] bg-[#0D1013] px-3.5 py-2.5 text-sm text-[#D9DCDF] outline-none placeholder:text-[#505861] focus:border-[#D98A32]/60"
            />
          </label>

          {error && (
            <p className="mt-4 rounded-lg border border-[#472F2F] bg-[#201414] px-3.5 py-2.5 text-xs text-[#D58A8A]">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !username || !password}
            className="mt-6 w-full rounded-lg bg-[#D98A32] py-2.5 text-sm font-semibold text-[#0B0D10] transition hover:bg-[#E29A47] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

      </div>
    </div>
  )
}

export default Login
