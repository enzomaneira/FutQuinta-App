import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import Sheet from '../components/Sheet.jsx'
import { Badge, Button, Card, EmptyState, Fab, LoadingList, Segmented, TextField } from '../components/ui.jsx'
import {
  useCash,
  useChargeAction,
  useCreateExpense,
  useDeleteExpense,
  useDropInCharges,
  useExpenses,
  useGenerateFees,
  useMonthlyFees,
  useStatement,
} from '../features/finance.js'
import {
  CHARGE_STATUS,
  EXPENSE_CATEGORY,
  formatMoney,
  formatShortDate,
  parseMoney,
} from '../lib/format.js'

const MONTHS = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
]
const TABS = [
  { value: 'fees', label: 'Mensal.' },
  { value: 'dropins', label: 'Avulsos' },
  { value: 'expenses', label: 'Despesas' },
  { value: 'statement', label: 'Extrato' },
]

function monthKey({ year, month }) {
  return `${year}-${String(month + 1).padStart(2, '0')}`
}

export default function FinancePage() {
  const now = new Date()
  const [cursor, setCursor] = useState({ year: now.getFullYear(), month: now.getMonth() })
  const [tab, setTab] = useState('fees')
  const month = monthKey(cursor)

  function move(delta) {
    setCursor(({ year, month: m }) => {
      const date = new Date(year, m + delta, 1)
      return { year: date.getFullYear(), month: date.getMonth() }
    })
  }

  return (
    <div className="space-y-4">
      <CashCard />

      <div className="flex items-center justify-between">
        <button type="button" onClick={() => move(-1)} aria-label="Mês anterior" className="flex size-11 items-center justify-center rounded-full hover:bg-neutral-200 dark:hover:bg-neutral-800">
          <ChevronLeft size={22} aria-hidden />
        </button>
        <h2 className="text-base font-semibold capitalize" aria-live="polite">
          {MONTHS[cursor.month]} {cursor.year}
        </h2>
        <button type="button" onClick={() => move(1)} aria-label="Próximo mês" className="flex size-11 items-center justify-center rounded-full hover:bg-neutral-200 dark:hover:bg-neutral-800">
          <ChevronRight size={22} aria-hidden />
        </button>
      </div>

      <Segmented label="Seção do financeiro" options={TABS} value={tab} onChange={setTab} />

      {tab === 'fees' && <MonthlyFees month={month} monthName={MONTHS[cursor.month]} />}
      {tab === 'dropins' && <DropIns month={month} />}
      {tab === 'expenses' && <Expenses month={month} />}
      {tab === 'statement' && <Statement month={month} />}
    </div>
  )
}

// --- caixa ---

function CashCard() {
  const { data: cash } = useCash()
  return (
    <Card>
      <p className="text-sm text-neutral-500 dark:text-neutral-400">Caixa atual</p>
      <p className={`text-3xl font-bold tabular-nums ${cash && cash.balance_cents < 0 ? 'text-red-600 dark:text-red-400' : ''}`}>
        {cash ? formatMoney(cash.balance_cents) : '…'}
      </p>
      {cash && (
        <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
          Saldo inicial {formatMoney(cash.initial_cents)} + recebido {formatMoney(cash.received_cents)} − despesas{' '}
          {formatMoney(cash.expenses_cents)}
        </p>
      )}
    </Card>
  )
}

// --- cobranças ---

function Totals({ charges }) {
  const count = (status) => charges.filter((c) => c.status === status).length
  const sum = (filter) => charges.filter(filter).reduce((total, c) => total + c.amount_cents, 0)
  const received = sum((c) => c.status === 'paid')
  const expected = sum((c) => c.status !== 'waived')
  return (
    <p className="px-1 text-sm text-neutral-600 dark:text-neutral-300">
      <strong>{formatMoney(received)}</strong> de {formatMoney(expected)} · {count('paid')} pago(s), {count('pending')}{' '}
      pendente(s), {count('overdue')} atrasado(s)
    </p>
  )
}

function ChargeList({ charges, showGame = false }) {
  const action = useChargeAction()
  const [selected, setSelected] = useState(null)
  const run = (charge, name, body, success) => action.mutate({ id: charge.id, action: name, body, success })

  return (
    <>
      <ul className="space-y-2">
        {charges.map((c) => {
          const status = CHARGE_STATUS[c.status]
          const open = c.status === 'pending' || c.status === 'overdue'
          return (
            <li key={c.id} className="flex min-h-16 items-center gap-2 rounded-2xl bg-white py-2 pr-2 pl-3 shadow-sm dark:bg-neutral-900">
              <button type="button" onClick={() => setSelected(c)} className="min-h-11 min-w-0 flex-1 text-left" aria-label={`Opções de ${c.player_name}`}>
                <span className="block truncate font-semibold">{c.player_name}</span>
                <span className="mt-0.5 flex flex-wrap items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400">
                  <Badge tone={status.tone}>{status.label}</Badge>
                  <span className="tabular-nums">{formatMoney(c.amount_cents)}</span>
                  <span>
                    · {showGame ? `jogo ${formatShortDate(c.due_date)}` : `vence ${formatShortDate(c.due_date)}`}
                  </span>
                  {c.payment_method && <span>· {c.payment_method === 'pix' ? 'Pix' : 'dinheiro'}</span>}
                </span>
              </button>
              {open && (
                <Button className="min-h-10 shrink-0 px-3 text-sm" disabled={action.isPending} onClick={() => run(c, 'pay', { method: 'pix' }, `${c.player_name}: pago via Pix`)}>
                  Marcar pago
                </Button>
              )}
            </li>
          )
        })}
      </ul>
      <ChargeActions charge={selected} onClose={() => setSelected(null)} run={run} />
    </>
  )
}

