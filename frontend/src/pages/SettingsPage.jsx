import { useState } from 'react'

import { Badge, Button, Card, LoadingList, TextField, inputClass } from '../components/ui.jsx'
import { useMe } from '../features/auth.js'
import {
  useCreateUser,
  useSaveSettings,
  useSetUserActive,
  useSettings,
  useUsers,
} from '../features/settings.js'
import { parseMoney } from '../lib/format.js'

const WEEKDAY_OPTIONS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']

const SECTIONS = [
  {
    title: 'Local',
    fields: [
      { key: 'venue_name', label: 'Nome do local', type: 'text' },
      { key: 'venue_address', label: 'Endereço', type: 'text' },
      { key: 'venue_lat', label: 'Latitude', type: 'coord', hint: 'Ex.: -23.5899 (usada no mapa)' },
      { key: 'venue_lng', label: 'Longitude', type: 'coord', hint: 'Ex.: -46.6355' },
    ],
  },
  {
    title: 'Jogo',
    note: 'Valem para os próximos jogos; jogos já criados mantêm horário e vagas.',
    fields: [
      { key: 'game_weekday', label: 'Dia da semana', type: 'weekday' },
      { key: 'game_start_time', label: 'Início', type: 'time' },
      { key: 'game_end_time', label: 'Fim', type: 'time' },
      { key: 'goalkeeper_slots', label: 'Vagas de goleiro', type: 'int' },
      { key: 'field_slots', label: 'Vagas de linha', type: 'int' },
    ],
  },
  {
    title: 'Lista semanal',
    fields: [
      { key: 'list_open_days_before', label: 'Lista abre quantos dias antes do jogo', type: 'int', hint: '2 = terça, para jogo na quinta' },
      { key: 'list_open_time', label: 'Horário em que a lista abre', type: 'time' },
      { key: 'confirmation_deadline_time', label: 'Prazo de confirmação dos mensalistas (no dia do jogo)', type: 'time', hint: 'Depois disso, pendentes perdem a vaga garantida' },
      { key: 'late_cancellation_time', label: 'Desistência em cima da hora a partir de (no dia do jogo)', type: 'time' },
    ],
  },
  {
    title: 'Valores',
    fields: [
      { key: 'monthly_fee_cents', label: 'Mensalidade', type: 'money' },
      { key: 'drop_in_fee_cents', label: 'Avulso (por jogo)', type: 'money' },
      { key: 'court_monthly_cents', label: 'Aluguel mensal da quadra', type: 'money' },
      { key: 'initial_cash_cents', label: 'Saldo inicial do caixa', type: 'money' },
    ],
  },
  {
    title: 'Cobrança',
    fields: [
      { key: 'billing_day', label: 'Dia em que as mensalidades são geradas', type: 'int' },
      { key: 'monthly_due_day', label: 'Dia do vencimento', type: 'int', hint: 'No dia seguinte, quem não pagou fica atrasado' },
    ],
  },
  {
    title: 'Pix',
    fields: [{ key: 'pix_key', label: 'Chave Pix', type: 'text', hint: 'Mostrada para os jogadores pagarem' }],
  },
]

// Valor da API -> texto do campo
function toInput(type, value) {
  if (type === 'money') return (value / 100).toFixed(2).replace('.', ',')
  return String(value ?? '')
}

// Texto do campo -> valor da API (lança erro com mensagem amigável)
function fromInput(field, text) {
  const value = text.trim()
  switch (field.type) {
    case 'money': {
      const cents = parseMoney(value)
      if (!Number.isFinite(cents)) throw new Error(`${field.label}: valor inválido`)
      return cents
    }
    case 'int':
    case 'weekday': {
      const number = Number(value)
      if (!Number.isInteger(number)) throw new Error(`${field.label}: use um número inteiro`)
      return number
    }
    case 'coord': {
      const number = Number(value.replace(',', '.'))
      if (value === '' || Number.isNaN(number)) throw new Error(`${field.label}: número inválido`)
      return number
    }
    default:
      return value
  }
}

export default function SettingsPage() {
  const { data: settings, isPending } = useSettings()
  if (isPending) return <LoadingList />
  return (
    <div className="space-y-4">
      {SECTIONS.map((section) => (
        <SettingsSection
          // Recria o formulário quando os valores salvos mudam
          key={`${section.title}-${section.fields.map((f) => settings[f.key]).join('|')}`}
          section={section}
          settings={settings}
        />
      ))}
      <OrganizersSection />
    </div>
  )
}

