import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router'

import { PAYMENT_STATUS, POSITION_LABEL, TYPE_LABEL, formatPhone } from '../lib/format.js'
import { Badge } from './ui.jsx'

// Cartão de jogador na lista; toque abre o perfil
export default function PlayerCard({ player, showType = false }) {
  return (
    <Link
      to={`/jogadores/${player.id}`}
      className="flex min-h-16 items-center gap-3 rounded-2xl bg-white px-4 py-3 shadow-sm active:bg-neutral-50 dark:bg-neutral-900 dark:active:bg-neutral-800"
    >
      <div className="min-w-0 flex-1">
        <p className="truncate text-base font-semibold">{player.name}</p>
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          <Badge tone={player.position === 'goalkeeper' ? 'blue' : 'neutral'}>
            {POSITION_LABEL[player.position]}
          </Badge>
          {showType && <Badge>{TYPE_LABEL[player.type]}</Badge>}
          {!player.active && <Badge tone="amber">Inativo</Badge>}
          {player.payment_status && player.payment_status !== 'ok' && (
            <Badge tone={PAYMENT_STATUS[player.payment_status].tone}>
              {PAYMENT_STATUS[player.payment_status].label}
            </Badge>
          )}
          {player.phone && (
            <span className="text-xs text-neutral-600 dark:text-neutral-400">
              {formatPhone(player.phone)}
            </span>
          )}
          {player.referred_by_name && (
            <span className="text-xs text-neutral-600 dark:text-neutral-400">
              · trazido por {player.referred_by_name}
            </span>
          )}
        </div>
      </div>
      <ChevronRight size={20} className="shrink-0 text-neutral-400" aria-hidden />
    </Link>
  )
}
