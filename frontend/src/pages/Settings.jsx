import { useState } from 'react'

import { KeyRound } from 'lucide-react'

import { changeOwnPassword, getAccount } from '../lib/auth.js'

function Settings() {
  const account = getAccount()

  return (
    <div className="mx-auto max-w-[700px]">
      <p className="text-sm font-medium text-[#477A76]">
        System
      </p>

      <h2 className="mt-1 text-2xl font-semibold text-[#202A33]">
        Settings
      </h2>

      <p className="mt-1 text-sm text-[#71808E]">
        Manage station and system preferences.
      </p>

      <section className="mt-6 rounded-2xl border border-[#252A30] bg-[#111419] p-6">
        <div className="flex items-center gap-2">
          <KeyRound size={16} className="text-[#D98A32]" />
          <h3 className="text-sm font-semibold text-[#ECEDEF]">Your account</h3>
        </div>
        <p className="mt-1 text-xs text-[#69717B]">
          Signed in as <span className="font-mono text-[#C9CDD2]">@{account?.username}</span>
          {account?.is_owner ? ' (owner)' : ''}
        </p>

        <ChangePasswordForm />
      </section>
    </div>
  )
}


function ChangePasswordForm() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSuccess(false)
    if (newPassword !== confirmPassword) {
      setError("New passwords don't match")
      return
    }
    setSaving(true)
    try {
      await changeOwnPassword(currentPassword, newPassword)
      setSuccess(true)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-5 border-t border-[#24292F] pt-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-[#8B929B]">
        Change your password
      </p>

      <div className="mt-3 grid gap-3">
        <input
          type="password"
          placeholder="Current password"
          autoComplete="current-password"
          value={currentPassword}
          onChange={(event) => setCurrentPassword(event.target.value)}
          className="rounded-lg border border-[#292E34] bg-[#0D1013] px-3.5 py-2.5 text-sm text-[#D9DCDF] outline-none placeholder:text-[#505861] focus:border-[#D98A32]/60"
        />
        <input
          type="password"
          placeholder="New password (at least 8 characters)"
          autoComplete="new-password"
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          className="rounded-lg border border-[#292E34] bg-[#0D1013] px-3.5 py-2.5 text-sm text-[#D9DCDF] outline-none placeholder:text-[#505861] focus:border-[#D98A32]/60"
        />
        <input
          type="password"
          placeholder="Confirm new password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          className="rounded-lg border border-[#292E34] bg-[#0D1013] px-3.5 py-2.5 text-sm text-[#D9DCDF] outline-none placeholder:text-[#505861] focus:border-[#D98A32]/60"
        />
      </div>

      {error && <p className="mt-3 text-xs text-[#D58A8A]">{error}</p>}
      {success && <p className="mt-3 text-xs text-[#6FA682]">Password updated. You'll stay signed in on this device.</p>}

      <button
        type="submit"
        disabled={saving || !currentPassword || !newPassword}
        className="mt-4 rounded-lg bg-[#D98A32] px-4 py-2.5 text-sm font-semibold text-[#0B0D10] transition hover:bg-[#E29A47] disabled:cursor-not-allowed disabled:opacity-50"
      >
        {saving ? 'Updating…' : 'Update password'}
      </button>
    </form>
  )
}

export default Settings