function ChargeActions({ charge, onClose, run }) {
  const options = []
  if (charge) {
    const add = (label, name, body, success, danger) => options.push({ label, name, body, success, danger })
    if (charge.status === 'pending' || charge.status === 'overdue') {
      add('Recebido via Pix', 'pay', { method: 'pix' }, 'Pago via Pix')
      add('Recebido em dinheiro', 'pay', { method: 'cash' }, 'Pago em dinheiro')
      add('Isentar esta cobrança', 'waive', undefined, 'Cobrança isenta', true)
    }
    if (charge.status === 'paid') add('Desfazer pagamento', 'undo-payment', undefined, 'Pagamento desfeito', true)
    if (charge.status === 'waived') add('Tirar isenção', 'unwaive', undefined, 'Isenção retirada')
  }
  return (
    <Sheet open={Boolean(charge)} onClose={onClose} title={charge?.player_name ?? ''}>
      {charge && (
        <ul className="-mx-2">
          {options.map((o) => (
            <li key={o.label}>
              <button
                type="button"
                onClick={() => {
                  onClose()
                  run(charge, o.name, o.body, `${charge.player_name}: ${o.success.toLowerCase()}`)
                }}
                className={`flex min-h-12 w-full items-center rounded-xl px-3 text-left text-base hover:bg-neutral-100 dark:hover:bg-neutral-800 ${o.danger ? 'text-red-600 dark:text-red-400' : ''}`}
              >
                {o.label}
              </button>
            </li>
          ))}
          <li>
            <Link to={`/jogadores/${charge.player_id}`} className="flex min-h-12 items-center rounded-xl px-3 text-base hover:bg-neutral-100 dark:hover:bg-neutral-800">
              Ver perfil
            </Link>
          </li>
        </ul>
      )}
    </Sheet>
  )
}

function MonthlyFees({ month, monthName }) {
  const { data: charges, isPending } = useMonthlyFees(month)
  const generate = useGenerateFees()
  if (isPending) return <LoadingList />
  if (charges.length === 0) {
    return (
      <div className="space-y-3">
        <EmptyState>
          Nenhuma mensalidade de {monthName}. Elas são geradas sozinhas no dia de cobrança (Configurações → Cobrança).
        </EmptyState>
        <Button className="w-full" disabled={generate.isPending} onClick={() => generate.mutate(month)}>
          Gerar mensalidades de {monthName}
        </Button>
      </div>
    )
  }
  return (
    <div className="space-y-3">
      <Totals charges={charges} />
      <ChargeList charges={charges} />
      <Button variant="ghost" className="w-full text-sm" disabled={generate.isPending} onClick={() => generate.mutate(month)}>
        Gerar as que faltam (mensalista novo)
      </Button>
    </div>
  )
}

function DropIns({ month }) {
  const { data: charges, isPending } = useDropInCharges(month)
  if (isPending) return <LoadingList />
  if (charges.length === 0) {
    return <EmptyState>Nenhum avulso cobrado neste mês. A cobrança é criada quando o avulso é confirmado no jogo.</EmptyState>
  }
  return (
    <div className="space-y-3">
      <Totals charges={charges} />
      <ChargeList charges={charges} showGame />
    </div>
  )
}

// --- despesas ---

