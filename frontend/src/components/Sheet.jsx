import { X } from 'lucide-react'
import { useEffect } from 'react'
import { createPortal } from 'react-dom'

// Painel que sobe da parte de baixo da tela (padrão de formulário no celular)
export default function Sheet({ open, onClose, title, children }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    const { overflow } = document.body.style
    document.body.style.overflow = 'hidden' // trava a rolagem do fundo
    // O fundo fica inerte: sem foco nem leitura por leitor de tela
    const root = document.getElementById('root')
    root?.setAttribute('inert', '')
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = overflow
      root?.removeAttribute('inert')
    }
  }, [open, onClose])

  if (!open) return null

  // Renderizado fora do #root (portal) para não ficar inerte junto com o fundo
  return createPortal(
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={title}>
      <button
        type="button"
        aria-label="Fechar"
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />
      <div className="pb-safe absolute inset-x-0 bottom-0 mx-auto flex max-h-[90dvh] max-w-2xl flex-col rounded-t-2xl bg-white shadow-xl dark:bg-neutral-900">
        <div className="flex items-center justify-between px-4 pt-2 pb-1">
          <span className="text-base font-semibold">{title}</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar"
            className="-mr-2 flex size-11 items-center justify-center rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-800"
          >
            <X size={22} aria-hidden />
          </button>
        </div>
        <div className="overflow-y-auto px-4 pb-4">{children}</div>
      </div>
    </div>,
    document.body,
  )
}
