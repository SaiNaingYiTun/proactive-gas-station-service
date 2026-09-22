import { useState } from 'react'

import {
  CheckCircle2,
  CircleAlert,
  Clock3,
  Search,
  ShieldAlert,
  TriangleAlert,
} from 'lucide-react'


const incidents = [
  {
    id: 'INC-001',
    title: 'Payment Dispute',
    type: 'Payment',
    customer: 'Sarah Lee',
    vehicle: 'XYZ-8923',
    date: '18 Aug 2026',
    time: '13:42',
    priority: 'High',
    status: 'Open',
    note: 'Customer reported a duplicate payment notification.',
  },

  {
    id: 'INC-002',
    title: 'Fuel Service Complaint',
    type: 'Service',
    customer: 'John Doe',
    vehicle: 'ABC-1234',
    date: '17 Aug 2026',
    time: '18:20',
    priority: 'Medium',
    status: 'Investigating',
    note: 'Customer reported longer than expected service time.',
  },

  {
    id: 'INC-003',
    title: 'Unregistered Vehicle Review',
    type: 'Security',
    customer: 'Unknown',
    vehicle: 'BKK-5092',
    date: '17 Aug 2026',
    time: '19:42',
    priority: 'High',
    status: 'Open',
    note: 'Vehicle detected repeatedly without a linked customer record.',
  },

  {
    id: 'INC-004',
    title: 'Car Wash Service Issue',
    type: 'Service',
    customer: 'Michael Tan',
    vehicle: '9กม-2811',
    date: '15 Aug 2026',
    time: '16:05',
    priority: 'Low',
    status: 'Resolved',
    note: 'Customer complaint was handled and service was repeated.',
  },
]


