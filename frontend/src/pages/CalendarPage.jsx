import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'

import Sheet from '../components/Sheet.jsx'
import { Badge, Button, Card, LoadingList } from '../components/ui.jsx'
import { useCalendar, useCreateGame } from '../features/games.js'
import { GAME_STATUS, formatGameDate, formatTime } from '../lib/format.js'

const WEEK_HEADER = ['D', 'S', 'T', 'Q', 'Q', 'S', 'S']
const MONTHS = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
]
// Rótulo curto para caber na célula do dia (o texto completo fica na lista abaixo)
const SHORT_STATUS = {
  draft: 'Rascunho',
  open: 'Aberta',
  closed: 'Fechada',
  played: 'Jogado',
  cancelled: 'Cancel.',
}
const CELL_TONE = {
  open: 'bg-brand-100 text-brand-800 dark:bg-brand-900 dark:text-brand-100',
  closed: 'bg-sky-100 text-sky-800 dark:bg-sky-900/60 dark:text-sky-100',
  played: 'bg-neutral-200 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-200',
  cancelled: 'bg-red-100 text-red-800 dark:bg-red-900/60 dark:text-red-100',
  draft: 'bg-neutral-200 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-200',
}

function iso(year, month, day) {
  return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

function todayIso() {
  const now = new Date()
  return iso(now.getFullYear(), now.getMonth(), now.getDate())
}

export default function CalendarPage() {
  const now = new Date()
  const [cursor, setCursor] = useState({ year: now.getFullYear(), month: now.getMonth() })
  const monthKey = `${cursor.year}-${String(cursor.month + 1).padStart(2, '0')}`
  const { data, isPending } = useCalendar(monthKey)
  const navigate = useNavigate()
  const [creating, setCreating] = useState(null) // data ISO do jogo a criar

  function move(delta) {
    setCursor(({ year, month }) => {
      const date = new Date(year, month + delta, 1)
      return { year: date.getFullYear(), month: date.getMonth() }
    })
  }

  const gamesByDate = Object.fromEntries((data?.games ?? []).map((g) => [g.local_date, g]))
  // Python: segunda=0; JavaScript: domingo=0
  const gameJsDay = data ? (data.game_weekday + 1) % 7 : null
  const firstWeekday = new Date(cursor.year, cursor.month, 1).getDay()
  const daysInMonth = new Date(cursor.year, cursor.month + 1, 0).getDate()
  const today = todayIso()

  function handleDay(day) {
    const date = iso(cursor.year, cursor.month, day)
    const game = gamesByDate[date]
    if (game) navigate(`/jogos/${game.id}`)
    else if (date >= today) setCreating(date)
  }

  return (
    <div className="space-y-4">
      <Card className="p-3">
        <div className="mb-2 flex items-center justify-between">
          <button type="button" onClick={() => move(-1)} aria-label="Mês anterior" className="flex size-11 items-center justify-center rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-800">
            <ChevronLeft size={22} aria-hidden />
          </button>
          <h2 className="text-base font-semibold capitalize" aria-live="polite">
            {MONTHS[cursor.month]} {cursor.year}
          </h2>
          <button type="button" onClick={() => move(1)} aria-label="Próximo mês" className="flex size-11 items-center justify-center rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-800">
            <ChevronRight size={22} aria-hidden />
          </button>
        </div>

        <div className="grid grid-cols-7 gap-1 text-center">
          {WEEK_HEADER.map((d, i) => (
            <div key={i} className={`py-1 text-xs font-semibold ${i === gameJsDay ? 'text-brand-700 dark:text-brand-500' : 'text-neutral-500'}`}>
              {d}
            </div>
          ))}
          {Array.from({ length: firstWeekday }, (_, i) => <div key={`pad-${i}`} />)}
          {Array.from({ length: daysInMonth }, (_, i) => {
            const day = i + 1
            const date = iso(cursor.year, cursor.month, day)
            const game = gamesByDate[date]
            const isGameDay = new Date(cursor.year, cursor.month, day).getDay() === gameJsDay
            const isDue = data && day === data.due_day
            const clickable = Boolean(game) || (isGameDay && date >= today)
            const label = [
              formatGameDate(date),
              game ? GAME_STATUS[game.status].label : isGameDay ? 'dia de jogo sem lista' : null,
              isDue ? 'vencimento da mensalidade' : null,
            ].filter(Boolean).join(', ')
            return (
              <button
                key={day}
                type="button"
                disabled={!clickable}
                onClick={() => handleDay(day)}
                aria-label={label}
                className={`flex min-h-14 flex-col items-center justify-start gap-0.5 rounded-lg pt-1 text-sm disabled:cursor-default ${
                  game ? CELL_TONE[game.status] : isGameDay ? 'ring-1 ring-brand-600/50 ring-inset' : ''
                } ${date === today ? 'font-bold underline underline-offset-4' : ''}`}
              >
                <span>{day}</span>
                {game && <span className="text-[10px] leading-tight font-semibold">{SHORT_STATUS[game.status]}</span>}
                {isDue && <span className="text-[10px] leading-tight font-semibold text-amber-700 dark:text-amber-300">Venc.</span>}
              </button>
            )
          })}
        </div>

        <p className="mt-3 text-xs text-neutral-500 dark:text-neutral-400">
          Dias de jogo têm borda verde; toque para abrir ou criar o jogo. “Venc.” marca o vencimento
          da mensalidade (dia {data?.due_day ?? 15}).
        </p>
      </Card>

      <section>
        <h3 className="mb-2 px-1 text-sm font-semibold text-neutral-500 dark:text-neutral-400">Jogos do mês</h3>
        {isPending ? (
          <LoadingList />
        ) : data.games.length === 0 ? (
          <p className="px-1 text-sm text-neutral-500">Nenhum jogo neste mês.</p>
        ) : (
          <ul className="space-y-2">
            {data.games.map((g) => (
              <li key={g.id}>
                <Link to={`/jogos/${g.id}`} className="flex min-h-14 items-center justify-between gap-2 rounded-2xl bg-white px-4 py-3 shadow-sm dark:bg-neutral-900">
                  <span>
                    <span className="block font-semibold capitalize">{formatGameDate(g.local_date)}</span>
                    <span className="text-sm text-neutral-500 dark:text-neutral-400">
                      {formatTime(g.start_time)} · {g.occupied}/{g.capacity} na lista
                    </span>
                  </span>
                  <Badge tone={GAME_STATUS[g.status].tone}>{GAME_STATUS[g.status].label}</Badge>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <CreateGameSheet date={creating} onClose={() => setCreating(null)} onCreated={(id) => navigate(`/jogos/${id}`)} />
    </div>
  )
}

function CreateGameSheet({ date, onClose, onCreated }) {
  const create = useCreateGame()
  return (
    <Sheet open={Boolean(date)} onClose={onClose} title="Criar jogo">
      {date && (
        <div className="space-y-4">
          <p className="text-sm">
            Criar o jogo de <strong className="capitalize">{formatGameDate(date)}</strong> e abrir a
            lista agora? Todos os mensalistas ativos entram como pendentes.
          </p>
          <Button
            className="w-full"
            disabled={create.isPending}
            onClick={() =>
              create.mutate(date, {
                onSuccess: (game) => {
                  onClose()
                  onCreated(game.id)
                },
              })
            }
          >
            {create.isPending ? 'Criando…' : 'Criar e abrir lista'}
          </Button>
        </div>
      )}
    </Sheet>
  )
}
