import { Shirt } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'

import { Badge, Card, EmptyState, LoadingList, TextField } from '../components/ui.jsx'
import { useGame } from '../features/games.js'
import { useGameCharges, useGameHistory } from '../features/insights.js'
import {
  ATTENDANCE_STATUS,
  CHARGE_STATUS,
  GAME_STATUS,
  formatGameDate,
  formatMoney,
  formatTime,
} from '../lib/format.js'

export default function HistoryPage() {
  const { id } = useParams()
  return id ? <HistoryDetail id={id} /> : <HistoryList />
}

// --- lista de jogos passados, com busca por data ---

function HistoryList() {
  const { data: games, isPending } = useGameHistory()
  const [date, setDate] = useState('')
  const shown = date ? (games ?? []).filter((g) => g.local_date === date) : games

  return (
    <div className="space-y-4">
      <Card>
        <TextField
          label="Escolha uma data"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          hint="Ou toque num jogo da lista abaixo."
        />
      </Card>
      {isPending ? (
        <LoadingList />
      ) : shown.length === 0 ? (
        <EmptyState>{date ? 'Não houve jogo nesta data.' : 'Nenhum jogo realizado ainda.'}</EmptyState>
      ) : (
        <ul className="space-y-2">
          {shown.map((g) => (
            <li key={g.id}>
              <Link
                to={`/historico/${g.id}`}
                className="flex min-h-14 items-center justify-between gap-2 rounded-2xl bg-white px-4 py-3 shadow-sm dark:bg-neutral-900"
              >
                <span>
                  <span className="block font-semibold capitalize">{formatGameDate(g.local_date)}</span>
                  <span className="text-sm text-neutral-600 dark:text-neutral-400">
                    {formatTime(g.start_time)} · {g.occupied} jogador{g.occupied === 1 ? '' : 'es'}
                  </span>
                </span>
                <Badge tone={GAME_STATUS[g.status].tone}>{GAME_STATUS[g.status].label}</Badge>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// --- detalhe de um jogo passado ---

function HistoryDetail({ id }) {
  const { data: game, isPending, isError, error } = useGame(id)
  const { data: values } = useGameCharges(id)
  if (isPending) return <LoadingList />
  if (isError) return <EmptyState>{error.message}</EmptyState>

  const played = [...game.lineup.goalkeeper, ...game.lineup.field]
  const cancelled = game.out.filter((a) => a.status === 'cancelled')
  const released = game.out.filter((a) => a.status === 'released')

  return (
    <div className="space-y-4">
      <Card className="space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-lg font-bold capitalize">{formatGameDate(game.local_date)}</h2>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              {formatTime(game.start_time)} às {formatTime(game.end_time)}
            </p>
          </div>
          <Badge tone={GAME_STATUS[game.status].tone}>{GAME_STATUS[game.status].label}</Badge>
        </div>
        <p className="flex items-center gap-2 text-sm">
          <Shirt size={18} aria-hidden />
          Coletes: <strong>{game.bib_player?.name ?? 'não definido'}</strong>
        </p>
        <p className="text-sm text-neutral-600 dark:text-neutral-300">
          {plural(played.filter((a) => a.status === 'present').length, 'compareceu', 'compareceram')} ·{' '}
          {plural(played.filter((a) => a.status === 'absent').length, 'faltou', 'faltaram')} ·{' '}
          {plural(cancelled.length, 'desmarcou', 'desmarcaram')}
        </p>
        {game.status !== 'played' && (
          <Link to={`/jogos/${game.id}`} className="inline-flex min-h-11 items-center text-sm font-semibold text-brand-700 underline dark:text-brand-500">
            Abrir na tela do jogo
          </Link>
        )}
      </Card>

      <PeopleSection title="Goleiros" items={game.lineup.goalkeeper} />
      <PeopleSection title="Linha" items={game.lineup.field} />
      <PeopleSection title="Desmarcaram" items={cancelled} />
      <PeopleSection title="Não responderam até o prazo" items={released} />

      <section>
        <SectionTitle>Valores recebidos (avulsos)</SectionTitle>
        <Card className="space-y-2">
          {!values ? (
            <p className="text-sm text-neutral-600 dark:text-neutral-400">Carregando…</p>
          ) : values.charges.length === 0 ? (
            <p className="text-sm text-neutral-600 dark:text-neutral-400">Nenhum avulso neste jogo.</p>
          ) : (
            <>
              <p className="text-sm">
                <strong>{formatMoney(values.received_cents)}</strong> recebido de{' '}
                {formatMoney(values.expected_cents)}
              </p>
              <ul className="space-y-1">
                {values.charges.map((c) => (
                  <li key={c.id} className="flex items-center justify-between gap-2 text-sm">
                    <span className="truncate">{c.player_name}</span>
                    <span className="flex items-center gap-2">
                      <Badge tone={CHARGE_STATUS[c.status].tone}>{CHARGE_STATUS[c.status].label}</Badge>
                      <span className="tabular-nums">{formatMoney(c.amount_cents)}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
          <p className="text-xs text-neutral-600 dark:text-neutral-400">Mensalidades são cobradas por mês: veja no Financeiro.</p>
        </Card>
      </section>
    </div>
  )
}

function PeopleSection({ title, items }) {
  if (items.length === 0) return null
  return (
    <section>
      <SectionTitle>
        {title} ({items.length})
      </SectionTitle>
      <ul className="divide-y divide-neutral-200 rounded-2xl bg-white shadow-sm dark:divide-neutral-800 dark:bg-neutral-900">
        {items.map((a) => {
          const status = ATTENDANCE_STATUS[a.status]
          const late = a.status === 'cancelled' && a.late_cancellation
          return (
            <li key={a.player_id}>
              <Link to={`/jogadores/${a.player_id}`} className="flex min-h-12 items-center justify-between gap-2 px-4 py-2">
                <span className="truncate font-medium">{a.name}</span>
                <span className="flex shrink-0 gap-1">
                  {a.slot_type === 'drop_in' && <Badge>Avulso</Badge>}
                  <Badge tone={late ? 'red' : status.tone}>{late ? 'Em cima da hora' : status.label}</Badge>
                </span>
              </Link>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function plural(count, singular, pluralForm) {
  return `${count} ${count === 1 ? singular : pluralForm}`
}

function SectionTitle({ children }) {
  return <h3 className="mb-2 px-1 text-sm font-semibold text-neutral-600 dark:text-neutral-400">{children}</h3>
}
