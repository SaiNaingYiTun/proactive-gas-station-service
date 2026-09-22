import { useState } from 'react'

import {
  Bell,
  ChevronDown,
  CircleUserRound,
  LogOut,
} from 'lucide-react'

import { useNavigate } from 'react-router'

import Sidebar from '../components/Sidebar.jsx'
import { useBackendHealth } from '../lib/useBackendHealth.js'
import { getAccount, logout } from '../lib/auth.js'

function AppLayout({ children }) {
  const healthy = useBackendHealth()
  const account = getAccount()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

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

            {/* Live status -- a real check of /api/health, not a fixed "online" claim */}
            <div
              className={`hidden items-center gap-2 rounded-full border px-3 py-2 md:flex ${
                healthy === false ? 'border-[#472F2F] bg-[#201414]' : 'border-[#273129] bg-[#111A14]'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  healthy === null ? 'bg-[#555D67]' : healthy ? 'bg-[#5D9B73]' : 'bg-[#C45F5F]'
                }`}
              ></span>
              <span className={`text-[11px] font-medium ${healthy === false ? 'text-[#D58A8A]' : 'text-[#7CB18D]'}`}>
                {healthy === null ? 'Checking…' : healthy ? 'Live System' : 'Backend Unreachable'}
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
            <div className="relative">
              <button
                type="button"
                onClick={() => setMenuOpen((open) => !open)}
                className="flex items-center gap-3 rounded-lg border border-[#252A30] bg-[#111419] px-3 py-2 transition hover:border-[#343A42]"
              >

                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-[#1D2228] text-[#AEB4BB]">
                  <CircleUserRound size={18} />
                </div>


                <div className="hidden text-left sm:block">

                  <p className="text-xs font-medium text-[#E7E9EB]">
                    {account?.display_name ?? 'Signed out'}
                  </p>

                  <p className="mt-0.5 text-[10px] text-[#68717A]">
                    {account?.is_owner ? 'Owner' : 'Station Staff'}
                  </p>

                </div>

                <ChevronDown
                  size={14}
                  className={`text-[#626A74] transition ${menuOpen ? 'rotate-180' : ''}`}
                />

              </button>

              {menuOpen && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
                  <div className="absolute right-0 z-20 mt-2 w-44 overflow-hidden rounded-lg border border-[#252A30] bg-[#151A1F] shadow-xl">
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="flex w-full items-center gap-2 px-4 py-3 text-left text-xs font-medium text-[#D58A8A] transition hover:bg-[#1C2024]"
                    >
                      <LogOut size={14} />
                      Log out
                    </button>
                  </div>
                </>
              )}
            </div>

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
