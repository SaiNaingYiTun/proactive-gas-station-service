import {
  LayoutDashboard,
  CarFront,
  ChartNoAxesCombined,
  Settings,
  ShieldCheck,
  Radio,
} from 'lucide-react'

import { NavLink } from 'react-router'

import { useBackendHealth } from '../lib/useBackendHealth.js'
import { isOwner } from '../lib/auth.js'

const navigationItems = [
  {
    name: 'Overview',
    path: '/',
    icon: LayoutDashboard,
  },
  {
    name: 'Vehicles',
    path: '/vehicles',
    icon: CarFront,
  },
  {
    name: 'Analytics',
    path: '/analytics',
    icon: ChartNoAxesCombined,
  },
]

function Sidebar() {
  // Replaces the old hardcoded "System Online" text: this actually polls the
  // backend's /api/health, the same way the desktop app's own status check
  // does, instead of showing "online" unconditionally regardless of whether
  // anything is reachable.
  const healthy = useBackendHealth()

  const items = isOwner()
    ? [...navigationItems, { name: 'Staff', path: '/staff', icon: ShieldCheck }]
    : navigationItems

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-72 flex-col border-r border-[#22272D] bg-[#0B0D10]">

      {/* Brand */}
      <div className="px-7 pb-7 pt-8">

        <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-[#D98A32]">
          JUST
        </p>

        <h1 className="mt-3 text-[20px] font-semibold tracking-[-0.02em] text-[#F4F5F6]">
          RCVCI
        </h1>

        <p className="mt-2 text-xs text-[#656D77]">
          Operations Management System
        </p>

      </div>


      <div className="mx-6 h-px bg-[#1D2228]" />


      {/* Navigation */}
      <nav className="flex-1 px-4 py-6">

        <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.22em] text-[#555D67]">
          Operations
        </p>

        <div className="space-y-1">

          {items.map((item) => {

            const Icon = item.icon

            return (
              <NavLink
                key={item.name}
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) =>
                  `group flex items-center gap-3 rounded-lg border-l-2 px-3 py-3 text-sm transition-all duration-200 ${
                    isActive
                      ? 'border-[#D98A32] bg-[#171A1F] text-white'
                      : 'border-transparent text-[#858D97] hover:bg-[#121519] hover:text-[#DCE0E4]'
                  }`
                }
              >

                {({ isActive }) => (
                  <>
                    <Icon
                      size={18}
                      strokeWidth={1.8}
                      className={
                        isActive
                          ? 'text-[#D98A32]'
                          : 'text-[#626A74] transition group-hover:text-[#A7ADB5]'
                      }
                    />

                    <span>
                      {item.name}
                    </span>
                  </>
                )}

              </NavLink>
            )
          })}

        </div>

      </nav>


      {/* Bottom */}
      <div className="p-4">

        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg border-l-2 px-3 py-3 text-sm transition-all ${
              isActive
                ? 'border-[#D98A32] bg-[#171A1F] text-white'
                : 'border-transparent text-[#858D97] hover:bg-[#121519] hover:text-white'
            }`
          }
        >
          <Settings
            size={18}
            strokeWidth={1.8}
          />

          Settings
        </NavLink>


        {/* System panel */}
        <div className="mt-4 rounded-xl border border-[#252A30] bg-[#111419] p-4">

          <div className="flex items-center justify-between">

            <div className="flex items-center gap-2">

              <span className="relative flex h-2.5 w-2.5">
                {healthy && (
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#5D9B73] opacity-40"></span>
                )}
                <span
                  className={`relative inline-flex h-2.5 w-2.5 rounded-full ${
                    healthy === null ? 'bg-[#555D67]' : healthy ? 'bg-[#5D9B73]' : 'bg-[#C45F5F]'
                  }`}
                ></span>
              </span>

              <span className="text-xs font-medium text-[#DCE0E4]">
                {healthy === null ? 'Checking…' : healthy ? 'System Online' : 'Backend Unreachable'}
              </span>

            </div>

            <Radio
              size={15}
              className={healthy === false ? 'text-[#C45F5F]' : 'text-[#5D9B73]'}
            />

          </div>

          <p className="mt-2 text-[11px] leading-5 text-[#606872]">
            {healthy === false ? 'Cannot reach the backend API' : 'Detection services operational'}
          </p>

        </div>

      </div>

    </aside>
  )
}

export default Sidebar
