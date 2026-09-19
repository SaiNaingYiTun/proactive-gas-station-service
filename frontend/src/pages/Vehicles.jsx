import { useEffect, useMemo, useState } from 'react'

import {
  CarFront,
  CircleCheck,
  DoorOpen,
  Search,
  ShieldAlert,
} from 'lucide-react'

import { fetchVisits } from '../lib/api.js'
import {
  formatTime,
  latestActivityTime,
  vehicleLabel,
  visitStatusLabel,
} from '../lib/visits.js'


function Vehicles() {
  const [visits, setVisits] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')

  useEffect(() => {
    let cancelled = false

    fetchVisits({ limit: 200 })
      .then((data) => {
        if (!cancelled) setVisits(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  // Visits are already ordered most-recent-first by the backend, so the
  // first row seen per plate is that vehicle's latest known state; every
  // later row for the same plate just adds to its visit count.
  const vehicles = useMemo(() => {
    const grouped = new Map()

    for (const visit of visits) {
      const key = visit.plate_number || `unread-${visit.id}`
      const existing = grouped.get(key)
      if (existing) {
        existing.visitCount += 1
      } else {
        grouped.set(key, { ...visit, visitCount: 1 })
      }
    }

    return Array.from(grouped.values())
  }, [visits])

  const filteredVehicles = vehicles.filter((vehicle) => {
    const value = search.toLowerCase()

    const matchesSearch =
      (vehicle.plate_number || '').toLowerCase().includes(value) ||
      (vehicle.vehicle_make || '').toLowerCase().includes(value) ||
      (vehicle.vehicle_model || '').toLowerCase().includes(value)

    const matchesStatus =
      statusFilter === 'All' ||
      visitStatusLabel(vehicle) === statusFilter

    return matchesSearch && matchesStatus
  })

  const needsReviewCount = vehicles.filter(
    (vehicle) => vehicle.match_status === 'ambiguous' || vehicle.match_status === 'exit_only'
  ).length

  const insideCount = vehicles.filter(
    (vehicle) => vehicle.visit_status === 'inside'
  ).length


  return (
    <div className="mx-auto max-w-[1600px]">

      {/* HEADER */}
      <div>

        <div className="flex items-center gap-2">

          <span className="h-px w-6 bg-[#D98A32]"></span>

          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#D98A32]">
            Recognition Database
          </p>

        </div>


        <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-[#F5F6F7]">
          Vehicles
        </h2>

        <p className="mt-2 text-sm text-[#727A84]">
          Vehicles detected by the recognition system, grouped by plate.
        </p>

      </div>


      {error && (
        <p className="mt-6 rounded-lg border border-[#472F2F] bg-[#201414] px-4 py-3 text-sm text-[#D58A8A]">
          Could not reach the backend: {error}
        </p>
      )}


      {/* METRICS */}
      <div className="mt-8 grid gap-4 md:grid-cols-4">

        <VehicleMetric
          icon={CarFront}
          label="Total Vehicles"
          value={loading ? '—' : vehicles.length}
        />

        <VehicleMetric
          icon={DoorOpen}
          label="Currently Inside"
          value={loading ? '—' : insideCount}
          success
        />

        <VehicleMetric
          icon={CircleCheck}
          label="Completed"
          value={
            loading
              ? '—'
              : vehicles.filter((vehicle) => visitStatusLabel(vehicle) === 'Completed').length
          }
        />

        <VehicleMetric
          icon={ShieldAlert}
          label="Needs Review"
          value={loading ? '—' : needsReviewCount}
          warning
        />

      </div>


      {/* VEHICLE DATABASE */}
      <section className="mt-6 overflow-hidden rounded-2xl border border-[#252A30] bg-[#111419]">

        <div className="flex flex-col gap-4 border-b border-[#24292F] px-6 py-5 lg:flex-row lg:items-center lg:justify-between">

          <div>

            <h3 className="text-sm font-semibold text-[#ECEDEF]">
              Vehicle Database
            </h3>

            <p className="mt-1.5 text-xs text-[#69717B]">
              Vehicles detected by the recognition system.
            </p>

          </div>


          <div className="flex gap-3">

            <div className="relative w-72">

              <Search
                size={15}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[#555E67]"
              />

              <input
                type="text"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search plate, make, model..."
                className="w-full rounded-lg border border-[#292E34] bg-[#0D1013] py-2.5 pl-10 pr-4 text-xs text-[#D9DCDF] outline-none placeholder:text-[#505861] focus:border-[#D98A32]/60"
              />

            </div>


            <select
              value={statusFilter}
              onChange={(event) =>
                setStatusFilter(event.target.value)
              }
              className="rounded-lg border border-[#292E34] bg-[#0D1013] px-4 py-2.5 text-xs text-[#AAB0B7] outline-none focus:border-[#D98A32]/60"
            >
              <option>All</option>
              <option>Inside</option>
              <option>Completed</option>
              <option>Needs Review</option>
              <option>Unmatched Exit</option>
            </select>

          </div>

        </div>


        <div className="overflow-x-auto">

          <table className="w-full">

            <thead className="bg-[#0E1114]">

              <tr>
                <Heading>License Plate</Heading>
                <Heading>Vehicle</Heading>
                <Heading>Colour</Heading>
                <Heading>Last Seen</Heading>
                <Heading>Visits</Heading>
                <Heading>Status</Heading>
              </tr>

            </thead>


            <tbody className="divide-y divide-[#20252B]">

              {!loading && filteredVehicles.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-sm text-[#5F6770]">
                    No vehicles match this search.
                  </td>
                </tr>
              )}

              {filteredVehicles.map((vehicle) => (

                <tr
                  key={vehicle.id}
                  className="transition hover:bg-[#15191E]"
                >

                  <td className="px-6 py-4">

                    <p className="font-mono text-sm font-semibold tracking-[0.06em] text-[#F0F1F2]">
                      {vehicle.plate_number || 'Unread'}
                    </p>

                  </td>


                  <td className="px-6 py-4">

                    <p className="text-sm text-[#B8BDC3]">
                      {vehicleLabel(vehicle)}
                    </p>

                  </td>


                  <td className="px-6 py-4 text-sm capitalize text-[#5F6770]">
                    {vehicle.vehicle_color || 'unknown'}
                  </td>


                  <td className="px-6 py-4 font-mono text-xs text-[#737B84]">
                    {formatTime(latestActivityTime(vehicle))}
                  </td>


                  <td className="px-6 py-4 font-mono text-sm text-[#999FA6]">
                    {vehicle.visitCount}
                  </td>


                  <td className="px-6 py-4">

                    <StatusBadge visit={vehicle} />

                  </td>

                </tr>

              ))}

            </tbody>

          </table>

        </div>

      </section>

    </div>
  )
}


function VehicleMetric({
  icon: Icon,
  label,
  value,
  success,
  warning,
}) {
  let color = 'text-[#707984]'
  let valueColor = 'text-[#F1F2F3]'
  let border = 'border-[#252A30]'

  if (success) {
    color = 'text-[#6FA682]'
    valueColor = 'text-[#88B798]'
    border = 'border-[#2B4032]'
  }

  if (warning) {
    color = 'text-[#C66B6B]'
    valueColor = 'text-[#D58A8A]'
    border = 'border-[#432D2D]'
  }

  return (
    <div className={`rounded-2xl border ${border} bg-[#111419] p-5`}>

      <div className="flex items-center justify-between">

        <div>

          <p className="text-xs text-[#747C85]">
            {label}
          </p>

          <p className={`mt-3 text-3xl font-semibold ${valueColor}`}>
            {value}
          </p>

        </div>

        <Icon
          size={20}
          strokeWidth={1.6}
          className={color}
        />

      </div>

    </div>
  )
}


function StatusBadge({ visit }) {
  const label = visitStatusLabel(visit)
  const needsReview = visit.match_status === 'ambiguous' || visit.match_status === 'exit_only'

  if (needsReview) {
    return (
      <span className="rounded-full border border-[#472F2F] bg-[#201414] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[#C97A7A]">
        {label}
      </span>
    )
  }

  if (visit.visit_status === 'inside') {
    return (
      <span className="rounded-full border border-[#2E4636] bg-[#142019] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[#76A887]">
        {label}
      </span>
    )
  }

  return (
    <span className="rounded-full border border-[#343A41] bg-[#181C20] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[#808892]">
      {label}
    </span>
  )
}


function Heading({ children }) {
  return (
    <th className="px-6 py-3.5 text-left text-[10px] font-semibold uppercase tracking-[0.15em] text-[#555E67]">
      {children}
    </th>
  )
}


export default Vehicles
