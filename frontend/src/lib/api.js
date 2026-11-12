import { clearToken, getToken } from './auth.js'

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

/**
 * Chamada à API com JWT. Em 401 limpa a sessão e volta para o login.
 */
export async function api(path, { method = 'GET', body } = {}) {
  const headers = { Accept: 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let response
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'Sem conexão. Verifique a internet.')
  }

  if (response.status === 204) return null
  const data = await response.json().catch(() => null)

  if (!response.ok) {
    if (response.status === 401 && path !== '/auth/login') {
      clearToken()
      if (window.location.pathname !== '/login') window.location.assign('/login')
    }
    throw new ApiError(response.status, errorMessage(data, response.status))
  }
  return data
}

function errorMessage(data, status) {
  const detail = data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return 'Dados inválidos. Confira os campos.'
  if (status >= 500) return 'Erro no servidor. Tente de novo.'
  return 'Algo deu errado.'
}
