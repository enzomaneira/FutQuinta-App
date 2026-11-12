import Placeholder from '../components/Placeholder.jsx'
import { useMe } from '../features/auth.js'

export default function HomePage() {
  const { data: me } = useMe()
  return (
    <div className="space-y-3">
      <p className="text-sm text-neutral-500 dark:text-neutral-400">Olá, {me?.email}</p>
      <Placeholder title="Próximo jogo" stage="1.5">
        Data, contagem de confirmados, goleiros e coletes.
      </Placeholder>
      <Placeholder title="Caixa atual" stage="1.5" />
      <Placeholder title="Local e mapa" stage="1.5" />
    </div>
  )
}
