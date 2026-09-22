import {
  Activity,
  ArrowUpRight,
  Camera,
  CarFront,
  Clock3,
  CreditCard,
  Droplets,
  ScanLine,
  Sparkles,
  UserRound,
} from 'lucide-react'

import { useNavigate } from 'react-router'

import {
  currentDetection,
  recentDetections,
} from '../data/mockDetections.js'


function LiveDetection() {
  const navigate = useNavigate()

  function openCustomerProfile() {
    if (currentDetection.customerId) {
      navigate(`/customers/${currentDetection.customerId}`)
    } else {
      navigate('/customers')
    }
  }

  return (
    <div className="mx-auto max-w-[1600px]">

      {/* PAGE HEADER */}
      <div className="flex items-end justify-between gap-6">

        <div>

          <div className="flex items-center gap-2">

            <span className="h-px w-6 bg-[#D98A32]"></span>

            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#D98A32]">
              Vehicle Recognition
            </p>

          </div>


          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-[#F5F6F7]">
            Live Detection
          </h2>


          <p className="mt-2 text-sm text-[#727A84]">
            Monitor incoming vehicles and identify returning customers in real time.
          </p>

        </div>


        {/* Detection Status */}
        <div className="flex items-center gap-3 rounded-lg border border-[#493824] bg-[#1A1510] px-4 py-2.5">

          <span className="relative flex h-2.5 w-2.5">

            <span className="absolute h-full w-full animate-ping rounded-full bg-[#D98A32] opacity-30"></span>

            <span className="relative h-2.5 w-2.5 rounded-full bg-[#D98A32]"></span>

          </span>

          <span className="text-xs font-semibold text-[#E1A35E]">
            Detection Active
          </span>

        </div>

      </div>



      {/* MAIN GRID */}
      <div className="mt-8 grid gap-6 xl:grid-cols-12">

        {/* ================================================= */}
        {/* CAMERA */}
        {/* ================================================= */}

        <section className="overflow-hidden rounded-2xl border border-[#252A30] bg-[#111419] xl:col-span-8">

          {/* Camera header */}
          <div className="flex items-center justify-between border-b border-[#24292F] px-6 py-5">

            <div className="flex items-center gap-3">

              <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#34302A] bg-[#1D1813]">

                <Camera
                  size={18}
                  strokeWidth={1.7}
                  className="text-[#D98A32]"
                />

              </div>


              <div>

                <h3 className="text-sm font-semibold text-[#ECEDEF]">
                  Entrance Camera
                </h3>

                <p className="mt-1 text-xs text-[#69717B]">
                  Camera 01 · Main Entrance
                </p>

              </div>

            </div>


            {/* LIVE indicator */}
            <div className="flex items-center gap-2">

              <span className="relative flex h-2 w-2">

                <span className="absolute h-full w-full animate-ping rounded-full bg-[#C45F5F] opacity-40"></span>

                <span className="relative h-2 w-2 rounded-full bg-[#C45F5F]"></span>

              </span>

              <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-[#858D97]">
                LIVE
              </span>

            </div>

          </div>



          {/* Camera feed */}
          <div className="relative flex min-h-[470px] items-center justify-center overflow-hidden bg-[#0B0D10]">

            {/* subtle grid */}
            <div
              className="absolute inset-0 opacity-[0.07]"
              style={{
                backgroundImage:
                  'linear-gradient(#ffffff 1px, transparent 1px), linear-gradient(90deg, #ffffff 1px, transparent 1px)',
                backgroundSize: '40px 40px',
              }}
            />


            {/* camera label */}
            <div className="absolute left-6 top-6 flex items-center gap-2 rounded-lg border border-[#282D33] bg-[#111419]/90 px-3 py-2 backdrop-blur">

              <Camera
                size={13}
                className="text-[#777F88]"
              />

              <span className="font-mono text-[10px] text-[#A3A9B0]">
                CAM_01
              </span>

            </div>


            {/* Time */}
            <div className="absolute right-6 top-6">

              <span className="font-mono text-[11px] text-[#626A74]">
                {currentDetection.detectedAt}
              </span>

            </div>



            {/* Scan line */}
            <div className="absolute left-[20%] right-[20%] top-[50%] h-px bg-gradient-to-r from-transparent via-[#D98A32]/60 to-transparent shadow-[0_0_15px_rgba(217,138,50,0.35)]" />



            {/* DETECTION BOX */}
            <div className="relative flex h-56 w-[420px] items-center justify-center">

              {/* corners */}
              <span className="absolute left-0 top-0 h-10 w-10 border-l-2 border-t-2 border-[#D98A32]" />

              <span className="absolute right-0 top-0 h-10 w-10 border-r-2 border-t-2 border-[#D98A32]" />

              <span className="absolute bottom-0 left-0 h-10 w-10 border-b-2 border-l-2 border-[#D98A32]" />

              <span className="absolute bottom-0 right-0 h-10 w-10 border-b-2 border-r-2 border-[#D98A32]" />


              {/* detected badge */}
              <div className="absolute -top-4 left-0 flex items-center gap-2 bg-[#D98A32] px-3 py-1.5">

                <ScanLine
                  size={12}
                  className="text-[#0B0D10]"
                />

                <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#0B0D10]">
                  Vehicle Detected
                </span>

              </div>


              {/* plate */}
              <div className="text-center">

                <p className="text-[10px] font-semibold uppercase tracking-[0.25em] text-[#646D77]">
                  License Plate
                </p>

                <p className="mt-4 font-mono text-4xl font-semibold tracking-[0.09em] text-[#F6F7F8]">
                  {currentDetection.licensePlate}
                </p>


                <div className="mt-5 flex items-center justify-center gap-2">

                  <Sparkles
                    size={13}
                    className="text-[#D98A32]"
                  />

                  <span className="font-mono text-[11px] text-[#8A919A]">
                    {currentDetection.confidence}% MATCH CONFIDENCE
                  </span>

                </div>

              </div>

            </div>



            {/* processing */}
            <div className="absolute bottom-6 right-6 flex items-center gap-2 rounded-lg border border-[#332D25] bg-[#18140F]/90 px-3 py-2">

              <Activity
                size={13}
                className="text-[#D98A32]"
              />

              <span className="text-[10px] font-medium text-[#C78D50]">
                AI PROCESSING
              </span>

            </div>

          </div>



          {/* Camera statistics */}
          <div className="grid grid-cols-3 divide-x divide-[#24292F] border-t border-[#24292F] bg-[#0E1114]">

            <DetectionStat
              icon={CarFront}
              label="License Plate"
              value={currentDetection.licensePlate}
            />

            <DetectionStat
              icon={ScanLine}
              label="AI Confidence"
              value={`${currentDetection.confidence}%`}
              accent
            />

            <DetectionStat
              icon={Clock3}
              label="Detection Time"
              value={currentDetection.detectedAt}
            />

          </div>

        </section>



        {/* ================================================= */}
        {/* CUSTOMER MATCH */}
        {/* ================================================= */}

        <section className="overflow-hidden rounded-2xl border border-[#252A30] bg-[#111419] xl:col-span-4">

          {/* header */}
          <div className="border-b border-[#24292F] px-6 py-5">

            <div className="flex items-start justify-between gap-3">

              <div>

                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#D98A32]">
                  Recognition Result
                </p>

                <h3 className="mt-2 text-base font-semibold text-[#ECEDEF]">
                  Customer Match
                </h3>

              </div>


              <span className="rounded-full border border-[#493824] bg-[#1C1610] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-[#D99A53]">
                Returning
              </span>

            </div>


            <p className="mt-2 text-xs text-[#69717B]">
              Customer record linked to detected vehicle
            </p>

          </div>



          <div className="p-6">

            {/* CUSTOMER */}
            <div className="flex items-center gap-4">

              <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-[#34302A] bg-[#201A14] text-base font-semibold text-[#D98A32]">
                JD
              </div>


              <div>

                <p className="text-base font-semibold text-[#F0F1F2]">
                  {currentDetection.customer.name}
                </p>

                <p className="mt-1 text-sm text-[#858D97]">
                  {currentDetection.vehicle}
                </p>

                <p className="mt-1 text-xs text-[#59616A]">
                  {currentDetection.vehicleColor}
                </p>

              </div>

            </div>



            <div className="my-6 h-px bg-[#252A30]" />



            {/* DETAILS */}
            <div className="space-y-5">

              <CustomerInfo
                icon={Droplets}
                label="Preferred Fuel"
                value={currentDetection.customer.preferredFuel}
              />

              <CustomerInfo
                icon={CreditCard}
                label="Payment"
                value={currentDetection.customer.preferredPayment}
              />

              <CustomerInfo
                icon={CarFront}
                label="Car Wash"
                value={currentDetection.customer.carWash}
              />

              <CustomerInfo
                icon={UserRound}
                label="Total Visits"
                value={currentDetection.customer.totalVisits}
              />

              <CustomerInfo
                icon={Clock3}
                label="Last Visit"
                value={currentDetection.customer.lastVisit}
              />

            </div>



            {/* profile button */}
            <button
              type="button"
              onClick={openCustomerProfile}
              className="mt-7 flex w-full items-center justify-center gap-2 rounded-lg bg-[#D98A32] px-4 py-3 text-xs font-bold text-[#0B0D10] transition hover:bg-[#E39A45]"
            >
              View Customer Profile

              <ArrowUpRight size={15} />
            </button>

          </div>

        </section>

      </div>



      {/* ================================================= */}
      {/* RECENT DETECTIONS */}
      {/* ================================================= */}

      <section className="mt-6 overflow-hidden rounded-2xl border border-[#252A30] bg-[#111419]">

        <div className="flex items-center justify-between border-b border-[#24292F] px-6 py-5">

          <div>

            <div className="flex items-center gap-2">

              <Activity
                size={16}
                className="text-[#D98A32]"
              />

              <h3 className="text-sm font-semibold text-[#ECEDEF]">
                Recent Detection Activity
              </h3>

            </div>

            <p className="mt-1.5 text-xs text-[#69717B]">
              Latest vehicles captured at the station entrance.
            </p>

          </div>


          <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-[#565E67]">
            Real-time feed
          </p>

        </div>



        <div className="overflow-x-auto">

          <table className="w-full">

            <thead className="bg-[#0E1114]">

              <tr>

                <TableHeading>
                  Plate
                </TableHeading>

                <TableHeading>
                  Vehicle
                </TableHeading>

                <TableHeading>
                  Customer
                </TableHeading>

                <TableHeading>
                  Time
                </TableHeading>

                <TableHeading>
                  Recognition
                </TableHeading>

              </tr>

            </thead>


            <tbody className="divide-y divide-[#20252B]">

              {recentDetections.map((detection) => (

                <tr
                  key={detection.id}
                  className="transition hover:bg-[#15191E]"
                >

                  <td className="px-6 py-4">

                    <span className="font-mono text-sm font-semibold tracking-wide text-[#ECEDEF]">
                      {detection.licensePlate}
                    </span>

                  </td>


                  <td className="px-6 py-4 text-sm text-[#8B929B]">
                    {detection.vehicle}
                  </td>


                  <td className="px-6 py-4 text-sm text-[#A5ABB2]">
                    {detection.customer}
                  </td>


                  <td className="px-6 py-4">

                    <span className="font-mono text-xs text-[#68717A]">
                      {detection.time}
                    </span>

                  </td>


                  <td className="px-6 py-4">

                    <span
                      className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.1em] ${
                        detection.status === 'Returning'
                          ? 'border-[#493824] bg-[#1A1510] text-[#D99A53]'
                          : 'border-[#343A41] bg-[#181C20] text-[#808892]'
                      }`}
                    >
                      {detection.status}
                    </span>

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



/* ========================================================= */
/* SMALL COMPONENTS */
/* ========================================================= */


function DetectionStat({
  icon: Icon,
  label,
  value,
  accent = false,
}) {
  return (
    <div className="px-6 py-5">

      <div className="flex items-center gap-2">

        <Icon
          size={13}
          className={
            accent
              ? 'text-[#D98A32]'
              : 'text-[#626A74]'
          }
        />

        <p className="text-[10px] font-medium uppercase tracking-[0.13em] text-[#5E6670]">
          {label}
        </p>

      </div>


      <p
        className={`mt-2 font-mono text-sm font-semibold ${
          accent
            ? 'text-[#D98A32]'
            : 'text-[#D6D9DC]'
        }`}
      >
        {value}
      </p>

    </div>
  )
}


function CustomerInfo({
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


      <span className="text-right text-xs font-medium text-[#D3D6D9]">
        {value}
      </span>

    </div>
  )
}


function TableHeading({ children }) {
  return (
    <th className="px-6 py-3.5 text-left text-[10px] font-semibold uppercase tracking-[0.15em] text-[#555E67]">
      {children}
    </th>
  )
}


export default LiveDetection