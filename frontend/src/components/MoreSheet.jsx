import { History, LogOut, Settings, UserPlus, X } from 'lucide-react'
import { useEffect } from 'react'
import { Link } from 'react-router'

import { useLogout } from '../features/auth.js'

const ITEMS = [
  { to: '/avulsos', label: 'Avulsos', icon: UserPlus },
  { to: '/historico', label: 'Histórico', icon: History },
  { to: '/configuracoes', label: 'Configurações', icon: Settings },
]

// Menu "Mais": painel que sobe da parte de baixo da tela
export default function MoreSheet({ open, onClose }) {
  const logout = useLogout()

  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label="Mais opções">
      <button
        type="button"
        aria-label="Fechar"
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />
      <div className="pb-safe absolute inset-x-0 bottom-0 mx-auto max-w-2xl rounded-t-2xl bg-white p-2 shadow-xl dark:bg-neutral-900">
        <div className="flex items-center justify-between px-3 py-2">
          <span className="text-base font-semibold">Mais</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar"
            className="flex size-11 items-center justify-center rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-800"
          >
            <X size={22} aria-hidden />
          </button>
        </div>
        <ul>
          {ITEMS.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <Link
                to={to}
                onClick={onClose}
                className="flex min-h-12 items-center gap-3 rounded-xl px-3 text-base hover:bg-neutral-100 dark:hover:bg-neutral-800"
              >
                <Icon size={22} aria-hidden />
                {label}
              </Link>
            </li>
          ))}
          <li>
            <button
              type="button"
              onClick={logout}
              className="flex min-h-12 w-full items-center gap-3 rounded-xl px-3 text-base text-red-600 hover:bg-neutral-100 dark:text-red-400 dark:hover:bg-neutral-800"
            >
              <LogOut size={22} aria-hidden />
              Sair
            </button>
          </li>
        </ul>
      </div>
    </div>
  )
}
