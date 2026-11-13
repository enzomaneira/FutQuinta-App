import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'

import { useLogin } from '../features/auth.js'
import { getToken } from '../lib/auth.js'

const inputClass =
  'mt-1 block min-h-12 w-full rounded-xl border border-neutral-300 bg-white px-3 text-base outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-600/30 dark:border-neutral-700 dark:bg-neutral-900'

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const login = useLogin()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  if (getToken() && !login.isPending) return <Navigate to="/" replace />

  function handleSubmit(e) {
    e.preventDefault()
    login.mutate(
      { email, password },
      { onSuccess: () => navigate(location.state?.from ?? '/', { replace: true }) },
    )
  }

  return (
    <div className="pt-safe flex min-h-dvh flex-col justify-center px-4">
      <div className="mx-auto w-full max-w-sm">
        <img src="/logo.svg" alt="" className="mx-auto size-16" />
        <h1 className="mt-4 text-center text-2xl font-bold">App Futebol</h1>
        <p className="mt-1 text-center text-sm text-neutral-600 dark:text-neutral-400">
          Acesso dos organizadores
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <label className="block text-sm font-medium">
            E-mail
            <input
              type="email"
              autoComplete="username"
              inputMode="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputClass}
            />
          </label>
          <label className="block text-sm font-medium">
            Senha
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClass}
            />
          </label>

          {login.isError && (
            <p role="alert" className="text-sm text-red-600 dark:text-red-400">
              {login.error.message}
            </p>
          )}

          <button
            type="submit"
            disabled={login.isPending}
            className="min-h-12 w-full rounded-xl bg-brand-700 text-base font-semibold text-white active:bg-brand-800 disabled:opacity-60"
          >
            {login.isPending ? 'Entrando…' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  )
}
