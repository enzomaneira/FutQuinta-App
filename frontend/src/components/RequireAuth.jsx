import { Navigate, useLocation } from 'react-router'

import { useMe } from '../features/auth.js'
import { getToken } from '../lib/auth.js'

export default function RequireAuth({ children }) {
  const location = useLocation()
  const hasToken = Boolean(getToken())
  const me = useMe()

  if (!hasToken || me.isError) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  if (me.isPending) {
    return (
      <div className="flex min-h-dvh items-center justify-center text-neutral-500">
        Carregando…
      </div>
    )
  }
  return children
}
