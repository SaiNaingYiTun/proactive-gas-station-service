import { useEffect, useState } from 'react'

import {
  Activity,
  ArrowUpRight,
  CarFront,
  Clock3,
  ShieldAlert,
  DoorOpen,
} from 'lucide-react'

import { Link } from 'react-router'

import { fetchAnalyticsSummary, fetchVisits } from '../lib/api.js'
import {
  formatTime,
  isToday,
  latestActivityTime,
  vehicleLabel,
  visitStatusLabel,
} from '../lib/visits.js'


function Overview() {
  const [visits, setVisits] = useState([])
  const [avgDwellMinutes, setAvgDwellMinutes] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false

    function load() {
      setError(null)
      fetchVisits({ limit: 50 })
        .then((data) => {
          if (!cancelled) setVisits(data)
        })
        .catch((err) => {
          if (!cancelled) setError(err.message)
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })

      fetchAnalyticsSummary({ days: 1 })
        .then((summary) => {
          if (!cancelled) setAvgDwellMinutes(summary.avg_dwell_minutes)
        })
        .catch(() => {})
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
  }, [])

  const vehiclesToday = visits.filter(
    (visit) => isToday(visit.entry_time) || isToday(visit.exit_time)
  ).length

  const currentlyInside = visits.filter(
    (visit) => visit.visit_status === 'inside'
  ).length

  const needsReview = visits.filter(
    (visit) => visit.match_status === 'ambiguous' || visit.match_status === 'exit_only'
  ).length

  const recentVisits = visits.slice(0, 6)
  const latest = visits[0]

  return (
    <div className="mx-auto max-w-[1600px]">

      {/* Header */}
      <div className="flex items-end justify-between">

        <div>

          <div className="flex items-center gap-2">

            <span className="h-px w-6 bg-[#D98A32]"></span>

            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#D98A32]">
              Command Center
            </p>

          </div>


          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-[#F5F6F7]">
            Operations Overview
          </h2>


          <p className="mt-2 text-sm text-[#727A84]">
            Real-time station activity and recognition status.
          </p>

        </div>


        <Link
          to="/vehicles"
          className="flex items-center gap-2 rounded-lg bg-[#D98A32] px-4 py-2.5 text-sm font-semibold text-[#0B0D10] transition hover:bg-[#E29A47]"
        >
          View All Vehicles

          <ArrowUpRight size={16} />
        </Link>

      </div>


      {error && (
        <p className="mt-6 rounded-lg border border-[#472F2F] bg-[#201414] px-4 py-3 text-sm text-[#D58A8A]">
          Could not reach the backend: {error}
        </p>
      )}


      {/* KPI Cards */}
      <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">

        <MetricCard
          title="Vehicles Today"
          value={loading ? '—' : vehiclesToday}
          label="Detected entries/exits"
          icon={CarFront}
        />

        <MetricCard
          title="Currently Inside"
          value={loading ? '—' : currentlyInside}
          label="Open visits"
          icon={DoorOpen}
        />

        <MetricCard
          title="Avg. Dwell Time"
          value={avgDwellMinutes === null ? '—' : `${avgDwellMinutes}m`}
          label="Today, entry to exit"
          icon={Clock3}
          accent
        />

        <MetricCard
          title="Needs Review"
          value={loading ? '—' : needsReview}
          label="Ambiguous or unmatched exits"
          icon={ShieldAlert}
          warning
        />

      </div>


      {/* Main content */}
      <div className="mt-6 grid gap-6 xl:grid-cols-12">

        {/* Recent detections */}
        <section className="overflow-hidden rounded-2xl border border-[#252A30] bg-[#111419] xl:col-span-8">

          <div className="flex items-center justify-between border-b border-[#24292F] px-6 py-5">

            <div>

              <div className="flex items-center gap-2">

                <Activity
                  size={16}
                  className="text-[#D98A32]"
                />

                <h3 className="text-sm font-semibold text-[#E9EAEC]">
                  Recent Detection Activity
                </h3>

              </div>

              <p className="mt-1.5 text-xs text-[#69717B]">
                Latest vehicles captured at the station entrance
              </p>

            </div>


            <Link
              to="/vehicles"
              className="text-xs font-medium text-[#D98A32] hover:text-[#E5A352]"
            >
              View all vehicles
            </Link>

          </div>


          {/* Table headings */}
          <div className="grid grid-cols-5 border-b border-[#20252B] bg-[#0E1114] px-6 py-3">

            <TableHeading>
              Plate
            </TableHeading>

            <TableHeading>
              Vehicle
            </TableHeading>

            <TableHeading>
              Colour
            </TableHeading>

            <TableHeading>
              Time
            </TableHeading>

            <TableHeading>
              Status
            </TableHeading>

          </div>


          <div>

            {!loading && recentVisits.length === 0 && (
              <p className="px-6 py-8 text-center text-sm text-[#5F6770]">
                No visits recorded yet.
              </p>
            )}

            {recentVisits.map((visit) => (

              <div
                key={visit.id}
                className="grid grid-cols-5 items-center border-b border-[#20252B] px-6 py-4 last:border-b-0 hover:bg-[#15191E]"
              >

                <p className="text-sm font-semibold tracking-wide text-[#ECEDEF]">
                  {visit.plate_number || '—'}
                </p>


                <p className="text-sm text-[#8B929B]">
                  {vehicleLabel(visit)}
                </p>


                <p className="text-sm text-[#A5ABB2] capitalize">
                  {visit.vehicle_color || 'unknown'}
                </p>


                <p className="font-mono text-xs text-[#6F7780]">
                  {formatTime(latestActivityTime(visit))}
                </p>


                <div>

                  <StatusBadge visit={visit} />

                </div>

              </div>

            ))}

          </div>

        </section>


        {/* Detection Snapshot */}
        <section className="overflow-hidden rounded-2xl border border-[#2D2B27] bg-[#111419] xl:col-span-4">

          <div className="border-b border-[#24292F] px-6 py-5">

            <div className="flex items-center justify-between">

              <div>

                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#D98A32]">
                  Latest Match
                </p>

                <h3 className="mt-2 text-sm font-semibold text-[#E9EAEC]">
                  Vehicle Recognition
                </h3>

              </div>


              <span className="relative flex h-2.5 w-2.5">

                <span className="absolute h-full w-full animate-ping rounded-full bg-[#D98A32] opacity-30"></span>

                <span className="relative h-2.5 w-2.5 rounded-full bg-[#D98A32]"></span>

              </span>

            </div>

          </div>


          <div className="p-6">

            {!latest && (
              <p className="text-sm text-[#5F6770]">
                {loading ? 'Loading…' : 'No detections yet.'}
              </p>
            )}

            {latest && (
              <>
                {/* Plate */}
                <div className="rounded-xl border border-[#303239] bg-[#0B0D10] p-5">

                  <p className="text-[10px] font-medium uppercase tracking-[0.22em] text-[#636B74]">
                    License Plate
                  </p>

                  <p className="mt-3 font-mono text-2xl font-semibold tracking-[0.08em] text-white">
                    {latest.plate_number || '—'}
                  </p>


                  <div className="mt-4 flex items-center justify-between">

                    <p className="text-xs text-[#707883]">
                      Status
                    </p>

                    <p className="font-mono text-xs font-semibold text-[#D98A32]">
                      {visitStatusLabel(latest)}
                    </p>

                  </div>

                </div>


                {/* Vehicle */}
                <div className="mt-6 space-y-4 border-t border-[#252A30] pt-5">

                  <InfoRow
                    label="Vehicle"
                    value={vehicleLabel(latest)}
                  />

                  <InfoRow
                    label="Colour"
                    value={latest.vehicle_color || 'Unknown'}
                  />

                  <InfoRow
                    label="Entry"
                    value={formatTime(latest.entry_time)}
                  />

                  <InfoRow
                    label="Exit"
                    value={formatTime(latest.exit_time)}
                  />

                </div>


                <Link
                  to="/vehicles"
                  className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg border border-[#343A41] bg-[#191D22] px-4 py-2.5 text-xs font-semibold text-[#C9CDD2] transition hover:border-[#D98A32]/50 hover:text-white"
                >
                  Inspect in Vehicles

                  <ArrowUpRight size={14} />
                </Link>
              </>
            )}

          </div>

        </section>

      </div>

    </div>
  )
}


function MetricCard({
  title,
  value,
  label,
  icon: Icon,
  accent = false,
  warning = false,
}) {
  return (
    <div
      className={`group relative overflow-hidden rounded-2xl border bg-[#111419] p-5 transition duration-200 hover:-translate-y-0.5 ${
        accent
          ? 'border-[#493824]'
          : warning
            ? 'border-[#3B2B2B]'
            : 'border-[#252A30]'
      }`}
    >

      {accent && (
        <div className="absolute inset-x-0 top-0 h-px bg-[#D98A32]" />
      )}


      <div className="flex items-start justify-between">

        <div>

          <p className="text-xs font-medium text-[#747C85]">
            {title}
          </p>

          <p
            className={`mt-4 text-3xl font-semibold tracking-[-0.04em] ${
              accent
                ? 'text-[#D98A32]'
                : warning
                  ? 'text-[#D7A0A0]'
                  : 'text-[#F1F2F3]'
            }`}
          >
            {value}
          </p>

        </div>


        <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#282E34] bg-[#171A1F]">

          <Icon
            size={18}
            strokeWidth={1.7}
            className={
              accent
                ? 'text-[#D98A32]'
                : warning
                  ? 'text-[#B96868]'
                  : 'text-[#707984]'
            }
          />

        </div>

      </div>


      <p className="mt-4 text-[11px] text-[#5F6770]">
        {label}
      </p>

    </div>
  )
}


function TableHeading({ children }) {
  return (
    <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-[#555E67]">
      {children}
    </p>
  )
}


function InfoRow({
  label,
  value,
}) {
  return (
    <div className="flex items-center justify-between gap-5">

      <span className="text-xs text-[#707882]">
        {label}
      </span>

      <span className="text-right text-xs font-medium text-[#C9CDD2]">
        {value}
      </span>

    </div>
  )
}


function StatusBadge({ visit }) {
  const label = visitStatusLabel(visit)
  const needsReview = visit.match_status === 'ambiguous' || visit.match_status === 'exit_only'

  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider ${
        needsReview
          ? 'border-[#472F2F] bg-[#201414] text-[#C97A7A]'
          : visit.visit_status === 'inside'
            ? 'border-[#344B3B] bg-[#152019] text-[#73A884]'
            : 'border-[#3A3F45] bg-[#1C2024] text-[#858D97]'
      }`}
    >
      {label}
    </span>
  )
}


export default Overview
