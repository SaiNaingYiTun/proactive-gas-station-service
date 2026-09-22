import {
  ArrowLeft,
  CalendarDays,
  CarFront,
  CreditCard,
  Droplets,
  Mail,
  Phone,
  ReceiptText,
  Sparkles,
  TriangleAlert,
  UserRound,
} from 'lucide-react'

import { useNavigate, useParams } from 'react-router'

import { customers } from '../data/mockCustomers.js'


function CustomerDetails() {
  const navigate = useNavigate()
  const { customerId } = useParams()

  const customer = customers.find(
    (customer) => customer.id === customerId
  )


  if (!customer) {
    return (
      <div className="mx-auto max-w-[1600px]">

        <div className="rounded-2xl border border-[#432D2D] bg-[#151112] p-8">

          <TriangleAlert
            size={24}
            className="text-[#C96E6E]"
          />

          <h2 className="mt-5 text-2xl font-semibold text-[#F2F3F4]">
            Customer Not Found
          </h2>

          <p className="mt-2 text-sm text-[#727A84]">
            The requested customer record could not be located.
          </p>

          <button
            type="button"
            onClick={() => navigate('/customers')}
            className="mt-6 flex items-center gap-2 rounded-lg bg-[#D98A32] px-4 py-2.5 text-xs font-bold text-[#0B0D10]"
          >
            <ArrowLeft size={14} />

            Back to Customers
          </button>

        </div>

      </div>
    )
  }


  return (
    <div className="mx-auto max-w-[1600px]">

      {/* BACK */}
      <button
        type="button"
        onClick={() => navigate('/customers')}
        className="flex items-center gap-2 text-xs font-semibold text-[#777F88] transition hover:text-[#D98A32]"
      >
        <ArrowLeft size={15} />

        Back to Customers
      </button>



      {/* ================================================= */}
      {/* CUSTOMER HEADER */}
      {/* ================================================= */}

      <div className="mt-7 flex flex-col justify-between gap-6 lg:flex-row lg:items-end">

        <div>

          <div className="flex items-center gap-2">

            <span className="h-px w-6 bg-[#D98A32]"></span>

            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#D98A32]">
              Customer Profile
            </p>

          </div>


          <div className="mt-4 flex items-center gap-4">

            <div className="flex h-16 w-16 items-center justify-center rounded-xl border border-[#3C342A] bg-[#211A13] text-lg font-semibold text-[#D98A32]">
              {getInitials(customer.name)}
            </div>


            <div>

              <h2 className="text-3xl font-semibold tracking-[-0.035em] text-[#F5F6F7]">
                {customer.name}
              </h2>

              <div className="mt-2 flex items-center gap-3">

                <span className="font-mono text-xs text-[#68717A]">
                  {customer.id}
                </span>

                <span className="h-1 w-1 rounded-full bg-[#444B53]"></span>

                <span className="rounded-full border border-[#493824] bg-[#1A1510] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-[#D99A53]">
                  {customer.status}
                </span>

              </div>

            </div>

          </div>

        </div>


        {/* QUICK STATS */}
        <div className="flex gap-3">

          <QuickStat
            label="Total Visits"
            value={customer.totalVisits}
          />

          <QuickStat
            label="Last Visit"
            value={customer.lastVisit}
            small
          />

        </div>

      </div>



      {/* ================================================= */}
      {/* CONTACT + VEHICLE */}
      {/* ================================================= */}

      <div className="mt-8 grid gap-6 xl:grid-cols-2">

        {/* CONTACT */}
        <section className="overflow-hidden rounded-2xl border border-[#252A30] bg-[#111419]">

          <SectionHeader
            icon={UserRound}
            title="Contact Information"
            subtitle="Registered customer details"
          />


          <div className="space-y-5 p-6">

            <InfoRow
              icon={Phone}
              label="Phone"
              value={customer.phone}
            />

            <InfoRow
              icon={Mail}
              label="Email"
              value={customer.email}
            />

            <InfoRow
              icon={CalendarDays}
              label="Total Visits"
              value={customer.totalVisits}
            />

            <InfoRow
              icon={CalendarDays}
              label="Last Visit"
              value={customer.lastVisit}
            />

          </div>

        </section>


        {/* VEHICLE */}
        <section className="overflow-hidden rounded-2xl border border-[#252A30] bg-[#111419]">

          <SectionHeader
            icon={CarFront}
            title="Registered Vehicle"
            subtitle="Vehicle linked to customer profile"
          />


          <div className="p-6">

            {/* Plate */}
            <div className="rounded-xl border border-[#34302A] bg-[#0B0D10] p-5">

              <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[#5F6770]">
                License Plate
              </p>

              <p className="mt-3 font-mono text-2xl font-semibold tracking-[0.08em] text-[#F2F3F4]">
                {customer.vehicle.licensePlate}
              </p>

            </div>


            <div className="mt-6 grid grid-cols-3 gap-4">

              <VehicleDetail
                label="Make"
                value={customer.vehicle.make}
              />

              <VehicleDetail
                label="Model"
                value={customer.vehicle.model}
              />

              <VehicleDetail
                label="Color"
                value={customer.vehicle.color}
              />

            </div>

          </div>

        </section>

      </div>



      {/* ================================================= */}
      {/* CUSTOMER PREFERENCES */}
      {/* ================================================= */}

      <section className="mt-6 overflow-hidden rounded-2xl border border-[#252A30] bg-[#111419]">

        <SectionHeader
          icon={Sparkles}
          title="Customer Preferences"
          subtitle="Stored service preferences for faster personalized service"
        />


        <div className="grid gap-px bg-[#24292F] md:grid-cols-2 xl:grid-cols-4">

          <PreferenceCard
            icon={Droplets}
            label="Preferred Fuel"
            value={customer.preferences.fuel}
            accent
          />

          <PreferenceCard
            icon={CreditCard}
            label="Payment Method"
            value={customer.preferences.payment}
          />

          <PreferenceCard
            icon={CarFront}
            label="Car Wash"
            value={customer.preferences.carWash}
          />

          <PreferenceCard
            icon={Sparkles}
            label="Favorite Service"
            value={customer.preferences.favoriteService}
          />

        </div>

      </section>



      {/* ================================================= */}
      {/* PURCHASE HISTORY */}
      {/* ================================================= */}

      <section className="mt-6 overflow-hidden rounded-2xl border border-[#252A30] bg-[#111419]">

        <div className="flex items-center justify-between border-b border-[#24292F] px-6 py-5">

          <div className="flex items-start gap-3">

            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-[#34302A] bg-[#1D1813]">

              <ReceiptText
                size={16}
                className="text-[#D98A32]"
              />

            </div>


            <div>

              <h3 className="text-sm font-semibold text-[#ECEDEF]">
                Purchase History
              </h3>

              <p className="mt-1 text-xs text-[#69717B]">
                Previous fuel purchases made by this customer.
              </p>

            </div>

          </div>


          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-[#555E67]">
            {customer.purchaseHistory.length} records
          </span>

        </div>


        {customer.purchaseHistory.length === 0 ? (

          <div className="py-14 text-center">

            <ReceiptText
              size={22}
              className="mx-auto text-[#4E565F]"
            />

            <p className="mt-4 text-sm font-medium text-[#A8AEB5]">
              No purchase history
            </p>

            <p className="mt-1 text-xs text-[#5F6770]">
              Purchases will appear here after the customer's first transaction.
            </p>

          </div>

        ) : (

          <div className="overflow-x-auto">

            <table className="w-full">

              <thead className="bg-[#0E1114]">

                <tr>
                  <Heading>Date</Heading>
                  <Heading>Fuel Type</Heading>
                  <Heading>Amount</Heading>
                  <Heading>Payment</Heading>
                </tr>

              </thead>


              <tbody className="divide-y divide-[#20252B]">

                {customer.purchaseHistory.map((purchase) => (

                  <tr
                    key={purchase.id}
                    className="transition hover:bg-[#15191E]"
                  >

                    <td className="px-6 py-4 font-mono text-xs text-[#747C85]">
                      {purchase.date}
                    </td>


                    <td className="px-6 py-4">

                      <div className="flex items-center gap-2">

                        <Droplets
                          size={14}
                          className="text-[#D98A32]"
                        />

                        <span className="text-sm text-[#B9BEC4]">
                          {purchase.fuel}
                        </span>

                      </div>

                    </td>


                    <td className="px-6 py-4">

                      <span className="font-mono text-sm font-semibold text-[#ECEDEF]">
                        ฿{purchase.amount.toLocaleString()}
                      </span>

                    </td>


                    <td className="px-6 py-4">

                      <div className="flex items-center gap-2">

                        <CreditCard
                          size={14}
                          className="text-[#616A74]"
                        />

                        <span className="text-sm text-[#898F97]">
                          {purchase.payment}
                        </span>

                      </div>

                    </td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>

        )}

      </section>



      {/* ================================================= */}
      {/* INCIDENTS */}
      {/* ================================================= */}

      <section className="mt-6 overflow-hidden rounded-2xl border border-[#252A30] bg-[#111419]">

        <SectionHeader
          icon={TriangleAlert}
          title="Customer Incidents"
          subtitle="Complaints and service incidents linked to this customer"
        />


        <div className="p-6">

          {customer.incidents.length === 0 ? (

            <div className="flex items-center justify-between rounded-xl border border-[#28352D] bg-[#111914] p-5">

              <div>

                <p className="text-sm font-medium text-[#A9C4B1]">
                  No active incidents
                </p>

                <p className="mt-1 text-xs text-[#657A6B]">
                  No complaints or service incidents recorded.
                </p>

              </div>


              <div className="flex h-9 w-9 items-center justify-center rounded-full border border-[#304639] bg-[#162219]">

                <span className="h-2 w-2 rounded-full bg-[#5D9B73]"></span>

              </div>

            </div>

          ) : (

            <div className="space-y-4">

              {customer.incidents.map((incident) => (

                <div
                  key={incident.id}
                  className="rounded-xl border border-[#3E2E2B] bg-[#181212] p-5"
                >

                  <div className="flex items-start justify-between gap-5">

                    <div>

                      <div className="flex items-center gap-3">

                        <TriangleAlert
                          size={16}
                          className="text-[#C96E6E]"
                        />

                        <p className="text-sm font-semibold text-[#E6E8EA]">
                          {incident.type}
                        </p>

                      </div>


                      <p className="mt-3 text-xs leading-5 text-[#7E858D]">
                        {incident.note}
                      </p>


                      <p className="mt-3 font-mono text-[10px] text-[#565E67]">
                        {incident.date} · {incident.id}
                      </p>

                    </div>


                    <span className="rounded-full border border-[#472F2F] bg-[#201414] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[#C97A7A]">
                      {incident.status}
                    </span>

                  </div>

                </div>

              ))}

            </div>

          )}

        </div>

      </section>

    </div>
  )
}



/* ========================================================= */
/* COMPONENTS */
/* ========================================================= */


function SectionHeader({
  icon: Icon,
  title,
  subtitle,
}) {
  return (
    <div className="flex items-start gap-3 border-b border-[#24292F] px-6 py-5">

      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[#34302A] bg-[#1D1813]">

        <Icon
          size={16}
          strokeWidth={1.7}
          className="text-[#D98A32]"
        />

      </div>


      <div>

        <h3 className="text-sm font-semibold text-[#ECEDEF]">
          {title}
        </h3>

        <p className="mt-1 text-xs text-[#69717B]">
          {subtitle}
        </p>

      </div>

    </div>
  )
}


function InfoRow({
  icon: Icon,
  label,
  value,
}) {
  return (
    <div className="flex items-center justify-between gap-6">

      <div className="flex items-center gap-3">

        <Icon
          size={15}
          strokeWidth={1.7}
          className="text-[#616A74]"
        />

        <span className="text-xs text-[#777F89]">
          {label}
        </span>

      </div>


      <span className="text-right text-sm font-medium text-[#D3D6D9]">
        {value}
      </span>

    </div>
  )
}


function VehicleDetail({
  label,
  value,
}) {
  return (
    <div className="rounded-lg border border-[#252A30] bg-[#0E1114] p-4">

      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#555E67]">
        {label}
      </p>

      <p className="mt-2 text-sm font-medium text-[#D5D8DB]">
        {value}
      </p>

    </div>
  )
}


function PreferenceCard({
  icon: Icon,
  label,
  value,
  accent = false,
}) {
  return (
    <div className="bg-[#111419] p-6">

      <div className="flex items-center gap-2">

        <Icon
          size={14}
          className={
            accent
              ? 'text-[#D98A32]'
              : 'text-[#626A74]'
          }
        />

        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#5F6770]">
          {label}
        </p>

      </div>


      <p
        className={`mt-4 text-sm font-semibold ${
          accent
            ? 'text-[#D98A32]'
            : 'text-[#D9DCDF]'
        }`}
      >
        {value}
      </p>

    </div>
  )
}


function QuickStat({
  label,
  value,
  small = false,
}) {
  return (
    <div className="min-w-32 rounded-xl border border-[#252A30] bg-[#111419] px-4 py-3">

      <p className="text-[9px] font-semibold uppercase tracking-[0.14em] text-[#555E67]">
        {label}
      </p>

      <p
        className={`mt-2 font-semibold text-[#E4E6E8] ${
          small
            ? 'text-xs'
            : 'font-mono text-lg'
        }`}
      >
        {value}
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


export default CustomerDetails