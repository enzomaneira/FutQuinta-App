import { AlertTriangle, Shirt } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'

import PlayerPicker from '../components/PlayerPicker.jsx'
import Sheet from '../components/Sheet.jsx'
import { Badge, Button, Card, EmptyState, LoadingList } from '../components/ui.jsx'
import { useCurrentGame, useGame, useGameAction, withStatus } from '../features/games.js'
import {
  ATTENDANCE_STATUS,
  GAME_STATUS,
  formatDeadline,
  formatGameDate,
  formatTime,
} from '../lib/format.js'

const POSITIONS = [
  { key: 'goalkeeper', title: 'Goleiros', singular: 'goleiro' },
  { key: 'field', title: 'Linha', singular: 'linha' },
]

export default function GamePage() {
  const { id } = useParams()
  return id ? <GameById id={id} /> : <CurrentGame />
}

function CurrentGame() {
  const { data: game, isPending, isError, error } = useCurrentGame()
  if (isPending) return <LoadingList />
  if (isError) return <EmptyState>{error.message}</EmptyState>
  if (!game) {
    return (
      <Card className="space-y-3 text-center">
        <p className="font-semibold">Nenhum jogo agendado</p>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          A lista abre sozinha no dia e horário definidos em Configurações. Para criar um jogo
          agora, toque numa data no Calendário.
        </p>
        <Link
          to="/calendario"
          className="inline-flex min-h-11 items-center justify-center rounded-xl bg-brand-700 px-4 font-semibold text-white"
        >
          Abrir calendário
        </Link>
      </Card>
    )
  }
  return <GameView game={game} />
}

function GameById({ id }) {
  const { data: game, isPending, isError, error } = useGame(id)
  if (isPending) return <LoadingList />
  if (isError) return <EmptyState>{error.message}</EmptyState>
  return <GameView game={game} />
}

function GameView({ game }) {
  const action = useGameAction(game.id)
  const [selected, setSelected] = useState(null) // { attendance, group }
  const [picker, setPicker] = useState(null) // { mode: 'add' | 'substitute' | 'bib', out? }

  const run = (path, options = {}) => action.mutate({ path, ...options })
  const busy = action.isPending

  const ops = {
    confirm: (a) =>
      run(`/players/${a.player_id}/confirm`, {
        optimistic: (g) => withStatus(g, a.player_id, 'confirmed'),
        success: `${a.name} confirmado`,
      }),
    cancel: (a) =>
      run(`/players/${a.player_id}/cancel`, {
        optimistic: (g) => withStatus(g, a.player_id, 'cancelled'),
        success: `${a.name} desmarcou — vaga liberada`,
      }),
    presence: (a, present) =>
      run(`/players/${a.player_id}/presence`, {
        body: { present },
        optimistic: (g) => withStatus(g, a.player_id, present ? 'present' : 'absent'),
        success: present ? `${a.name}: compareceu` : `${a.name}: faltou`,
      }),
    callNext: (position) =>
      run('/call-next', { body: { position }, success: 'Avulso chamado e confirmado' }),
    leaveQueue: (a) =>
      run(`/queue/${a.player_id}`, { method: 'DELETE', success: `${a.name} saiu da fila` }),
    joinQueue: (player) =>
      run('/queue', { body: { player_id: player.id }, success: `${player.name} entrou na fila` }),
    setBib: (playerId) =>
      run('/bib', { method: 'PUT', body: { player_id: playerId }, success: 'Coletes atualizados' }),
  }

  const lineupIds = new Set(
    [...game.lineup.goalkeeper, ...game.lineup.field].map((a) => a.player_id),
  )
  const queueIds = new Set([...game.queue.goalkeeper, ...game.queue.field].map((a) => a.player_id))

  function handlePick(player) {
    const mode = picker.mode
    setPicker(null)
    if (mode === 'bib') return ops.setBib(player.id)
    if (mode === 'substitute') {
      return run('/substitute', {
        body: { out_player_id: picker.out.player_id, in_player_id: player.id },
        success: `${player.name} entrou no lugar de ${picker.out.name}`,
      })
    }
    // Adicionar: mensalista confirma direto; avulso entra no fim da fila
    if (player.type === 'monthly') return ops.confirm({ player_id: player.id, name: player.name })
    return ops.joinQueue(player)
  }

  return (
    <div className="space-y-4">
      <Header game={game} onBib={() => setPicker({ mode: 'bib' })} />

      {game.alerts.length > 0 && (
        <Card className="space-y-1 border border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/40">
          {game.alerts.map((text) => (
            <p key={text} className="flex items-start gap-2 text-sm font-medium text-amber-900 dark:text-amber-100">
              <AlertTriangle size={18} className="mt-0.5 shrink-0" aria-hidden />
              {text}
            </p>
          ))}
        </Card>
      )}

      {POSITIONS.map((pos) => (
        <LineupSection
          key={pos.key}
          title={pos.title}
          singular={pos.singular}
          game={game}
          position={pos.key}
          busy={busy}
          ops={ops}
          onSelect={(attendance) => setSelected({ attendance, group: 'lineup' })}
        />
      ))}

      <QueueSection game={game} busy={busy} ops={ops} onSelect={(attendance) => setSelected({ attendance, group: 'queue' })} />
      <OutSection game={game} busy={busy} ops={ops} onSelect={(attendance) => setSelected({ attendance, group: 'out' })} />

      <ManageSection game={game} run={run} busy={busy} onAdd={() => setPicker({ mode: 'add' })} />

      <ActionsSheet
        selection={selected}
        game={game}
        ops={ops}
        onClose={() => setSelected(null)}
        onSubstitute={(attendance) => setPicker({ mode: 'substitute', out: attendance })}
      />

      <PlayerPicker
        open={picker !== null}
        onClose={() => setPicker(null)}
        onPick={handlePick}
        {...pickerProps(picker, lineupIds, queueIds)}
      />
    </div>
  )
}