function Expenses({ month }) {
  const { data: expenses, isPending } = useExpenses(month)
  const remove = useDeleteExpense()
  const [formOpen, setFormOpen] = useState(false)
  const total = (expenses ?? []).reduce((sum, e) => sum + e.amount_cents, 0)

  function handleDelete(expense) {
    if (window.confirm(`Apagar a despesa "${expense.description}" de ${formatMoney(expense.amount_cents)}?`)) {
      remove.mutate(expense.id)
    }
  }

  return (
    // pb-16: espaço para o botão flutuante não cobrir a última despesa
    <div className="space-y-3 pb-16">
      {isPending ? (
        <LoadingList />
      ) : expenses.length === 0 ? (
        <EmptyState>Nenhuma despesa neste mês.</EmptyState>
      ) : (
        <>
          <p className="px-1 text-sm text-neutral-600 dark:text-neutral-300">
            Total do mês: <strong>{formatMoney(total)}</strong>
          </p>
          <ul className="space-y-2">
            {expenses.map((e) => (
              <li key={e.id} className="flex min-h-16 items-center gap-2 rounded-2xl bg-white py-2 pr-2 pl-3 shadow-sm dark:bg-neutral-900">
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-semibold">{e.description}</span>
                  <span className="mt-0.5 flex flex-wrap items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400">
                    <Badge>{EXPENSE_CATEGORY[e.category]}</Badge>
                    {e.type === 'fixed' && <Badge tone="blue">Fixa</Badge>}
                    <span>{formatShortDate(e.date)}</span>
                  </span>
                </span>
                <span className="shrink-0 font-semibold tabular-nums text-red-700 dark:text-red-300">
                  − {formatMoney(e.amount_cents)}
                </span>
                <Button variant="ghost" className="min-h-10 shrink-0 px-2 text-sm" onClick={() => handleDelete(e)} aria-label={`Apagar ${e.description}`}>
                  Apagar
                </Button>
              </li>
            ))}
          </ul>
        </>
      )}
      <Fab onClick={() => setFormOpen(true)}>
        <Plus size={22} aria-hidden />
        Despesa
      </Fab>
      <ExpenseSheet open={formOpen} onClose={() => setFormOpen(false)} />
    </div>
  )
}

const CATEGORY_OPTIONS = Object.entries(EXPENSE_CATEGORY).map(([value, label]) => ({ value, label }))

function todayIso() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function ExpenseSheet({ open, onClose }) {
  return (
    <Sheet open={open} onClose={onClose} title="Nova despesa">
      {open && <ExpenseForm onDone={onClose} />}
    </Sheet>
  )
}

function ExpenseForm({ onDone }) {
  const create = useCreateExpense()
  const [date, setDate] = useState(todayIso())
  const [category, setCategory] = useState('ball')
  const [description, setDescription] = useState('')
  const [amount, setAmount] = useState('')
  const [error, setError] = useState(null)

  function handleSubmit(e) {
    e.preventDefault()
    const cents = parseMoney(amount)
    if (!Number.isFinite(cents) || cents <= 0) {
      setError('Informe um valor válido, ex.: 150,00')
      return
    }
    setError(null)
    create.mutate({ date, category, description, amount_cents: cents }, { onSuccess: onDone })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <span className="mb-1 block text-sm font-medium">Categoria</span>
        <Segmented label="Categoria" options={CATEGORY_OPTIONS} value={category} onChange={setCategory} />
      </div>
      <TextField label="Valor (R$)" inputMode="decimal" placeholder="150,00" required value={amount} onChange={(e) => setAmount(e.target.value)} />
      <TextField label="Descrição" placeholder={EXPENSE_CATEGORY[category]} maxLength={200} value={description} onChange={(e) => setDescription(e.target.value)} hint="Opcional. Sem descrição, usamos o nome da categoria." />
      <TextField label="Data" type="date" required value={date} onChange={(e) => setDate(e.target.value)} />
      {(error || create.isError) && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error ?? create.error.message}
        </p>
      )}
      <Button type="submit" className="w-full" disabled={create.isPending}>
        {create.isPending ? 'Lançando…' : 'Lançar despesa'}
      </Button>
    </form>
  )
}

// --- extrato ---

function Statement({ month }) {
  const { data, isPending } = useStatement(month)
  if (isPending) return <LoadingList />
  return (
    <div className="space-y-3">
      <Card className="grid grid-cols-2 divide-x divide-neutral-200 p-0 dark:divide-neutral-800">
        <div className="px-4 py-3">
          <p className="text-xs text-neutral-500 dark:text-neutral-400">Início do mês</p>
          <p className="font-semibold tabular-nums">{formatMoney(data.opening_cents)}</p>
        </div>
        <div className="px-4 py-3">
          <p className="text-xs text-neutral-500 dark:text-neutral-400">Fim do mês</p>
          <p className="font-semibold tabular-nums">{formatMoney(data.closing_cents)}</p>
        </div>
      </Card>
      {data.entries.length === 0 ? (
        <EmptyState>Nenhuma movimentação neste mês.</EmptyState>
      ) : (
        <ul className="divide-y divide-neutral-200 rounded-2xl bg-white shadow-sm dark:divide-neutral-800 dark:bg-neutral-900">
          {data.entries.map((e, i) => {
            const income = e.amount_cents > 0
            return (
              <li key={i} className="flex min-h-14 items-center gap-3 px-4 py-2">
                <span className="w-10 shrink-0 text-xs text-neutral-500">{formatShortDate(e.day)}</span>
                <span className="min-w-0 flex-1 text-sm">
                  <span className="block truncate">{e.description}</span>
                  <span className="text-xs text-neutral-500">Saldo {formatMoney(e.balance_cents)}</span>
                </span>
                <span className={`shrink-0 text-sm font-semibold tabular-nums ${income ? 'text-brand-700 dark:text-brand-500' : 'text-red-700 dark:text-red-300'}`}>
                  {income ? '+ ' : '− '}
                  {formatMoney(Math.abs(e.amount_cents))}
                </span>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
