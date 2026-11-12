import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '../lib/api.js'
import { clearToken, getToken, setToken } from '../lib/auth.js'

export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: () => api('/auth/me'),
    enabled: Boolean(getToken()),
    staleTime: 5 * 60_000,
  })
}

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (credentials) =>
      api('/auth/login', { method: 'POST', body: credentials }),
    onSuccess: (data) => {
      setToken(data.access_token)
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return () => {
    clearToken()
    queryClient.clear()
    window.location.assign('/login')
  }
}
