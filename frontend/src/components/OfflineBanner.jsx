import { WifiOff } from 'lucide-react'
import { useEffect, useState } from 'react'

// Aviso discreto quando o celular perde a internet (comum na quadra)
export default function OfflineBanner() {
  const [online, setOnline] = useState(() => navigator.onLine)

  useEffect(() => {
    const update = () => setOnline(navigator.onLine)
    window.addEventListener('online', update)
    window.addEventListener('offline', update)
    return () => {
      window.removeEventListener('online', update)
      window.removeEventListener('offline', update)
    }
  }, [])

  if (online) return null
  return (
    <div
      role="status"
      className="flex items-center justify-center gap-2 bg-amber-100 px-4 py-2 text-sm font-medium text-amber-900 dark:bg-amber-900 dark:text-amber-50"
    >
      <WifiOff size={16} aria-hidden />
      Sem internet: mostrando os últimos dados. Alterações não serão salvas.
    </div>
  )
}
