import { AlertTriangle, ChevronRight, MapPin, Shirt } from 'lucide-react'
import { Suspense, lazy } from 'react'
import { Link } from 'react-router'

import { Badge, Card, EmptyState, LoadingList } from '../components/ui.jsx'
import { useHome } from '../features/insights.js'
import {
  CHARGE_STATUS,
  GAME_STATUS,
  formatGameDate,
  formatMoney,
  formatTime,
  mapsUrl,
} from '../lib/format.js'

// Leaflet é pesado: carrega só quando a tela Início aparece
const VenueMap = lazy(() => import('../components/VenueMap.jsx'))

const linkClass =
  'inline-flex min-h-11 items-center gap-1 text-sm font-semibold text-brand-700 dark:text-brand-500'

export default function HomePage() {
  const { data, isPending, isError, error } = useHome()
  if (isPending) return <LoadingList />
  if (isError) return <EmptyState>{error.message}</EmptyState>
  const { game, cash, venue, open_charges: open } = data

  return (
    <div className="space-y-4">
      <NextGame game={game} />

      <div className="grid grid-cols-2 gap-3">
        <Link to="/financeiro" className="rounded-2xl bg-white p-4 shadow-sm dark:bg-neutral-900">
          <p className="text-xs text-neutral-600 dark:text-neutral-400">Caixa atual</p>
          <p className={`text-xl font-bold tabular-nums ${cash.balance_cents < 0 ? 'text-red-600 dark:text-red-400' : ''}`}>
            {formatMoney(cash.balance_cents)}
          </p>
        </Link>
        <Link to="/financeiro" className="rounded-2xl bg-white p-4 shadow-sm dark:bg-neutral-900">
          <p className="text-xs text-neutral-600 dark:text-neutral-400">Em aberto</p>
          <p className="text-xl font-bold tabular-nums">{formatMoney(open.total_cents)}</p>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            {open.count} cobrança{open.count === 1 ? '' : 's'}
            {open.overdue > 0 && <span className="font-semibold text-red-700 dark:text-red-300"> · {open.overdue} atrasada{open.overdue === 1 ? '' : 's'}</span>}
          </p>
        </Link>
      </div>

      {open.count > 0 && (
        <Card>
          <h2 className="mb-2 text-base font-semibold">Pendências de pagamento</h2>
          <ul className="space-y-1">
            {open.items.map((c) => (
              <li key={c.id}>
                <Link to={`/jogadores/${c.player_id}`} className="flex min-h-11 items-center justify-between gap-2 text-sm">
                  <span className="truncate">{c.player_name}</span>
                  <span className="flex shrink-0 items-center gap-2">
                    <Badge tone={CHARGE_STATUS[c.status].tone}>{CHARGE_STATUS[c.status].label}</Badge>
                    <span className="tabular-nums">{formatMoney(c.amount_cents)}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          <Link to="/financeiro" className={linkClass}>
            {open.count > open.items.length ? `Ver todas (${open.count})` : 'Abrir financeiro'}
            <ChevronRight size={16} aria-hidden />
          </Link>
        </Card>
      )}

      <Card className="space-y-3">
        <div>
          <h2 className="text-base font-semibold">{venue.name}</h2>
          <p className="flex items-start gap-1 text-sm text-neutral-600 dark:text-neutral-300">
            <MapPin size={16} className="mt-0.5 shrink-0" aria-hidden />
            {venue.address}
          </p>
        </div>
        <Suspense fallback={<div className="h-44 motion-safe:animate-pulse rounded-xl bg-neutral-200 dark:bg-neutral-800" />}>
          <VenueMap lat={venue.lat} lng={venue.lng} label={venue.name} />
        </Suspense>
        <a
          href={mapsUrl(venue.lat, venue.lng)}
          target="_blank"
          rel="noreferrer"
          className="inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-neutral-200 font-semibold dark:bg-neutral-800"
        >
          Abrir no mapa
        </a>
      </Card>
    </div>
  )
}

function NextGame({ game }) {
  if (!game) {
    return (
      <Card className="space-y-2">
        <p className="font-semibold">Nenhum jogo agendado</p>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          A lista abre sozinha no horário definido em Configurações, ou crie um jogo pelo Calendário.
        </p>
        <Link to="/calendario" className={linkClass}>
          Abrir calendário <ChevronRight size={16} aria-hidden />
        </Link>
      </Card>
    )
  }
  const status = GAME_STATUS[game.status]
  const gk = game.slots.goalkeeper
  const missingGk = gk.capacity - gk.confirmed
  return (
    <Link to="/jogo" className="block rounded-2xl bg-white p-4 shadow-sm dark:bg-neutral-900">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            {game.status === 'played' ? 'Último jogo' : 'Próximo jogo'}
          </p>
          <h2 className="text-lg font-bold capitalize">{formatGameDate(game.local_date)}</h2>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            {formatTime(game.start_time)} às {formatTime(game.end_time)}
          </p>
        </div>
        <Badge tone={status.tone}>{status.label}</Badge>
      </div>
      <p className="mt-2">
        <span className="text-4xl font-bold tabular-nums">{game.occupied}</span>
        <span className="text-xl text-neutral-600 dark:text-neutral-400">/{game.capacity}</span>
        <span className="ml-2 text-sm text-neutral-600 dark:text-neutral-400">na lista</span>
      </p>
      {game.editable && missingGk > 0 && (
        <p className="mt-2 flex items-center gap-2 rounded-xl bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900 dark:bg-amber-950/40 dark:text-amber-100">
          <AlertTriangle size={18} aria-hidden className="shrink-0" />
          {missingGk === 1 ? 'Falta 1 goleiro confirmado' : `Faltam ${missingGk} goleiros confirmados`}
        </p>
      )}
      <p className="mt-2 flex items-center gap-2 text-sm">
        <Shirt size={18} aria-hidden />
        Coletes: <strong>{game.bib_player?.name ?? 'não definido'}</strong>
      </p>
      <span className={`${linkClass} mt-1`}>
        Abrir lista <ChevronRight size={16} aria-hidden />
      </span>
    </Link>
  )
}
