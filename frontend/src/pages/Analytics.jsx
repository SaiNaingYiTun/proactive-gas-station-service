import { useEffect, useState } from 'react'

import {
  CarFront,
  Clock3,
  Palette,
  ShieldAlert,
  TrendingUp,
} from 'lucide-react'

import { fetchAnalyticsSummary } from '../lib/api.js'


// A small, brand-neutral palette cycled across bars/legend swatches --
// there is no per-make or per-colour brand palette to draw from, so this
// just needs to stay legible and consistent, not carry meaning per make.
const SERIES_COLORS = ['#D98A32', '#5B8DBF', '#7FAE7A', '#B478B0', '#C4694F', '#6CA8A8']

function Analytics() {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [days, setDays] = useState(30)

  useEffect(() => {
    let cancelled = false

    function load() {
      // Reset to the loading state on every `days` change (not just on
      // mount), so switching ranges shows a fresh load instead of the
      // previous range's numbers sitting there stale while the new ones
      // are fetched.
      setLoading(true)
      setError(null)
      fetchAnalyticsSummary({ days })
        .then((data) => { if (!cancelled) setSummary(data) })
        .catch((err) => { if (!cancelled) setError(err.message) })
        .finally(() => { if (!cancelled) setLoading(false) })
    }

    function onVisible() {
      if (document.visibilityState === 'visible') load()
    }

    load()
    document.addEventListener('visibilitychange', onVisible)
    window.addEventListener('focus', onVisible)

    return () => {
      cancelled = true
      document.removeEventListener('visibilitychange', onVisible)
      window.removeEventListener('focus', onVisible)
    }
  }, [days])

  const maxDaily = summary ? Math.max(1, ...summary.traffic_by_day.map((d) => d.count)) : 1

  return (
    <div className="mx-auto max-w-[1600px]">

      {/* HEADER */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-px w-6 bg-[#D98A32]"></span>
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#D98A32]">
              Station Intelligence
            </p>
          </div>

          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-[#F5F6F7]">
            Analytics
          </h2>

          <p className="mt-2 text-sm text-[#727A84]">
            Real traffic, make/colour, and dwell time computed from recorded visits.
          </p>
        </div>

        <div className="flex gap-1 rounded-lg border border-[#252A30] bg-[#111419] p-1">
          {[7, 30, 90].map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setDays(option)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                days === option ? 'bg-[#D98A32] text-[#0B0D10]' : 'text-[#8B929B] hover:text-white'
              }`}
            >
              {option}d
            </button>
          ))}
        </div>
      </div>

      {error && (
        <p className="mt-6 rounded-lg border border-[#472F2F] bg-[#201414] px-4 py-3 text-sm text-[#D58A8A]">
          Could not reach the backend: {error}
        </p>
      )}

      {/* KPI */}
      <div className="mt-8 grid gap-4 md:grid-cols-4">
        <AnalyticsMetric icon={CarFront} label="Total Visits" value={loading ? '—' : summary.total_visits} />
        <AnalyticsMetric
          icon={Clock3}
          label="Avg. Dwell Time"
          value={loading || summary.avg_dwell_minutes === null ? '—' : `${summary.avg_dwell_minutes}m`}
          accent
        />
        <AnalyticsMetric
          icon={ShieldAlert}
          label="Needs Review"
          value={loading ? '—' : summary.needs_review}
        />
        <AnalyticsMetric
          icon={TrendingUp}
          label="Days Covered"
          value={loading ? '—' : days}
        />
      </div>

      {/* MAIN CHARTS */}
      <div className="mt-6 grid gap-6 xl:grid-cols-12">

        {/* TRAFFIC */}
        <section className="rounded-2xl border border-[#252A30] bg-[#111419] p-6 xl:col-span-8">
          <h3 className="text-sm font-semibold text-[#ECEDEF]">Vehicle Traffic</h3>
          <p className="mt-1.5 text-xs text-[#69717B]">
            Entries recorded per day over the last {days} days
          </p>

          {!loading && summary.traffic_by_day.length === 0 && (
            <p className="mt-10 text-center text-sm text-[#5F6770]">No visits recorded in this range.</p>
          )}

          {!loading && summary.traffic_by_day.length > 0 && (
            <div className="mt-10 flex h-64 items-end gap-1.5 overflow-x-auto border-b border-[#292E34] pb-0">
              {summary.traffic_by_day.map((item) => (
                <div key={item.date} className="flex h-full min-w-[10px] flex-1 flex-col justify-end">
                  <div className="group relative flex flex-1 items-end justify-center">
                    <div
                      className="w-full max-w-14 rounded-t-md bg-gradient-to-t from-[#6F431C] to-[#D98A32] transition-all duration-300 group-hover:brightness-110"
                      style={{ height: `${Math.max(2, (item.count / maxDaily) * 100)}%` }}
                    />
                    <div className="absolute bottom-[calc(100%+8px)] hidden whitespace-nowrap rounded-md border border-[#32373D] bg-[#171A1F] px-2 py-1 font-mono text-[10px] text-[#D5D8DB] group-hover:block">
                      {item.date}: {item.count}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* MAKE BREAKDOWN */}
        <section className="rounded-2xl border border-[#252A30] bg-[#111419] p-6 xl:col-span-4">
          <h3 className="text-sm font-semibold text-[#ECEDEF]">Vehicle Make</h3>
          <p className="mt-1.5 text-xs text-[#69717B]">
            Recognised makes, "unknown" excluded
          </p>

          <BreakdownList
            loading={loading}
            items={summary?.by_make.map((row) => ({ label: row.make, count: row.count }))}
            emptyText="No make classifications yet."
          />
        </section>
      </div>

      {/* SECOND ROW */}
      <div className="mt-6 grid gap-6 xl:grid-cols-2">

        {/* COLOUR BREAKDOWN */}
        <section className="rounded-2xl border border-[#252A30] bg-[#111419] p-6">
          <div className="flex items-center gap-2">
            <Palette size={15} className="text-[#D98A32]" />
            <h3 className="text-sm font-semibold text-[#ECEDEF]">Vehicle Colour</h3>
          </div>
          <p className="mt-1.5 text-xs text-[#69717B]">
            Recognised colours, "unknown" excluded
          </p>

          <BreakdownList
            loading={loading}
            items={summary?.by_color.map((row) => ({ label: row.color, count: row.count }))}
            emptyText="No colour classifications yet."
          />
        </section>

        {/* DWELL TIME DETAIL */}
        <section className="rounded-2xl border border-[#252A30] bg-[#111419] p-6">
          <h3 className="text-sm font-semibold text-[#ECEDEF]">Dwell Time</h3>
          <p className="mt-1.5 text-xs text-[#69717B]">
            How long a completed visit spent between entry and exit
          </p>

          {!loading && (
            <div className="mt-7 space-y-5">
              <StatRow label="Average" value={summary.avg_dwell_minutes === null ? 'No completed visits yet' : `${summary.avg_dwell_minutes} minutes`} />
              <StatRow label="Completed visits with both entry and exit" value={summary.completed_with_dwell} />
              <StatRow label="Total visits in range" value={summary.total_visits} />
            </div>
          )}
        </section>
      </div>
    </div>
  )
}


function AnalyticsMetric({ icon: Icon, label, value, accent }) {
  return (
    <div className={`rounded-2xl border bg-[#111419] p-5 ${accent ? 'border-[#493824]' : 'border-[#252A30]'}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-[#747C85]">{label}</p>
          <p className={`mt-3 text-3xl font-semibold tracking-[-0.04em] ${accent ? 'text-[#D98A32]' : 'text-[#F1F2F3]'}`}>
            {value}
          </p>
        </div>
        <Icon size={19} strokeWidth={1.7} className={accent ? 'text-[#D98A32]' : 'text-[#707984]'} />
      </div>
    </div>
  )
}


function BreakdownList({ loading, items, emptyText }) {
  if (loading) {
    return <p className="mt-8 text-xs text-[#5F6770]">Loading…</p>
  }
  if (!items || items.length === 0) {
    return <p className="mt-8 text-xs text-[#5F6770]">{emptyText}</p>
  }
  const total = items.reduce((sum, item) => sum + item.count, 0) || 1

  return (
    <div className="mt-6 space-y-4">
      {items.slice(0, 8).map((item, index) => {
        const percent = Math.round((item.count / total) * 100)
        return (
          <div key={item.label}>
            <div className="flex items-center justify-between">
              <p className="text-xs capitalize text-[#9BA2AA]">{item.label}</p>
              <p className="font-mono text-xs font-semibold text-[#D7DADD]">{item.count} · {percent}%</p>
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[#22272D]">
              <div
                className="h-full rounded-full"
                style={{ width: `${percent}%`, backgroundColor: SERIES_COLORS[index % SERIES_COLORS.length] }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}


function StatRow({ label, value }) {
  return (
    <div className="rounded-xl border border-[#252A30] bg-[#0E1114] p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-[#B8BDC3]">{label}</p>
        <p className="font-mono text-lg font-semibold text-[#D98A32]">{value}</p>
      </div>
    </div>
  )
}


export default Analytics
