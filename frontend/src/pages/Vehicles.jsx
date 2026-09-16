import { useState } from 'react'

import {
  CarFront,
  CircleCheck,
  Search,
  ScanLine,
  ShieldAlert,
  UserRound,
} from 'lucide-react'

import { useNavigate } from 'react-router'

import { customers } from '../data/mockCustomers.js'


const additionalVehicles = [
  {
    id: 'V004',
    licensePlate: '7กข-5544',
    make: 'Honda',
    model: 'Civic',
    color: 'Blue',
    owner: 'Unknown',
    ownerId: null,
    visits: 1,
    lastSeen: '18 Aug 2026 • 14:27',
    status: 'New',
  },

  {
    id: 'V005',
    licensePlate: 'BKK-5092',
    make: 'Isuzu',
    model: 'D-Max',
    color: 'White',
    owner: 'Unregistered',
    ownerId: null,
    visits: 3,
    lastSeen: '17 Aug 2026 • 19:42',
    status: 'Review',
  },
]


function Vehicles() {
  const navigate = useNavigate()

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')

  const customerVehicles = customers.map((customer, index) => ({
    id: `V00${index + 1}`,
    licensePlate: customer.vehicle.licensePlate,
    make: customer.vehicle.make,
    model: customer.vehicle.model,
    color: customer.vehicle.color,
    owner: customer.name,
    ownerId: customer.id,
    visits: customer.totalVisits,
    lastSeen: customer.lastVisit,
    status: 'Known',
  }))

  const vehicles = [
    ...customerVehicles,
    ...additionalVehicles,
  ]


  const filteredVehicles = vehicles.filter((vehicle) => {
    const value = search.toLowerCase()

    const matchesSearch =
      vehicle.licensePlate.toLowerCase().includes(value) ||
      vehicle.make.toLowerCase().includes(value) ||
      vehicle.model.toLowerCase().includes(value) ||
      vehicle.owner.toLowerCase().includes(value)

    const matchesStatus =
      statusFilter === 'All' ||
      vehicle.status === statusFilter

    return matchesSearch && matchesStatus
  })


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
          Monitor recognized, new and unregistered vehicles.
        </p>

      </div>


      {/* METRICS */}
      <div className="mt-8 grid gap-4 md:grid-cols-4">

        <VehicleMetric
          icon={CarFront}
          label="Total Vehicles"
          value={vehicles.length}
        />

        <VehicleMetric
          icon={CircleCheck}
          label="Known"
          value={
            vehicles.filter(
              (vehicle) => vehicle.status === 'Known'
            ).length
          }
          success
        />

        <VehicleMetric
          icon={ScanLine}
          label="New Vehicles"
          value={
            vehicles.filter(
              (vehicle) => vehicle.status === 'New'
            ).length
          }
          accent
        />

        <VehicleMetric
          icon={ShieldAlert}
          label="Review"
          value={
            vehicles.filter(
              (vehicle) => vehicle.status === 'Review'
            ).length
          }
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
                placeholder="Search plate, model, owner..."
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
              <option>Known</option>
              <option>New</option>
              <option>Review</option>
            </select>

          </div>

        </div>


        <div className="overflow-x-auto">

          <table className="w-full">

            <thead className="bg-[#0E1114]">

              <tr>
                <Heading>License Plate</Heading>
                <Heading>Vehicle</Heading>
                <Heading>Owner</Heading>
                <Heading>Last Seen</Heading>
                <Heading>Visits</Heading>
                <Heading>Status</Heading>
                <th className="px-6 py-3"></th>
              </tr>

            </thead>


            <tbody className="divide-y divide-[#20252B]">

              {filteredVehicles.map((vehicle) => (

                <tr
                  key={vehicle.id}
                  className="transition hover:bg-[#15191E]"
                >

                  <td className="px-6 py-4">

                    <p className="font-mono text-sm font-semibold tracking-[0.06em] text-[#F0F1F2]">
                      {vehicle.licensePlate}
                    </p>

                    <p className="mt-1 text-[10px] uppercase tracking-wider text-[#545C65]">
                      {vehicle.id}
                    </p>

                  </td>


                  <td className="px-6 py-4">

                    <p className="text-sm text-[#B8BDC3]">
                      {vehicle.make} {vehicle.model}
                    </p>

                    <p className="mt-1 text-xs text-[#5F6770]">
                      {vehicle.color}
                    </p>

                  </td>


                  <td className="px-6 py-4">

                    <div className="flex items-center gap-2">

                      <UserRound
                        size={14}
                        className="text-[#606872]"
                      />

                      <span className="text-sm text-[#969DA5]">
                        {vehicle.owner}
                      </span>

                    </div>

                  </td>


                  <td className="px-6 py-4 font-mono text-xs text-[#737B84]">
                    {vehicle.lastSeen}
                  </td>


                  <td className="px-6 py-4 font-mono text-sm text-[#999FA6]">
                    {vehicle.visits}
                  </td>


                  <td className="px-6 py-4">

                    <StatusBadge status={vehicle.status} />

                  </td>


                  <td className="px-6 py-4">

                    {vehicle.ownerId ? (

                      <button
                        type="button"
                        onClick={() =>
                          navigate(`/customers/${vehicle.ownerId}`)
                        }
                        className="text-xs font-semibold text-[#D98A32] hover:text-[#E8A757]"
                      >
                        Owner Profile
                      </button>

                    ) : (

                      <span className="text-xs text-[#4F5760]">
                        —
                      </span>

                    )}

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
  accent,
  success,
  warning,
}) {
  let color = 'text-[#707984]'
  let valueColor = 'text-[#F1F2F3]'
  let border = 'border-[#252A30]'

  if (accent) {
    color = 'text-[#D98A32]'
    valueColor = 'text-[#D98A32]'
    border = 'border-[#493824]'
  }

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


function StatusBadge({ status }) {
  if (status === 'Known') {
    return (
      <span className="rounded-full border border-[#2E4636] bg-[#142019] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[#76A887]">
        Known
      </span>
    )
  }

  if (status === 'Review') {
    return (
      <span className="rounded-full border border-[#472F2F] bg-[#201414] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[#C97A7A]">
        Review
      </span>
    )
  }

  return (
    <span className="rounded-full border border-[#493824] bg-[#1A1510] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[#D99A53]">
      New
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