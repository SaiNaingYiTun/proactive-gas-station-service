import {
  Bell,
  ChevronDown,
  CircleUserRound,
} from 'lucide-react'

import Sidebar from '../components/Sidebar.jsx'

function AppLayout({ children }) {
  return (
    <div className="min-h-screen bg-transparent text-[#F4F5F6]">

      <Sidebar />


      <div className="ml-72 min-h-screen">

        {/* Top Navigation */}
        <header className="sticky top-0 z-30 flex h-[76px] items-center justify-between border-b border-[#20252B] bg-[#0B0D10]/90 px-8 backdrop-blur-xl">

          <div>

            <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-[#5F6771]">
              Proactive Gas Station
            </p>

            <p className="mt-1 text-sm font-medium text-[#B9BFC6]">
              Operations Console
            </p>

          </div>


          <div className="flex items-center gap-3">

            {/* Live status */}
            <div className="hidden items-center gap-2 rounded-full border border-[#273129] bg-[#111A14] px-3 py-2 md:flex">

              <span className="h-1.5 w-1.5 rounded-full bg-[#5D9B73]"></span>

              <span className="text-[11px] font-medium text-[#7CB18D]">
                Live System
              </span>

            </div>


            {/* Notification */}
            <button
              type="button"
              className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-[#252A30] bg-[#111419] text-[#858D97] transition hover:border-[#343A42] hover:text-white"
            >
              <Bell size={17} />

              <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-[#D98A32]"></span>
            </button>


            {/* User */}
            <button
              type="button"
              className="flex items-center gap-3 rounded-lg border border-[#252A30] bg-[#111419] px-3 py-2 transition hover:border-[#343A42]"
            >

              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-[#1D2228] text-[#AEB4BB]">
                <CircleUserRound size={18} />
              </div>


              <div className="hidden text-left sm:block">

                <p className="text-xs font-medium text-[#E7E9EB]">
                  Admin User
                </p>

                <p className="mt-0.5 text-[10px] text-[#68717A]">
                  Station Staff
                </p>

              </div>

              <ChevronDown
                size={14}
                className="text-[#626A74]"
              />

            </button>

          </div>

        </header>


        {/* Main Content */}
        <main className="px-8 py-8">
          {children}
        </main>

      </div>

    </div>
  )
}

export default AppLayout