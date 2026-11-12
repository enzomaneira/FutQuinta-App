import { Link } from 'react-router'

import { usePlayerProfile } from '../features/insights.js'
import {
  ATTENDANCE_STATUS,
  CHARGE_STATUS,
  formatGameDate,
  formatMoney,
  formatShortDate,
} from '../lib/format.js'
import { Badge, Card, LoadingList } from './ui.jsx'

function chargeLabel(type, reference, dueDate) {
  if (type === 'monthly_fee') {
    const [year, month] = reference.split('-')
    return `Mensalidade ${month}/${year}`
  }
  return dueDate ? `Avulso (jogo ${formatShortDate(dueDate)})` : 'Avulso'
}

/** Estatísticas, pagamentos e últimos jogos do perfil do jogador. */
export default function PlayerProfileSections({ playerId }) {
  const { data, isPending } = usePlayerProfile(playerId)
  if (isPending) return <LoadingList />
  const { stats } = data
  const rate =
    stats.attendance_rate === null ? '—' : `${Math.round(stats.attendance_rate * 100)}%`

  const tiles = [
    ['Jogos jogados', stats.games_played],
    ['Presença', rate, stats.attendance_base ? `${stats.games_played} de ${stats.attendance_base} jogos` : 'sem jogos ainda'],
    ['Desmarcou', stats.cancellations],
    ['Em cima da hora', stats.late_cancellations, 'desmarcou depois do limite'],
    ['Faltas sem aviso', stats.no_shows, 'confirmou e não foi'],
    ['Não respondeu', stats.no_response, 'perdeu a vaga no prazo'],
    ['Com os coletes', stats.bib_times, stats.bib_times === 1 ? 'vez' : 'vezes'],
  ]

  return (
    <>
      <section>
        <SectionTitle>Estatísticas</SectionTitle>
        <ul className="grid grid-cols-2 gap-2">
          {tiles.map(([label, value, hint]) => (
            <li key={label} className="rounded-2xl bg-white p-3 shadow-sm dark:bg-neutral-900">
              <p className="text-xs text-neutral-500 dark:text-neutral-400">{label}</p>
              <p className="text-2xl font-bold tabular-nums">{value}</p>
              {hint && <p className="text-xs text-neutral-500 dark:text-neutral-400">{hint}</p>}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <SectionTitle>Pagamentos</SectionTitle>
        <Card className="space-y-2">
          {data.open_charges.length === 0 ? (
            <p className="flex items-center gap-2 text-sm">
              <Badge tone="green">Em dia</Badge> Nenhuma cobrança em aberto.
            </p>
          ) : (
            <>
              <p className="text-sm font-medium">
                {data.open_charges.length} em aberto ·{' '}
                {formatMoney(data.open_charges.reduce((s, c) => s + c.amount_cents, 0))}
              </p>
              <ul className="space-y-1">
                {data.open_charges.map((c) => (
                  <li key={c.id} className="flex items-center justify-between gap-2 text-sm">
                    <span>{chargeLabel(c.type, c.reference, c.due_date)}</span>
                    <span className="flex items-center gap-2">
                      <Badge tone={CHARGE_STATUS[c.status].tone}>{CHARGE_STATUS[c.status].label}</Badge>
                      <span className="tabular-nums">{formatMoney(c.amount_cents)}</span>
                    </span>
                  </li>
                ))}
              </ul>
              <Link to="/financeiro" className="inline-flex min-h-11 items-center text-sm font-semibold text-brand-700 underline dark:text-brand-500">
                Receber no Financeiro
              </Link>
            </>
          )}
          {data.payments.length > 0 && (
            <div className="border-t border-neutral-200 pt-2 dark:border-neutral-800">
              <p className="mb-1 text-xs font-semibold text-neutral-500">Histórico de pagamentos</p>
              <ul className="space-y-1">
                {data.payments.map((p) => (
                  <li key={`${p.charge_id}-${p.paid_at}`} className="flex justify-between gap-2 text-sm">
                    <span>{chargeLabel(p.charge_type, p.reference, null)}</span>
                    <span className="text-neutral-500 tabular-nums">
                      {formatMoney(p.amount_cents)} · {p.method === 'pix' ? 'Pix' : 'dinheiro'} ·{' '}
                      {new Date(p.paid_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      </section>

      {data.recent_games.length > 0 && (
        <section>
          <SectionTitle>Últimos jogos</SectionTitle>
          <ul className="space-y-2">
            {data.recent_games.map((g) => {
              const status = ATTENDANCE_STATUS[g.status]
              const late = g.status === 'cancelled' && g.late_cancellation
              return (
                <li key={g.game_id}>
                  <Link
                    to={g.game_status === 'played' ? `/historico/${g.game_id}` : `/jogos/${g.game_id}`}
                    className="flex min-h-12 items-center justify-between gap-2 rounded-2xl bg-white px-4 py-2 shadow-sm dark:bg-neutral-900"
                  >
                    <span className="text-sm font-medium capitalize">{formatGameDate(g.local_date)}</span>
                    <span className="flex gap-1">
                      {g.game_status === 'cancelled' && <Badge tone="red">Jogo cancelado</Badge>}
                      <Badge tone={late ? 'red' : status.tone}>{late ? 'Em cima da hora' : status.label}</Badge>
                    </span>
                  </Link>
                </li>
              )
            })}
          </ul>
        </section>
      )}
    </>
  )
}

function SectionTitle({ children }) {
  return <h3 className="mb-2 px-1 text-sm font-semibold text-neutral-500 dark:text-neutral-400">{children}</h3>
}
