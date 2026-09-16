import { useState } from 'react'
import { useNavigate } from 'react-router'

import {
  ArrowUpRight,
  CarFront,
  Search,
  UserRoundCheck,
  Users,
} from 'lucide-react'

import { customers } from '../data/mockCustomers.js'


function Customers() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')

  const filteredCustomers = customers.filter((customer) => {
    const value = search.toLowerCase()

    return (
      customer.name.toLowerCase().includes(value) ||
      customer.phone.toLowerCase().includes(value) ||
      customer.vehicle.licensePlate.toLowerCase().includes(value)
    )
  })

  const totalVisits = customers.reduce(
    (total, customer) => total + customer.totalVisits,
    0
  )

  return (
    <div className="mx-auto max-w-[1600px]">

      {/* HEADER */}
      <div>

        <div className="flex items-center gap-2">
          <span className="h-px w-6 bg-[#D98A32]"></span>

          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#D98A32]">
            Customer Intelligence
          </p>
        </div>

        <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-[#F5F6F7]">
          Customers
        </h2>

        <p className="mt-2 text-sm text-[#727A84]">
          Customer profiles, vehicle ownership and service preferences.
        </p>

      </div>


      {/* METRICS */}
      <div className="mt-8 grid gap-4 md:grid-cols-3">

        <MetricCard
          icon={Users}
          label="Total Customers"
          value={customers.length}
          description="Registered customer profiles"
        />

        <MetricCard
          icon={UserRoundCheck}
          label="Returning"
          value={
            customers.filter(
              (customer) => customer.status === 'Returning'
            ).length
          }
          description="Recognized returning customers"
          accent
        />

        <MetricCard
          icon={CarFront}
          label="Recorded Visits"
          value={totalVisits}
          description="Combined customer visits"
        />

      </div>


      {/* DIRECTORY */}
      <section className="mt-6 overflow-hidden rounded-2xl border border-[#252A30] bg-[#111419]">

        <div className="flex flex-col gap-4 border-b border-[#24292F] px-6 py-5 md:flex-row md:items-center md:justify-between">

          <div>

            <h3 className="text-sm font-semibold text-[#ECEDEF]">
              Customer Directory
            </h3>

            <p className="mt-1.5 text-xs text-[#69717B]">
              Search by customer name, phone number or license plate.
            </p>

          </div>


          <div className="relative w-full md:w-80">

            <Search
              size={15}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[#555E67]"
            />

            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search customers..."
              className="w-full rounded-lg border border-[#292E34] bg-[#0D1013] py-2.5 pl-10 pr-4 text-xs text-[#D9DCDF] outline-none transition placeholder:text-[#505861] focus:border-[#D98A32]/60"
            />

          </div>

        </div>


        <div className="overflow-x-auto">

          <table className="w-full">

            <thead className="bg-[#0E1114]">

              <tr>
                <Heading>Customer</Heading>
                <Heading>Phone</Heading>
                <Heading>Vehicle</Heading>
                <Heading>License Plate</Heading>
                <Heading>Visits</Heading>
                <Heading>Status</Heading>
                <th className="px-6 py-3"></th>
              </tr>

            </thead>


            <tbody className="divide-y divide-[#20252B]">

              {filteredCustomers.map((customer) => (

                <tr
                  key={customer.id}
                  className="transition hover:bg-[#15191E]"
                >

                  <td className="px-6 py-4">

                    <div className="flex items-center gap-3">

                      <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-[#34302A] bg-[#201A14] text-xs font-semibold text-[#D98A32]">
                        {getInitials(customer.name)}
                      </div>

                      <div>

                        <p className="text-sm font-medium text-[#ECEDEF]">
                          {customer.name}
                        </p>

                        <p className="mt-1 text-xs text-[#5F6770]">
                          {customer.id}
                        </p>

                      </div>

                    </div>

                  </td>


                  <td className="px-6 py-4 text-sm text-[#858D97]">
                    {customer.phone}
                  </td>


                  <td className="px-6 py-4">

                    <p className="text-sm text-[#B7BCC2]">
                      {customer.vehicle.make} {customer.vehicle.model}
                    </p>

                    <p className="mt-1 text-xs text-[#59616A]">
                      {customer.vehicle.color}
                    </p>

                  </td>


                  <td className="px-6 py-4 font-mono text-sm font-semibold tracking-wide text-[#D7DADD]">
                    {customer.vehicle.licensePlate}
                  </td>


                  <td className="px-6 py-4 font-mono text-sm text-[#8B929B]">
                    {customer.totalVisits}
                  </td>


                  <td className="px-6 py-4">

                    <span className="inline-flex rounded-full border border-[#493824] bg-[#1A1510] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-[#D99A53]">
                      {customer.status}
                    </span>

                  </td>


                  <td className="px-6 py-4">

                    <button
                      type="button"
                      onClick={() =>
                        navigate(`/customers/${customer.id}`)
                      }
                      className="flex items-center gap-1.5 text-xs font-semibold text-[#D98A32] transition hover:text-[#E8A757]"
                    >
                      View

                      <ArrowUpRight size={13} />
                    </button>

                  </td>

                </tr>

              ))}

            </tbody>

          </table>

        </div>


        {filteredCustomers.length === 0 && (
          <div className="py-16 text-center">

            <p className="text-sm font-medium text-[#B8BDC3]">
              No matching customers
            </p>

            <p className="mt-2 text-xs text-[#626A74]">
              Try another name, phone number or license plate.
            </p>

          </div>
        )}

      </section>

    </div>
  )
}


function MetricCard({
  icon: Icon,
  label,
  value,
  description,
  accent = false,
}) {
  return (
    <div
      className={`relative overflow-hidden rounded-2xl border bg-[#111419] p-5 ${
        accent
          ? 'border-[#493824]'
          : 'border-[#252A30]'
      }`}
    >

      {accent && (
        <div className="absolute inset-x-0 top-0 h-px bg-[#D98A32]" />
      )}

      <div className="flex items-start justify-between">

        <div>

          <p className="text-xs text-[#747C85]">
            {label}
          </p>

          <p
            className={`mt-3 text-3xl font-semibold tracking-[-0.04em] ${
              accent
                ? 'text-[#D98A32]'
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
                : 'text-[#707984]'
            }
          />

        </div>

      </div>

      <p className="mt-4 text-[11px] text-[#5F6770]">
        {description}
      </p>

    </div>
  )
}


function Heading({ children }) {
  return (
    <th className="px-6 py-3.5 text-left text-[10px] font-semibold uppercase tracking-[0.15em] text-[#555E67]">
      {children}
    </th>
  )
}


function getInitials(name) {
  return name
    .split(' ')
    .map((word) => word[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}


export default Customers