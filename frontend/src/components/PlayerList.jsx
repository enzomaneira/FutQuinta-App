import { Search } from 'lucide-react'
import { useDeferredValue, useState } from 'react'

import { usePlayers } from '../features/players.js'
import PlayerCard from './PlayerCard.jsx'
import { EmptyState, LoadingList, inputClass } from './ui.jsx'

/** Busca + lista de jogadores, separada em Goleiros e Linha. */
export default function PlayerList({ filters, emptyText, showType = false }) {
  const [search, setSearch] = useState('')
  const q = useDeferredValue(search.trim())
  const { data: players, isPending, isError, error } = usePlayers({ ...filters, q })

  const goalkeepers = players?.filter((p) => p.position === 'goalkeeper') ?? []
  const field = players?.filter((p) => p.position === 'field') ?? []

  return (
    <div className="space-y-4">
      <label className="relative block">
        <span className="sr-only">Buscar por nome ou telefone</span>
        <Search
          size={18}
          className="pointer-events-none absolute top-1/2 left-3 mt-0.5 -translate-y-1/2 text-neutral-400"
          aria-hidden
        />
        <input
          type="search"
          placeholder="Buscar por nome ou telefone"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className={`${inputClass} pl-10`}
        />
      </label>

      {isPending ? (
        <LoadingList />
      ) : isError ? (
        <EmptyState>{error.message}</EmptyState>
      ) : players.length === 0 ? (
        <EmptyState>{q ? 'Ninguém encontrado com essa busca.' : emptyText}</EmptyState>
      ) : (
        <>
          <Group title="Goleiros" players={goalkeepers} showType={showType} />
          <Group title="Linha" players={field} showType={showType} />
        </>
      )}
    </div>
  )
}

function Group({ title, players, showType }) {
  if (players.length === 0) return null
  return (
    <section>
      <h3 className="mb-2 px-1 text-sm font-semibold text-neutral-500 dark:text-neutral-400">
        {title} ({players.length})
      </h3>
      <ul className="space-y-2">
        {players.map((player) => (
          <li key={player.id}>
            <PlayerCard player={player} showType={showType} />
          </li>
        ))}
      </ul>
    </section>
  )
}
