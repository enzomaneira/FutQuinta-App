import { useState } from 'react'

import { useCreatePlayer, usePlayers, useUpdatePlayer } from '../features/players.js'
import { formatPhone } from '../lib/format.js'
import Sheet from './Sheet.jsx'
import { Button, Segmented, TextField, inputClass } from './ui.jsx'

const POSITION_OPTIONS = [
  { value: 'field', label: 'Linha' },
  { value: 'goalkeeper', label: 'Goleiro' },
]
const TYPE_OPTIONS = [
  { value: 'monthly', label: 'Mensalista' },
  { value: 'drop_in', label: 'Avulso' },
]

/**
 * Cadastro e edição de jogador.
 * - Novo: `player` vazio; `defaultType` pré-seleciona o tipo (ex.: tela de Avulsos)
 * - Edição: `player` preenchido
 */
export default function PlayerFormSheet({ open, onClose, player, defaultType = 'monthly' }) {
  return (
    <Sheet open={open} onClose={onClose} title={player ? 'Editar jogador' : 'Novo jogador'}>
      {/* key recria o formulário com os valores certos a cada abertura */}
      {open && (
        <PlayerForm key={player?.id ?? 'new'} player={player} defaultType={defaultType} onDone={onClose} />
      )}
    </Sheet>
  )
}

function PlayerForm({ player, defaultType, onDone }) {
  const [name, setName] = useState(player?.name ?? '')
  const [phone, setPhone] = useState(player ? formatPhone(player.phone) : '')
  const [position, setPosition] = useState(player?.position ?? 'field')
  const [type, setType] = useState(player?.type ?? defaultType)
  // '' = ninguém; guardado como texto porque vem de um <select>
  const [referredBy, setReferredBy] = useState(player?.referred_by_id ? String(player.referred_by_id) : '')

  const create = useCreatePlayer()
  const update = useUpdatePlayer(player?.id)
  const mutation = player ? update : create

  function handleSubmit(e) {
    e.preventDefault()
    const body = { name, phone: phone.trim() || null, position, type }
    // "Trazido por" só existe para avulso (mensalista não tem)
    if (type === 'drop_in') body.referred_by_id = referredBy ? Number(referredBy) : null
    mutation.mutate(body, { onSuccess: onDone })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <TextField
        label="Nome"
        required
        maxLength={120}
        autoComplete="off"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <TextField
        label="Telefone (WhatsApp)"
        type="tel"
        inputMode="tel"
        autoComplete="off"
        placeholder="(11) 98765-4321"
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
        hint="Opcional. Sem DDI, consideramos Brasil (+55)."
      />
      <div>
        <span className="mb-1 block text-sm font-medium">Posição</span>
        <Segmented label="Posição" options={POSITION_OPTIONS} value={position} onChange={setPosition} />
      </div>
      <div>
        <span className="mb-1 block text-sm font-medium">Tipo</span>
        <Segmented label="Tipo" options={TYPE_OPTIONS} value={type} onChange={setType} />
      </div>
      {type === 'drop_in' && (
        <ReferrerSelect value={referredBy} onChange={setReferredBy} current={player} />
      )}

      {/* Na criação o erro aparece aqui; na edição o hook também mostra um aviso */}
      {mutation.isError && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {mutation.error.message}
        </p>
      )}

      <Button type="submit" className="w-full" disabled={mutation.isPending}>
        {mutation.isPending ? 'Salvando…' : player ? 'Salvar' : 'Cadastrar'}
      </Button>
    </form>
  )
}

/** Lista de mensalistas ativos para "Trazido por". Se o mensalista atual foi
 * desativado depois, ele continua aparecendo para não perder o vínculo. */
function ReferrerSelect({ value, onChange, current }) {
  const { data: monthly = [] } = usePlayers({ type: 'monthly' })
  const options = monthly.map((p) => ({ id: String(p.id), name: p.name }))
  if (current?.referred_by_id && !options.some((o) => o.id === String(current.referred_by_id))) {
    options.push({ id: String(current.referred_by_id), name: `${current.referred_by_name} (inativo)` })
  }
  return (
    <label className="block text-sm font-medium">
      Trazido por (mensalista)
      <select value={value} onChange={(e) => onChange(e.target.value)} className={inputClass}>
        <option value="">Ninguém / não sei</option>
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>
      <span className="mt-1 block text-xs text-neutral-600 dark:text-neutral-400">Opcional.</span>
    </label>
  )
}
