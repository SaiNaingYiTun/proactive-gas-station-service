import {
  Activity,
  CarFront,
  ScanLine,
  TrendingUp,
  Users,
} from 'lucide-react'


const trafficData = [
  { day: 'Mon', value: 54 },
  { day: 'Tue', value: 72 },
  { day: 'Wed', value: 61 },
  { day: 'Thu', value: 82 },
  { day: 'Fri', value: 94 },
  { day: 'Sat', value: 78 },
  { day: 'Sun', value: 67 },
]


const fuelData = [
  {
    name: 'Gasohol 95',
    percent: 44,
  },
  {
    name: 'Diesel',
    percent: 29,
  },
  {
    name: 'Gasohol 91',
    percent: 18,
  },
  {
    name: 'Premium',
    percent: 9,
  },
]


const frequencyData = [
  {
    label: 'Frequent',
    description: '2+ visits per week',
    value: 38,
  },
  {
    label: 'Regular',
    description: '1–3 visits per month',
    value: 43,
  },
  {
    label: 'Occasional',
    description: 'Less than once per month',
    value: 19,
  },
]


function Analytics() {
  return (
    <div className="mx-auto max-w-[1600px]">

      {/* HEADER */}
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
          Traffic patterns, recognition activity and customer behavior.
        </p>

      </div>


      {/* KPI */}
      <div className="mt-8 grid gap-4 md:grid-cols-4">

        <AnalyticsMetric
          icon={CarFront}
          label="Vehicles Today"
          value="48"
          change="+12%"
        />

        <AnalyticsMetric
          icon={Users}
          label="Returning Customers"
          value="31"
          change="64.6%"
        />

        <AnalyticsMetric
          icon={ScanLine}
          label="Recognition Rate"
          value="96.8%"
          change="+1.4%"
          accent
        />

        <AnalyticsMetric
          icon={Activity}
          label="Average Visits"
          value="4.7"
          change="+0.6"
        />

      </div>


      {/* MAIN CHARTS */}
      <div className="mt-6 grid gap-6 xl:grid-cols-12">

        {/* TRAFFIC */}
        <section className="rounded-2xl border border-[#252A30] bg-[#111419] p-6 xl:col-span-8">

          <div className="flex items-start justify-between">

            <div>

              <h3 className="text-sm font-semibold text-[#ECEDEF]">
                Vehicle Traffic
              </h3>

              <p className="mt-1.5 text-xs text-[#69717B]">
                Vehicles detected over the last seven days
              </p>

            </div>


            <div className="flex items-center gap-2">

              <TrendingUp
                size={15}
                className="text-[#D98A32]"
              />

              <span className="text-xs font-semibold text-[#D98A32]">
                +8.4%
              </span>

            </div>

          </div>


          <div className="mt-10 flex h-64 items-end gap-4 border-b border-[#292E34]">

            {trafficData.map((item) => (

              <div
                key={item.day}
                className="flex h-full flex-1 flex-col justify-end"
              >

                <div className="group relative flex flex-1 items-end justify-center">

                  <div
                    className="w-full max-w-14 rounded-t-md bg-gradient-to-t from-[#6F431C] to-[#D98A32] transition-all duration-300 group-hover:brightness-110"
                    style={{
                      height: `${item.value}%`,
                    }}
                  />


                  <div className="absolute bottom-[calc(100%+8px)] hidden rounded-md border border-[#32373D] bg-[#171A1F] px-2 py-1 font-mono text-[10px] text-[#D5D8DB] group-hover:block">
                    {item.value}
                  </div>

                </div>


                <p className="py-3 text-center font-mono text-[10px] uppercase text-[#606872]">
                  {item.day}
                </p>

              </div>

            ))}

          </div>

        </section>


        {/* FUEL */}
        <section className="rounded-2xl border border-[#252A30] bg-[#111419] p-6 xl:col-span-4">

          <h3 className="text-sm font-semibold text-[#ECEDEF]">
            Fuel Preference
          </h3>

          <p className="mt-1.5 text-xs text-[#69717B]">
            Most frequently selected fuel types
          </p>


          <div className="mt-8 space-y-6">

            {fuelData.map((fuel) => (

              <div key={fuel.name}>

                <div className="flex items-center justify-between">

                  <p className="text-xs text-[#9BA2AA]">
                    {fuel.name}
                  </p>

                  <p className="font-mono text-xs font-semibold text-[#D7DADD]">
                    {fuel.percent}%
                  </p>

                </div>


                <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-[#22272D]">

                  <div
                    className="h-full rounded-full bg-[#D98A32]"
                    style={{
                      width: `${fuel.percent}%`,
                    }}
                  />

                </div>

              </div>

            ))}

          </div>

        </section>

      </div>


      {/* SECOND ROW */}
      <div className="mt-6 grid gap-6 xl:grid-cols-2">

        {/* CUSTOMER FREQUENCY */}
        <section className="rounded-2xl border border-[#252A30] bg-[#111419] p-6">

          <h3 className="text-sm font-semibold text-[#ECEDEF]">
            Customer Visit Frequency
          </h3>

          <p className="mt-1.5 text-xs text-[#69717B]">
            Customer segments based on station visit frequency.
          </p>


          <div className="mt-7 space-y-4">

            {frequencyData.map((item) => (

              <div
                key={item.label}
                className="rounded-xl border border-[#252A30] bg-[#0E1114] p-4"
              >

                <div className="flex items-center justify-between">

                  <div>

                    <p className="text-sm font-medium text-[#D5D8DB]">
                      {item.label}
                    </p>

                    <p className="mt-1 text-[11px] text-[#626A74]">
                      {item.description}
                    </p>

                  </div>


                  <p className="font-mono text-xl font-semibold text-[#D98A32]">
                    {item.value}%
                  </p>

                </div>

              </div>

            ))}

          </div>

        </section>


        {/* SYSTEM PERFORMANCE */}
        <section className="rounded-2xl border border-[#252A30] bg-[#111419] p-6">

          <h3 className="text-sm font-semibold text-[#ECEDEF]">
            Recognition Performance
          </h3>

          <p className="mt-1.5 text-xs text-[#69717B]">
            Current AI detection and customer matching performance.
          </p>


          <div className="mt-7">

            <PerformanceRow
              label="Vehicle Detection"
              value="98.2%"
              percent={98}
            />

            <PerformanceRow
              label="License Plate Recognition"
              value="96.8%"
              percent={97}
            />

            <PerformanceRow
              label="Customer Matching"
              value="92.4%"
              percent={92}
            />

            <PerformanceRow
              label="Camera Availability"
              value="100%"
              percent={100}
              healthy
            />

          </div>

        </section>

      </div>

    </div>
  )
}


function AnalyticsMetric({
  icon: Icon,
  label,
  value,
  change,
  accent,
}) {
  return (
    <div
      className={`rounded-2xl border bg-[#111419] p-5 ${
        accent
          ? 'border-[#493824]'
          : 'border-[#252A30]'
      }`}
    >

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


        <Icon
          size={19}
          strokeWidth={1.7}
          className={
            accent
              ? 'text-[#D98A32]'
              : 'text-[#707984]'
          }
        />

      </div>


      <p className="mt-4 font-mono text-[10px] text-[#686F78]">
        {change}
      </p>

    </div>
  )
}


function PerformanceRow({
  label,
  value,
  percent,
  healthy,
}) {
  return (
    <div className="border-b border-[#22272D] py-5 first:pt-0 last:border-b-0">

      <div className="flex items-center justify-between">

        <p className="text-xs text-[#969DA5]">
          {label}
        </p>

        <p
          className={`font-mono text-xs font-semibold ${
            healthy
              ? 'text-[#75A986]'
              : 'text-[#D98A32]'
          }`}
        >
          {value}
        </p>

      </div>


      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[#22272D]">

        <div
          className={`h-full rounded-full ${
            healthy
              ? 'bg-[#5D9B73]'
              : 'bg-[#D98A32]'
          }`}
          style={{
            width: `${percent}%`,
          }}
        />

      </div>

    </div>
  )
}


export default Analytics