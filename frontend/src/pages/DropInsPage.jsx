import { Plus } from 'lucide-react'
import { useState } from 'react'

import PlayerFormSheet from '../components/PlayerFormSheet.jsx'
import PlayerList from '../components/PlayerList.jsx'
import { Card, Fab } from '../components/ui.jsx'

export default function DropInsPage() {
  const [formOpen, setFormOpen] = useState(false)
  return (
    <div className="space-y-4 pb-16">
      <Card className="text-sm text-neutral-600 dark:text-neutral-300">
        A fila de cada jogo segue a ordem em que o avulso se candidata. Ela aparece na
        tela <strong>Jogo</strong>, junto com o botão de chamar.
      </Card>
      <PlayerList filters={{ type: 'drop_in' }} emptyText="Nenhum avulso cadastrado ainda." />

      <Fab onClick={() => setFormOpen(true)}>
        <Plus size={22} aria-hidden />
        Novo avulso
      </Fab>
      <PlayerFormSheet open={formOpen} onClose={() => setFormOpen(false)} defaultType="drop_in" />
    </div>
  )
}