function pickerProps(picker, lineupIds, queueIds) {
  if (!picker) return {}
  if (picker.mode === 'bib') {
    return {
      title: 'Quem leva os coletes?',
      // Prioriza quem está na lista; sem ninguém na lista, mostra todos
      filter: lineupIds.size ? (p) => lineupIds.has(p.id) : undefined,
    }
  }
  if (picker.mode === 'substitute') {
    return {
      title: `Substituir ${picker.out.name}`,
      hint: 'Mostrando só jogadores da mesma posição que ainda não estão na lista.',
      exclude: [...lineupIds],
      filter: (p) => p.position === picker.out.position,
    }
  }
  return {
    title: 'Adicionar jogador',
    hint: 'Mensalista entra confirmado (se houver vaga). Avulso entra no fim da fila.',
    exclude: [...lineupIds, ...queueIds],
  }
}

// --- cabeçalho ---

function Header({ game, onBib }) {
  const status = GAME_STATUS[game.status]
  const gk = game.slots.goalkeeper
  const field = game.slots.field
  return (
    <Card className="space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-lg font-bold capitalize">{formatGameDate(game.local_date)}</h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            {formatTime(game.start_time)} às {formatTime(game.end_time)}
          </p>
        </div>
        <Badge tone={status.tone}>{status.label}</Badge>
      </div>

      <div className="flex items-end gap-4">
        <p>
          <span className="text-4xl font-bold tabular-nums">{game.occupied}</span>
          <span className="text-xl text-neutral-500">/{game.capacity}</span>
          <span className="ml-2 text-sm text-neutral-500 dark:text-neutral-400">na lista</span>
        </p>
        <p className="pb-1 text-sm text-neutral-600 dark:text-neutral-300">
          Goleiros {gk.confirmed + gk.pending}/{gk.capacity} · Linha {field.confirmed + field.pending}/
          {field.capacity}
        </p>
      </div>

      {game.editable && (
        <p className="text-xs text-neutral-500 dark:text-neutral-400">
          {game.deadline_passed
            ? 'Prazo de confirmação dos mensalistas encerrado.'
            : `Mensalistas confirmam até ${formatDeadline(game.confirmation_deadline)}.`}{' '}
          Desmarcar a partir de {formatDeadline(game.late_cancellation_at)} conta como em cima da hora.
        </p>
      )}

      <div className="flex items-center justify-between gap-2 border-t border-neutral-200 pt-3 dark:border-neutral-800">
        <p className="flex min-w-0 items-center gap-2 text-sm">
          <Shirt size={18} aria-hidden className="shrink-0" />
          <span className="truncate">
            Coletes: <strong>{game.bib_player?.name ?? 'não definido'}</strong>
          </span>
        </p>
        <Button variant="secondary" className="min-h-10 px-3 text-sm" onClick={onBib}>
          {game.bib_player ? 'Trocar' : 'Definir'}
        </Button>
      </div>
    </Card>
  )
}

// --- linhas da lista ---

