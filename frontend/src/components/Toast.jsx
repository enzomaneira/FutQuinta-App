import { createContext, useCallback, useContext, useRef, useState } from 'react'

// Aviso discreto de sucesso/erro, usado com as atualizações otimistas
const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const nextId = useRef(1)

  const show = useCallback((message, type = 'success') => {
    const id = nextId.current++
    setToasts((list) => [...list, { id, message, type }])
    setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), 3000)
  }, [])

  return (
    <ToastContext.Provider value={show}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-24 z-50 flex flex-col items-center gap-2 px-4"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role={t.type === 'error' ? 'alert' : 'status'}
            className={`pointer-events-auto max-w-sm rounded-xl px-4 py-3 text-sm font-medium shadow-lg ${
              t.type === 'error'
                ? 'bg-red-600 text-white'
                : 'bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900'
            }`}
          >
            {t.type === 'error' ? 'Erro: ' : ''}
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const show = useContext(ToastContext)
  if (!show) throw new Error('useToast precisa estar dentro de ToastProvider')
  return show
}
