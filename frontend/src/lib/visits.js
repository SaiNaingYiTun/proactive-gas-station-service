// Shared display helpers so Overview/Vehicles/Analytics agree on how a
// raw vehicle_visits row (see backend/main.py) reads on screen.

export function visitStatusLabel(visit) {
  if (visit.match_status === 'ambiguous') return 'Needs Review'
  if (visit.match_status === 'exit_only') return 'Unmatched Exit'
  if (visit.visit_status === 'inside') return 'Inside'
  if (visit.visit_status === 'completed') return 'Completed'
  return visit.visit_status ?? 'Unknown'
}

export function vehicleLabel(visit) {
  const make = visit.vehicle_make && visit.vehicle_make !== 'unknown' ? visit.vehicle_make : null
  const model = visit.vehicle_model && visit.vehicle_model !== 'unknown' ? visit.vehicle_model : null
  if (make && model) return `${make} ${model}`
  if (make) return make
  return 'Unknown vehicle'
}

export function formatTime(isoString) {
  if (!isoString) return '—'
  const date = new Date(isoString)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// The most recent activity timestamp for a visit -- exit_time once it's
// closed, otherwise entry_time; an "exit_only" visit has neither reliably
// so created_at is the last resort.
export function latestActivityTime(visit) {
  return visit.exit_time ?? visit.entry_time ?? visit.created_at
}

export function isToday(isoString) {
  if (!isoString) return false
  const date = new Date(isoString)
  const now = new Date()
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  )
}
