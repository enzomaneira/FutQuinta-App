import { Search } from 'lucide-react'
import { useMemo, useState } from 'react'

import { usePlayers } from '../features/players.js'
import { POSITION_LABEL, TYPE_LABEL } from '../lib/format.js'
import Sheet from './Sheet.jsx'
import { Badge, EmptyState, LoadingList, inputClass } from './ui.jsx'

/**
 * Painel para escolher um jogador ativo.
 * `exclude`: ids que não aparecem; `filter(player)`: filtro extra.
 */
export default function PlayerPicker({ open, onClose, title, onPick, exclude = [], filter, hint }) {
  return (
    <Sheet open={open} onClose={onClose} title={title}>
      {open && <PickerBody onPick={onPick} exclude={exclude} filter={filter} hint={hint} />}
    </Sheet>
  )
}

function PickerBody({ onPick, exclude, filter, hint }) {
  const [search, setSearch] = useState('')
  const { data: players, isPending } = usePlayers({})

  const options = useMemo(() => {
    const term = search.trim().toLowerCase()
    return (players ?? []).filter(
      (p) =>
        !exclude.includes(p.id) &&
        (!filter || filter(p)) &&
        (!term || p.name.toLowerCase().includes(term)),
    )
  }, [players, exclude, filter, search])

  return (
    <div className="space-y-3">
      {hint && <p className="text-sm text-neutral-600 dark:text-neutral-400">{hint}</p>}
      <label className="relative block">
        <span className="sr-only">Buscar jogador</span>
        <Search
          size={18}
          className="pointer-events-none absolute top-1/2 left-3 mt-0.5 -translate-y-1/2 text-neutral-400"
          aria-hidden
        />
        <input
          type="search"
          placeholder="Buscar jogador"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className={`${inputClass} pl-10`}
        />
      </label>
      {isPending ? (
        <LoadingList />
      ) : options.length === 0 ? (
        <EmptyState>Nenhum jogador disponível.</EmptyState>
      ) : (
        <ul className="-mx-2">
          {options.map((player) => (
            <li key={player.id}>
              <button
                type="button"
                onClick={() => onPick(player)}
                className="flex min-h-12 w-full items-center justify-between gap-2 rounded-xl px-3 text-left hover:bg-neutral-100 dark:hover:bg-neutral-800"
              >
                <span className="truncate font-medium">{player.name}</span>
                <span className="flex shrink-0 gap-1">
                  <Badge tone={player.position === 'goalkeeper' ? 'blue' : 'neutral'}>
                    {POSITION_LABEL[player.position]}
                  </Badge>
                  <Badge>{TYPE_LABEL[player.type]}</Badge>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