function Row({ attendance, onSelect, children, prefix }) {
  const status = ATTENDANCE_STATUS[attendance.status]
  const late = attendance.status === 'cancelled' && attendance.late_cancellation
  return (
    <li className="flex min-h-14 items-center gap-2 rounded-2xl bg-white py-1.5 pr-2 pl-3 shadow-sm dark:bg-neutral-900">
      <button
        type="button"
        onClick={() => onSelect(attendance)}
        className="flex min-h-11 min-w-0 flex-1 items-center gap-2 text-left"
        aria-label={`Ações para ${attendance.name}`}
      >
        {prefix}
        <span className="min-w-0">
          <span className="block truncate font-semibold">{attendance.name}</span>
          <span className="mt-0.5 flex flex-wrap gap-1">
            {attendance.status === 'queued' ? (
              // Na fila, o que importa é a posição (cada posição tem sua fila)
              <Badge tone={attendance.position === 'goalkeeper' ? 'blue' : 'neutral'}>
                {attendance.position === 'goalkeeper' ? 'Fila de goleiro' : 'Fila de linha'}
              </Badge>
            ) : late ? (
              <Badge tone="red">Desmarcou em cima da hora</Badge>
            ) : (
              <Badge tone={status.tone}>{status.label}</Badge>
            )}
            {attendance.slot_type === 'drop_in' && attendance.status !== 'queued' && <Badge>Avulso</Badge>}
          </span>
        </span>
      </button>
      {children}
    </li>
  )
}

const small = 'min-h-10 shrink-0 px-3 text-sm'

function LineupSection({ title, singular, game, position, busy, ops, onSelect }) {
  const items = game.lineup[position]
  const slots = game.slots[position]
  const nextInQueue = game.queue[position][0]
  const played = game.status === 'played'
  return (
    <section>
      <SectionTitle>
        {title} ({slots.confirmed + slots.pending}/{slots.capacity})
      </SectionTitle>
      <ul className="space-y-2">
        {items.map((a) => (
          <Row key={a.player_id} attendance={a} onSelect={onSelect}>
            {game.editable && a.status === 'pending' && (
              <Button className={small} disabled={busy} onClick={() => ops.confirm(a)}>
                Confirmar
              </Button>
            )}
            {game.editable && a.status === 'confirmed' && (
              <Button variant="secondary" className={small} disabled={busy} onClick={() => ops.cancel(a)}>
                Desmarcar
              </Button>
            )}
            {played && (a.status === 'present' || a.status === 'confirmed') && (
              <Button variant="secondary" className={small} disabled={busy} onClick={() => ops.presence(a, false)}>
                Faltou
              </Button>
            )}
            {played && a.status === 'absent' && (
              <Button variant="secondary" className={small} disabled={busy} onClick={() => ops.presence(a, true)}>
                Veio
              </Button>
            )}
          </Row>
        ))}
        {game.editable &&
          Array.from({ length: slots.free }, (_, i) => (
            <li
              key={`free-${i}`}
              className="flex min-h-14 items-center justify-between gap-2 rounded-2xl border border-dashed border-neutral-300 py-1.5 pr-2 pl-3 dark:border-neutral-700"
            >
              <span className="text-sm text-neutral-500">Vaga livre de {singular}</span>
              {nextInQueue && i === 0 && (
                <Button className={small} disabled={busy} onClick={() => ops.callNext(position)}>
                  Chamar {nextInQueue.name.split(' ')[0]}
                </Button>
              )}
            </li>
          ))}
      </ul>
    </section>
  )
}

function QueueSection({ game, busy, ops, onSelect }) {
  const total = game.queue.goalkeeper.length + game.queue.field.length
  if (!game.editable && total === 0) return null
  return (
    <section>
      <SectionTitle>Fila de avulsos ({total})</SectionTitle>
      {total === 0 ? (
        <EmptyState>Ninguém na fila. Use “Adicionar jogador” para incluir um avulso.</EmptyState>
      ) : (
        <ul className="space-y-2">
          {POSITIONS.flatMap(({ key }) =>
            game.queue[key].map((a) => {
              const hasSlot = game.slots[key].free > 0
              return (
                <Row
                  key={a.player_id}
                  attendance={{ ...a, status: 'queued' }}
                  onSelect={onSelect}
                  prefix={
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-neutral-100 text-sm font-bold dark:bg-neutral-800">
                      {a.queue_position}º
                    </span>
                  }
                >
                  {game.editable && (
                    <Button
                      className={small}
                      disabled={busy || !hasSlot}
                      onClick={() => ops.confirm(a)}
                      aria-label={hasSlot ? `Chamar ${a.name}` : `Sem vaga de ${key === 'goalkeeper' ? 'goleiro' : 'linha'} livre`}
                    >
                      {hasSlot ? 'Chamar' : 'Sem vaga'}
                    </Button>
                  )}
                </Row>
              )
            }),
          )}
        </ul>
      )}
    </section>
  )
}

