import { useRouteError } from 'react-router'

// Tela mostrada quando algo quebra ao abrir uma página. O caso mais comum é
// uma versão nova publicada enquanto o app estava aberto: recarregar resolve.
export default function ErrorPage() {
  const error = useRouteError()
  console.error(error)
  return (
    <div className="pt-safe flex min-h-dvh flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="text-lg font-semibold">Algo deu errado ao abrir esta tela</p>
      <p className="text-sm text-neutral-600 dark:text-neutral-400">
        Pode ser uma versão nova do app. Recarregar costuma resolver.
      </p>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className="min-h-12 w-full max-w-xs rounded-xl bg-brand-700 font-semibold text-white"
      >
        Recarregar
      </button>
      <a href="/" className="inline-flex min-h-11 items-center text-sm font-semibold underline">
        Ir para o início
      </a>
    </div>
  )
}
