import { useState } from 'react'

import { useCreatePlayer, useUpdatePlayer } from '../features/players.js'
import { formatPhone } from '../lib/format.js'
import Sheet from './Sheet.jsx'
import { Button, Segmented, TextField } from './ui.jsx'

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

  const create = useCreatePlayer()
  const update = useUpdatePlayer(player?.id)
  const mutation = player ? update : create

  function handleSubmit(e) {
    e.preventDefault()
    const body = { name, phone: phone.trim() || null, position, type }
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