function Incidents() {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('All')

  const filteredIncidents = incidents.filter((incident) => {
    const value = search.toLowerCase()

    const matchesSearch =
      incident.title.toLowerCase().includes(value) ||
      incident.customer.toLowerCase().includes(value) ||
      incident.vehicle.toLowerCase().includes(value)

    const matchesFilter =
      filter === 'All' ||
      incident.status === filter

    return matchesSearch && matchesFilter
  })


  return (
    <div className="mx-auto max-w-[1600px]">

      {/* HEADER */}
      <div>

        <div className="flex items-center gap-2">

          <span className="h-px w-6 bg-[#D98A32]"></span>

          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#D98A32]">
            Operational Risk
          </p>

        </div>


        <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-[#F5F6F7]">
          Incidents
        </h2>

        <p className="mt-2 text-sm text-[#727A84]">
          Monitor customer complaints, service issues and security events.
        </p>

      </div>


      {/* METRICS */}
      <div className="mt-8 grid gap-4 md:grid-cols-4">

        <IncidentMetric
          icon={TriangleAlert}
          label="Open Incidents"
          value={
            incidents.filter(
              (incident) => incident.status === 'Open'
            ).length
          }
          danger
        />

        <IncidentMetric
          icon={ShieldAlert}
          label="High Priority"
          value={
            incidents.filter(
              (incident) => incident.priority === 'High'
            ).length
          }
          warning
        />

        <IncidentMetric
          icon={Clock3}
          label="Investigating"
          value={
            incidents.filter(
              (incident) => incident.status === 'Investigating'
            ).length
          }
          accent
        />

        <IncidentMetric
          icon={CheckCircle2}
          label="Resolved"
          value={
            incidents.filter(
              (incident) => incident.status === 'Resolved'
            ).length
          }
          success
        />

      </div>


      {/* INCIDENT LIST */}
      <section className="mt-6 overflow-hidden rounded-2xl border border-[#252A30] bg-[#111419]">

        <div className="flex flex-col gap-4 border-b border-[#24292F] px-6 py-5 lg:flex-row lg:items-center lg:justify-between">

          <div>

            <h3 className="text-sm font-semibold text-[#ECEDEF]">
              Incident Log
            </h3>

            <p className="mt-1.5 text-xs text-[#69717B]">
              Current and historical incident records.
            </p>

          </div>


          <div className="flex gap-3">

            <div className="relative w-72">

              <Search
                size={15}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[#555E67]"
              />

              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search incident..."
                className="w-full rounded-lg border border-[#292E34] bg-[#0D1013] py-2.5 pl-10 pr-4 text-xs text-[#D9DCDF] outline-none placeholder:text-[#505861] focus:border-[#D98A32]/60"
              />

            </div>


            <select
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
              className="rounded-lg border border-[#292E34] bg-[#0D1013] px-4 py-2.5 text-xs text-[#AAB0B7] outline-none"
            >
              <option>All</option>
              <option>Open</option>
              <option>Investigating</option>
              <option>Resolved</option>
            </select>

          </div>

        </div>


        <div className="divide-y divide-[#20252B]">

          {filteredIncidents.map((incident) => (

            <div
              key={incident.id}
              className="px-6 py-5 transition hover:bg-[#15191E]"
            >

              <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">

                <div className="flex gap-4">

                  <div
                    className={`mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border ${
                      incident.priority === 'High'
                        ? 'border-[#472F2F] bg-[#201414]'
                        : 'border-[#3D3529] bg-[#1B1711]'
                    }`}
                  >

                    {incident.priority === 'High' ? (
                      <CircleAlert
                        size={18}
                        className="text-[#C96E6E]"
                      />
                    ) : (
                      <TriangleAlert
                        size={18}
                        className="text-[#D98A32]"
                      />
                    )}

                  </div>


                  <div>

                    <div className="flex flex-wrap items-center gap-3">

                      <p className="text-sm font-semibold text-[#E8EAEC]">
                        {incident.title}
                      </p>

                      <span className="font-mono text-[10px] text-[#535B64]">
                        {incident.id}
                      </span>

                    </div>


                    <p className="mt-2 max-w-2xl text-xs leading-5 text-[#757D86]">
                      {incident.note}
                    </p>


                    <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2">

                      <Meta
                        label="Vehicle"
                        value={incident.vehicle}
                      />

                      <Meta
                        label="Customer"
                        value={incident.customer}
                      />

                      <Meta
                        label="Type"
                        value={incident.type}
                      />

                      <Meta
                        label="Reported"
                        value={`${incident.date} • ${incident.time}`}
                      />

                    </div>

                  </div>

                </div>


                <div className="flex items-center gap-2">

                  <PriorityBadge priority={incident.priority} />

                  <StatusBadge status={incident.status} />

                </div>

              </div>

            </div>

          ))}

        </div>

      </section>

    </div>
  )
}


function IncidentMetric({
  icon: Icon,
  label,
  value,
  danger,
  warning,
  accent,
  success,
}) {
  let color = 'text-[#707984]'
  let valueColor = 'text-[#F1F2F3]'
  let border = 'border-[#252A30]'

  if (danger || warning) {
    color = 'text-[#C56B6B]'
    valueColor = 'text-[#D98D8D]'
    border = 'border-[#432D2D]'
  }

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
          size={19}
          strokeWidth={1.7}
          className={color}
        />

      </div>

    </div>
  )
}


function Meta({ label, value }) {
  return (
    <div>

      <p className="text-[9px] font-semibold uppercase tracking-wider text-[#4F5760]">
        {label}
      </p>

      <p className="mt-1 text-xs text-[#8A929B]">
        {value}
      </p>

    </div>
  )
}


function PriorityBadge({ priority }) {
  if (priority === 'High') {
    return (
      <span className="rounded-full border border-[#472F2F] bg-[#201414] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[#C97A7A]">
        High
      </span>
    )
  }

  return (
    <span className="rounded-full border border-[#493824] bg-[#1A1510] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[#D99A53]">
      {priority}
    </span>
  )
}


function StatusBadge({ status }) {
  if (status === 'Resolved') {
    return (
      <span className="rounded-full border border-[#2E4636] bg-[#142019] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[#76A887]">
        Resolved
      </span>
    )
  }

  if (status === 'Investigating') {
    return (
      <span className="rounded-full border border-[#493824] bg-[#1A1510] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[#D99A53]">
        Investigating
      </span>
    )
  }

  return (
    <span className="rounded-full border border-[#472F2F] bg-[#201414] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[#C97A7A]">
      Open
    </span>
  )
}


export default Incidents