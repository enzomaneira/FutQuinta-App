import { Banknote, CalendarDays, House, Trophy, Users } from 'lucide-react'
import { NavLink } from 'react-router'

export const NAV_ITEMS = [
  { to: '/', label: 'Início', icon: House, end: true },
  { to: '/calendario', label: 'Calendário', icon: CalendarDays },
  { to: '/jogo', label: 'Jogo', icon: Trophy },
  { to: '/jogadores', label: 'Jogadores', icon: Users },
  { to: '/financeiro', label: 'Financeiro', icon: Banknote },
]

export default function BottomNav() {
  return (
    <nav
      aria-label="Navegação principal"
      className="pb-safe fixed inset-x-0 bottom-0 z-40 border-t border-neutral-200 bg-white/95 backdrop-blur dark:border-neutral-800 dark:bg-neutral-900/95"
    >
      <ul className="mx-auto grid max-w-2xl grid-cols-5">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <li key={to}>
            <NavLink
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex min-h-14 flex-col items-center justify-center gap-0.5 text-[11px] font-medium ${
                  isActive
                    ? 'text-brand-700 dark:text-brand-500'
                    : 'text-neutral-500 dark:text-neutral-400'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={22} strokeWidth={isActive ? 2.4 : 1.8} aria-hidden />
                  <span>{label}</span>
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
