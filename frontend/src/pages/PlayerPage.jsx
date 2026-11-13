import { MessageCircle, Pencil, Phone } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import PlayerProfileSections from '../components/PlayerProfileSections.jsx'
import PlayerFormSheet from '../components/PlayerFormSheet.jsx'
import { Badge, Button, Card, EmptyState, LoadingList } from '../components/ui.jsx'
import { useDeletePlayer, usePlayer, useUpdatePlayer } from '../features/players.js'
import {
  PAYMENT_STATUS,
  POSITION_LABEL,
  TYPE_LABEL,
  formatPhone,
  whatsappUrl,
} from '../lib/format.js'

const linkButton =
  'inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-neutral-200 px-4 text-base font-semibold active:bg-neutral-300 dark:bg-neutral-800 dark:active:bg-neutral-700'

export default function PlayerPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data: player, isPending, isError, error } = usePlayer(id)
  const update = useUpdatePlayer(id)
  const remove = useDeletePlayer()
  const [editing, setEditing] = useState(false)

  if (isPending) return <LoadingList />
  if (isError) return <EmptyState>{error.message}</EmptyState>

  function toggleActive() {
    const verb = player.active ? 'Desativar' : 'Reativar'
    if (player.active && !window.confirm(`${verb} ${player.name}?`)) return
    update.mutate({ active: !player.active })
  }

  function handleDelete() {
    if (!window.confirm(`Excluir ${player.name}? Isso não pode ser desfeito.`)) return
    remove.mutate(player.id, { onSuccess: () => navigate('/jogadores', { replace: true }) })
  }

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-xl font-bold break-words">{player.name}</h2>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <Badge tone={player.position === 'goalkeeper' ? 'blue' : 'neutral'}>
                {POSITION_LABEL[player.position]}
              </Badge>
              <Badge tone={player.type === 'monthly' ? 'green' : 'neutral'}>
                {TYPE_LABEL[player.type]}
              </Badge>
              <Badge tone={player.active ? 'green' : 'amber'}>
                {player.active ? 'Ativo' : 'Inativo'}
              </Badge>
              {player.payment_status && (
                <Badge tone={PAYMENT_STATUS[player.payment_status].tone}>
                  {PAYMENT_STATUS[player.payment_status].label}
                </Badge>
              )}
            </div>
          </div>
          <Button variant="ghost" onClick={() => setEditing(true)} aria-label="Editar jogador" className="-mr-2 px-3">
            <Pencil size={20} aria-hidden />
          </Button>
        </div>

        {player.phone ? (
          <>
            <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-400">
              {formatPhone(player.phone)}
            </p>
            <div className="mt-2 flex gap-2">
              <a className={linkButton} href={whatsappUrl(player.phone)} target="_blank" rel="noreferrer">
                <MessageCircle size={20} aria-hidden />
                WhatsApp
              </a>
              <a className={linkButton} href={`tel:${player.phone}`}>
                <Phone size={20} aria-hidden />
                Ligar
              </a>
            </div>
          </>
        ) : (
          <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-400">Sem telefone cadastrado.</p>
        )}
      </Card>

      <PlayerProfileSections playerId={player.id} />

      <div className="space-y-2">
        <Button variant="secondary" className="w-full" onClick={toggleActive} disabled={update.isPending}>
          {player.active ? 'Desativar jogador' : 'Reativar jogador'}
        </Button>
        {player.can_delete && (
          <Button variant="ghost" className="w-full text-red-700 dark:text-red-400" onClick={handleDelete} disabled={remove.isPending}>
            Excluir cadastro
          </Button>
        )}
      </div>

      <PlayerFormSheet open={editing} onClose={() => setEditing(false)} player={player} />
    </div>
  )
}
