import { History, LogOut, Settings, UserPlus } from 'lucide-react'
import { Link } from 'react-router'

import { useLogout } from '../features/auth.js'
import Sheet from './Sheet.jsx'

const ITEMS = [
  { to: '/avulsos', label: 'Avulsos', icon: UserPlus },
  { to: '/historico', label: 'Histórico', icon: History },
  { to: '/configuracoes', label: 'Configurações', icon: Settings },
]

const itemClass =
  'flex min-h-12 w-full items-center gap-3 rounded-xl px-3 text-base hover:bg-neutral-100 dark:hover:bg-neutral-800'

// Menu "Mais": telas usadas com menos frequência
export default function MoreSheet({ open, onClose }) {
  const logout = useLogout()
  return (
    <Sheet open={open} onClose={onClose} title="Mais">
      <ul className="-mx-2">
        {ITEMS.map(({ to, label, icon: Icon }) => (
          <li key={to}>
            <Link to={to} onClick={onClose} className={itemClass}>
              <Icon size={22} aria-hidden />
              {label}
            </Link>
          </li>
        ))}
        <li>
          <button
            type="button"
            onClick={logout}
            className={`${itemClass} text-red-600 dark:text-red-400`}
          >
            <LogOut size={22} aria-hidden />
            Sair
          </button>
        </li>
      </ul>
    </Sheet>
  )
}