function SettingsSection({ section, settings }) {
  const save = useSaveSettings()
  const initial = Object.fromEntries(section.fields.map((f) => [f.key, toInput(f.type, settings[f.key])]))
  const [values, setValues] = useState(initial)
  const [error, setError] = useState(null)
  const dirty = section.fields.some((f) => values[f.key] !== initial[f.key])

  function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    try {
      const changes = {}
      for (const field of section.fields) {
        if (values[field.key] !== initial[field.key]) changes[field.key] = fromInput(field, values[field.key])
      }
      save.mutate(changes)
    } catch (err) {
      setError(err.message)
    }
  }

  const set = (key) => (e) => setValues((v) => ({ ...v, [key]: e.target.value }))

  return (
    <Card as="form" onSubmit={handleSubmit} className="space-y-3">
      <h2 className="text-base font-semibold">{section.title}</h2>
      {section.note && <p className="text-xs text-neutral-600 dark:text-neutral-400">{section.note}</p>}
      {section.fields.map((field) =>
        field.type === 'weekday' ? (
          <label key={field.key} className="block text-sm font-medium">
            {field.label}
            <select value={values[field.key]} onChange={set(field.key)} className={inputClass}>
              {WEEKDAY_OPTIONS.map((name, index) => (
                <option key={name} value={String(index)}>
                  {name}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <TextField
            key={field.key}
            label={field.type === 'money' ? `${field.label} (R$)` : field.label}
            hint={field.hint}
            value={values[field.key]}
            onChange={set(field.key)}
            type={field.type === 'time' ? 'time' : 'text'}
            inputMode={
              field.type === 'int' ? 'numeric' : field.type === 'money' || field.type === 'coord' ? 'decimal' : undefined
            }
          />
        ),
      )}
      {error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
      <Button type="submit" className="w-full" disabled={!dirty || save.isPending}>
        {save.isPending ? 'Salvando…' : dirty ? 'Salvar' : 'Sem alterações'}
      </Button>
    </Card>
  )
}

function OrganizersSection() {
  const { data: me } = useMe()
  const { data: users, isPending } = useUsers()
  const setActive = useSetUserActive()
  const isAdmin = me?.role === 'admin'

  return (
    <Card className="space-y-3">
      <h2 className="text-base font-semibold">Organizadores</h2>
      {isPending ? (
        <LoadingList />
      ) : (
        <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
          {users.map((user) => (
            <li key={user.id} className="flex min-h-14 items-center justify-between gap-2 py-2">
              <span className="min-w-0">
                <span className="block truncate text-sm font-medium">{user.email}</span>
                <span className="mt-0.5 flex gap-1">
                  <Badge tone={user.role === 'admin' ? 'blue' : 'neutral'}>
                    {user.role === 'admin' ? 'Admin' : 'Organizador'}
                  </Badge>
                  {!user.active && <Badge tone="amber">Sem acesso</Badge>}
                </span>
              </span>
              {isAdmin && user.id !== me.id && (
                <Button
                  variant="secondary"
                  className="shrink-0 px-3 text-sm"
                  disabled={setActive.isPending}
                  onClick={() => setActive.mutate({ id: user.id, active: !user.active })}
                >
                  {user.active ? 'Remover acesso' : 'Devolver acesso'}
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
      {isAdmin ? (
        <NewOrganizerForm />
      ) : (
        <p className="text-xs text-neutral-600 dark:text-neutral-400">Só administradores adicionam ou removem organizadores.</p>
      )}
    </Card>
  )
}

function NewOrganizerForm() {
  const create = useCreateUser()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [admin, setAdmin] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    create.mutate(
      { email, password, admin },
      {
        onSuccess: () => {
          setEmail('')
          setPassword('')
          setAdmin(false)
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 border-t border-neutral-200 pt-3 dark:border-neutral-800">
      <p className="text-sm font-medium">Adicionar organizador</p>
      <TextField label="E-mail" type="email" required autoComplete="off" value={email} onChange={(e) => setEmail(e.target.value)} />
      <TextField
        label="Senha inicial"
        type="password"
        required
        minLength={8}
        autoComplete="new-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        hint="Mínimo de 8 caracteres. Passe para a pessoa por um canal seguro."
      />
      <label className="flex min-h-11 items-center gap-3 text-sm">
        <input type="checkbox" checked={admin} onChange={(e) => setAdmin(e.target.checked)} className="size-5" />
        Pode gerenciar organizadores (admin)
      </label>
      {create.isError && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {create.error.message}
        </p>
      )}
      <Button type="submit" variant="secondary" className="w-full" disabled={create.isPending}>
        {create.isPending ? 'Adicionando…' : 'Adicionar'}
      </Button>
    </form>
  )
}
