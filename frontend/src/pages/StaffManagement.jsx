import { useEffect, useState } from 'react'

import { KeyRound, ShieldCheck, UserPlus, Users } from 'lucide-react'

import { createStaff, fetchStaff, updateStaff } from '../lib/api.js'
import { formatTime } from '../lib/visits.js'
import { getAccount } from '../lib/auth.js'


function StaffManagement() {
  const [staff, setStaff] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [showCreate, setShowCreate] = useState(false)

  function load() {
    setLoading(true)
    fetchStaff()
      .then(setStaff)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  // The initial load doesn't need load()'s own setLoading(true) -- `loading`
  // already starts true -- so this effect fetches directly rather than
  // calling a function that resets state synchronously in the effect body.
  useEffect(() => {
    fetchStaff()
      .then(setStaff)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="mx-auto max-w-[1200px]">

      <div>
        <div className="flex items-center gap-2">
          <span className="h-px w-6 bg-[#D98A32]"></span>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#D98A32]">
            Owner Only
          </p>
        </div>
        <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-[#F5F6F7]">
          Staff Accounts
        </h2>
        <p className="mt-2 text-sm text-[#727A84]">
          Create logins for staff, or repurpose a former employee's account for whoever replaces them.
        </p>
      </div>

      {error && (
        <p className="mt-6 rounded-lg border border-[#472F2F] bg-[#201414] px-4 py-3 text-sm text-[#D58A8A]">
          {error}
        </p>
      )}

      <section className="mt-6 overflow-hidden rounded-2xl border border-[#252A30] bg-[#111419]">
        <div className="flex items-center justify-between border-b border-[#24292F] px-6 py-5">
          <div className="flex items-center gap-2">
            <Users size={16} className="text-[#D98A32]" />
            <h3 className="text-sm font-semibold text-[#ECEDEF]">Accounts</h3>
          </div>
          <button
            type="button"
            onClick={() => setShowCreate((v) => !v)}
            className="flex items-center gap-2 rounded-lg bg-[#D98A32] px-3.5 py-2 text-xs font-semibold text-[#0B0D10] transition hover:bg-[#E29A47]"
          >
            <UserPlus size={14} />
            New staff account
          </button>
        </div>

        {showCreate && (
          <CreateStaffForm
            onDone={() => { setShowCreate(false); load() }}
            onCancel={() => setShowCreate(false)}
          />
        )}

        <div className="divide-y divide-[#20252B]">
          {!loading && staff.length === 0 && (
            <p className="px-6 py-8 text-center text-sm text-[#5F6770]">No staff accounts yet.</p>
          )}
          {staff.map((account) => (
            <div key={account.id} className="px-6 py-5">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-[#ECEDEF]">{account.display_name}</p>
                    {account.is_owner && (
                      <span className="flex items-center gap-1 rounded-full border border-[#493824] bg-[#1C1610] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#D99A53]">
                        <ShieldCheck size={10} /> Owner
                      </span>
                    )}
                    {!account.active && (
                      <span className="rounded-full border border-[#472F2F] bg-[#201414] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#C97A7A]">
                        Deactivated
                      </span>
                    )}
                  </div>
                  <p className="mt-1 font-mono text-xs text-[#858D97]">@{account.username}</p>
                  <p className="mt-1 text-[11px] text-[#5F6770]">
                    Added {formatTime(account.created_at)} · last changed {formatTime(account.updated_at)}
                  </p>
                </div>
                {!account.is_owner && (
                  <button
                    type="button"
                    onClick={() => setEditingId(editingId === account.id ? null : account.id)}
                    className="flex items-center gap-1.5 rounded-lg border border-[#292E34] bg-[#0D1013] px-3 py-2 text-xs font-medium text-[#C9CDD2] transition hover:border-[#D98A32]/50"
                  >
                    <KeyRound size={13} />
                    {editingId === account.id ? 'Cancel' : 'Change login / deactivate'}
                  </button>
                )}
              </div>

              {editingId === account.id && (
                <EditStaffForm
                  account={account}
                  onDone={() => { setEditingId(null); load() }}
                  onCancel={() => setEditingId(null)}
                />
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}


function OwnerReauth({ ownerUsername, ownerPassword, setOwnerUsername, setOwnerPassword }) {
  const account = getAccount()
  return (
    <div className="mt-4 rounded-xl border border-[#3B2F1F] bg-[#1A140D] p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-[#D98A32]">
        Confirm it's you
      </p>
      <p className="mt-1 text-[11px] text-[#9C8A6E]">
        Re-enter your own owner login to confirm this change{account?.username ? ` (signed in as @${account.username})` : ''}.
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <input
          type="text"
          placeholder="Your owner username"
          autoComplete="username"
          value={ownerUsername}
          onChange={(event) => setOwnerUsername(event.target.value)}
          className="rounded-lg border border-[#292E34] bg-[#0D1013] px-3 py-2 text-xs text-[#D9DCDF] outline-none placeholder:text-[#505861] focus:border-[#D98A32]/60"
        />
        <input
          type="password"
          placeholder="Your owner password"
          autoComplete="current-password"
          value={ownerPassword}
          onChange={(event) => setOwnerPassword(event.target.value)}
          className="rounded-lg border border-[#292E34] bg-[#0D1013] px-3 py-2 text-xs text-[#D9DCDF] outline-none placeholder:text-[#505861] focus:border-[#D98A32]/60"
        />
      </div>
    </div>
  )
}


function CreateStaffForm({ onDone, onCancel }) {
  const [username, setUsername] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [ownerUsername, setOwnerUsername] = useState('')
  const [ownerPassword, setOwnerPassword] = useState('')
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSaving(true)
    try {
      await createStaff({ username: username.trim(), password, displayName: displayName.trim(), ownerUsername: ownerUsername.trim(), ownerPassword })
      onDone()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="border-b border-[#24292F] bg-[#0E1114] px-6 py-5">
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Display name" value={displayName} onChange={setDisplayName} placeholder="e.g. Nok" />
        <Field label="Username" value={username} onChange={setUsername} placeholder="e.g. nok" />
        <Field label="Password" type="password" value={password} onChange={setPassword} placeholder="At least 8 characters" />
      </div>
      <OwnerReauth {...{ ownerUsername, ownerPassword, setOwnerUsername, setOwnerPassword }} />
      {error && <p className="mt-3 text-xs text-[#D58A8A]">{error}</p>}
      <div className="mt-4 flex gap-2">
        <button type="submit" disabled={saving} className="rounded-lg bg-[#D98A32] px-4 py-2 text-xs font-semibold text-[#0B0D10] transition hover:bg-[#E29A47] disabled:opacity-50">
          {saving ? 'Creating…' : 'Create account'}
        </button>
        <button type="button" onClick={onCancel} className="rounded-lg border border-[#292E34] px-4 py-2 text-xs text-[#AAB0B7]">
          Cancel
        </button>
      </div>
    </form>
  )
}


function EditStaffForm({ account, onDone, onCancel }) {
  const [username, setUsername] = useState(account.username)
  const [displayName, setDisplayName] = useState(account.display_name)
  const [password, setPassword] = useState('')
  const [ownerUsername, setOwnerUsername] = useState('')
  const [ownerPassword, setOwnerPassword] = useState('')
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  async function submit(extra = {}) {
    setError(null)
    setSaving(true)
    try {
      await updateStaff(account.id, {
        username: username.trim() !== account.username ? username.trim() : undefined,
        displayName: displayName.trim() !== account.display_name ? displayName.trim() : undefined,
        password: password ? password : undefined,
        ownerUsername: ownerUsername.trim(),
        ownerPassword,
        ...extra,
      })
      onDone()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mt-4 rounded-xl border border-[#252A30] bg-[#0E1114] p-4">
      <p className="text-xs text-[#858D97]">
        Change the username and password to hand this login to a new hire, or just deactivate it.
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <Field label="Display name" value={displayName} onChange={setDisplayName} />
        <Field label="Username" value={username} onChange={setUsername} />
        <Field label="New password" type="password" value={password} onChange={setPassword} placeholder="Leave blank to keep current" />
      </div>
      <OwnerReauth {...{ ownerUsername, ownerPassword, setOwnerUsername, setOwnerPassword }} />
      {error && <p className="mt-3 text-xs text-[#D58A8A]">{error}</p>}
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => submit()}
          disabled={saving}
          className="rounded-lg bg-[#D98A32] px-4 py-2 text-xs font-semibold text-[#0B0D10] transition hover:bg-[#E29A47] disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save changes'}
        </button>
        <button
          type="button"
          onClick={() => submit({ active: !account.active })}
          disabled={saving}
          className="rounded-lg border border-[#472F2F] bg-[#201414] px-4 py-2 text-xs font-medium text-[#D58A8A] disabled:opacity-50"
        >
          {account.active ? 'Deactivate this login' : 'Reactivate this login'}
        </button>
        <button type="button" onClick={onCancel} className="rounded-lg border border-[#292E34] px-4 py-2 text-xs text-[#AAB0B7]">
          Cancel
        </button>
      </div>
    </div>
  )
}


function Field({ label, value, onChange, type = 'text', placeholder }) {
  return (
    <label className="block">
      <span className="text-[11px] font-medium text-[#8B929B]">{label}</span>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-lg border border-[#292E34] bg-[#0D1013] px-3 py-2 text-xs text-[#D9DCDF] outline-none placeholder:text-[#505861] focus:border-[#D98A32]/60"
      />
    </label>
  )
}


export default StaffManagement
