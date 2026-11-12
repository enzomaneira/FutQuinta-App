import { Plus } from 'lucide-react'
import { useState } from 'react'

import PlayerFormSheet from '../components/PlayerFormSheet.jsx'
import PlayerList from '../components/PlayerList.jsx'
import { Card, Fab, Segmented } from '../components/ui.jsx'
import { useMonthlySlots } from '../features/players.js'

const TABS = [
  { value: 'monthly', label: 'Mensalistas' },
  { value: 'drop_in', label: 'Avulsos' },
  { value: 'inactive', label: 'Inativos' },
]

const TAB_FILTERS = {
  monthly: { type: 'monthly' },
  drop_in: { type: 'drop_in' },
  inactive: { status: 'inactive' },
}

const EMPTY_TEXT = {
  monthly: 'Nenhum mensalista cadastrado ainda.',
  drop_in: 'Nenhum avulso cadastrado ainda.',
  inactive: 'Nenhum jogador inativo.',
}

export default function PlayersPage() {
  const [tab, setTab] = useState('monthly')
  const [formOpen, setFormOpen] = useState(false)

  return (
    <div className="space-y-4 pb-16">
      <Segmented label="Filtrar jogadores" options={TABS} value={tab} onChange={setTab} />
      {tab === 'monthly' && <MonthlySlots />}
      <PlayerList
        filters={TAB_FILTERS[tab]}
        emptyText={EMPTY_TEXT[tab]}
        showType={tab === 'inactive'}
      />

      <Fab onClick={() => setFormOpen(true)}>
        <Plus size={22} aria-hidden />
        Novo
      </Fab>
      <PlayerFormSheet
        open={formOpen}
        onClose={() => setFormOpen(false)}
        defaultType={tab === 'drop_in' ? 'drop_in' : 'monthly'}
      />
    </div>
  )
}

// Vagas garantidas ocupadas por mensalistas (ex.: Goleiros 2/2, Linha 14/15)
function MonthlySlots() {
  const { data } = useMonthlySlots()
  if (!data) return null
  const items = [
    ['Goleiros', data.goalkeeper],
    ['Linha', data.field],
  ]
  return (
    <Card className="grid grid-cols-2 divide-x divide-neutral-200 p-0 dark:divide-neutral-800">
      {items.map(([label, { used, total }]) => (
        <div key={label} className="px-4 py-3">
          <p className="text-xs text-neutral-500 dark:text-neutral-400">{label} mensalistas</p>
          <p className="text-lg font-semibold">
            {used}/{total}
            {used < total && (
              <span className="ml-2 text-xs font-medium text-amber-700 dark:text-amber-300">
                {total - used} {total - used === 1 ? 'vaga' : 'vagas'} livre{total - used === 1 ? '' : 's'}
              </span>
            )}
          </p>
        </div>
      ))}
    </Card>
  )
}
