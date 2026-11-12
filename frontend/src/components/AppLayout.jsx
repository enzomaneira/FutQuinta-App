import { ChevronLeft, Menu } from 'lucide-react'
import { useCallback, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router'

import BottomNav, { NAV_ITEMS } from './BottomNav.jsx'
import MoreSheet from './MoreSheet.jsx'

const EXTRA_TITLES = {
  '/avulsos': 'Avulsos',
  '/historico': 'Histórico',
  '/configuracoes': 'Configurações',
}

// Telas de detalhe: título próprio e botão de voltar
const DETAIL_PAGES = [
  { prefix: '/jogadores/', title: 'Jogador', back: '/jogadores' },
  { prefix: '/jogos/', title: 'Jogo', back: '/calendario' },
  { prefix: '/historico/', title: 'Jogo realizado', back: '/historico' },
]

function pageInfo(pathname) {
  const detail = DETAIL_PAGES.find((d) => pathname.startsWith(d.prefix))
  if (detail) return { title: detail.title, back: detail.back }
  const item = NAV_ITEMS.find((i) => i.to === pathname)
  return { title: item?.label ?? EXTRA_TITLES[pathname] ?? 'App Futebol' }
}

// Estrutura das telas logadas: cabeçalho com "Mais" + conteúdo + navegação inferior
export default function AppLayout() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const page = pageInfo(pathname)
  const [moreOpen, setMoreOpen] = useState(false)
  const closeMore = useCallback(() => setMoreOpen(false), [])

  return (
    <div className="min-h-dvh">
      <header className="pt-safe sticky top-0 z-30 border-b border-neutral-200 bg-white/95 backdrop-blur dark:border-neutral-800 dark:bg-neutral-900/95">
        <div className="mx-auto flex h-14 max-w-2xl items-center justify-between px-4">
          <div className="flex min-w-0 items-center gap-1">
            {page.back && (
              <button
                type="button"
                onClick={() => (window.history.length > 1 ? navigate(-1) : navigate(page.back))}
                aria-label="Voltar"
                className="-ml-2 flex size-11 items-center justify-center rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-800"
              >
                <ChevronLeft size={24} aria-hidden />
              </button>
            )}
            <h1 className="truncate text-lg font-semibold">{page.title}</h1>
          </div>
          <button
            type="button"
            onClick={() => setMoreOpen(true)}
            className="-mr-2 flex min-h-11 items-center gap-1.5 rounded-full px-3 text-sm font-medium hover:bg-neutral-100 dark:hover:bg-neutral-800"
          >
            <Menu size={20} aria-hidden />
            Mais
          </button>
        </div>
      </header>

      {/* pb-24 deixa espaço para a navegação inferior fixa */}
      <main className="mx-auto max-w-2xl px-4 pt-4 pb-24">
        <Outlet />
      </main>

      <BottomNav />
      <MoreSheet open={moreOpen} onClose={closeMore} />
    </div>
  )
}