function OutSection({ game, busy, ops, onSelect }) {
  if (game.out.length === 0) return null
  return (
    <section>
      <SectionTitle>Fora da lista ({game.out.length})</SectionTitle>
      <ul className="space-y-2">
        {game.out.map((a) => (
          <Row key={a.player_id} attendance={a} onSelect={onSelect}>
            {game.editable && a.player_type === 'monthly' && (
              <Button variant="secondary" className={small} disabled={busy} onClick={() => ops.confirm(a)}>
                Reconfirmar
              </Button>
            )}
          </Row>
        ))}
      </ul>
    </section>
  )
}

function ManageSection({ game, run, busy, onAdd }) {
  function cancelGame() {
    if (window.confirm('Cancelar este jogo? Avulsos confirmados não serão cobrados.')) {
      run('/cancel', { success: 'Jogo cancelado' })
    }
  }
  return (
    <section className="space-y-2">
      {game.editable && (
        <Button className="w-full" disabled={busy} onClick={onAdd}>
          Adicionar jogador
        </Button>
      )}
      {(game.status === 'open' || game.status === 'draft') && (
        <Button variant="secondary" className="w-full" disabled={busy} onClick={() => run('/close', { success: 'Lista fechada' })}>
          Fechar lista
        </Button>
      )}
      {(game.status === 'closed' || game.status === 'cancelled') && (
        <Button variant="secondary" className="w-full" disabled={busy} onClick={() => run('/reopen', { success: 'Lista reaberta' })}>
          {game.status === 'cancelled' ? 'Reabrir jogo' : 'Reabrir lista'}
        </Button>
      )}
      {game.editable && (
        <Button variant="ghost" className="w-full text-red-600 dark:text-red-400" disabled={busy} onClick={cancelGame}>
          Cancelar jogo
        </Button>
      )}
    </section>
  )
}

function SectionTitle({ children }) {
  return (
    <h3 className="mb-2 px-1 text-sm font-semibold text-neutral-500 dark:text-neutral-400">{children}</h3>
  )
}

// --- menu de ações de um jogador ---

function ActionsSheet({ selection, game, ops, onClose, onSubstitute }) {
  const a = selection?.attendance
  const options = []
  if (a) {
    const { group } = selection
    const editable = game.editable
    const item = (label, fn, tone) => options.push({ label, fn, tone })
    if (group === 'lineup' && editable) {
      if (a.status === 'pending') item('Confirmar presença', () => ops.confirm(a))
      item('Desmarcar (libera a vaga)', () => ops.cancel(a), 'danger')
      item('Substituir por outro jogador', () => onSubstitute(a))
    }
    if (group === 'lineup' && game.status === 'played') {
      if (a.status === 'absent') item('Marcar que compareceu', () => ops.presence(a, true))
      else item('Marcar falta', () => ops.presence(a, false), 'danger')
    }
    if (group === 'lineup') item('Responsável pelos coletes', () => ops.setBib(a.player_id))
    if (group === 'queue' && editable) {
      item('Chamar agora', () => ops.confirm(a))
      item('Tirar da fila', () => ops.leaveQueue(a), 'danger')
    }
    if (group === 'out' && editable) {
      if (a.player_type === 'monthly') item('Reconfirmar (se houver vaga)', () => ops.confirm(a))
      else item('Colocar no fim da fila', () => ops.joinQueue({ id: a.player_id, name: a.name }))
    }
  }
  return (
    <Sheet open={Boolean(a)} onClose={onClose} title={a?.name ?? ''}>
      <ul className="-mx-2">
        {options.map(({ label, fn, tone }) => (
          <li key={label}>
            <button
              type="button"
              onClick={() => {
                onClose()
                fn()
              }}
              className={`flex min-h-12 w-full items-center rounded-xl px-3 text-left text-base hover:bg-neutral-100 dark:hover:bg-neutral-800 ${
                tone === 'danger' ? 'text-red-600 dark:text-red-400' : ''
              }`}
            >
              {label}
            </button>
          </li>
        ))}
        {a && (
          <li>
            <Link
              to={`/jogadores/${a.player_id}`}
              className="flex min-h-12 items-center rounded-xl px-3 text-base hover:bg-neutral-100 dark:hover:bg-neutral-800"
            >
              Ver perfil
            </Link>
          </li>
        )}
      </ul>
    </Sheet>
  )
}
