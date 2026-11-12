import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useToast } from '../components/Toast.jsx'
import { api } from '../lib/api.js'

export function useSettings() {
  return useQuery({ queryKey: ['settings'], queryFn: () => api('/settings') })
}

export function useSaveSettings() {
  const queryClient = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: (changes) => api('/settings', { method: 'PATCH', body: changes }),
    onSuccess: (settings) => {
      queryClient.setQueryData(['settings'], settings)
      queryClient.invalidateQueries({ queryKey: ['games'] })
      queryClient.invalidateQueries({ queryKey: ['players', 'monthly-slots'] })
      toast('Configurações salvas')
    },
    onError: (error) => toast(error.message, 'error'),
  })
}

export function useUsers() {
  return useQuery({ queryKey: ['users'], queryFn: () => api('/users') })
}

export function useCreateUser() {
  const queryClient = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: (body) => api('/users', { method: 'POST', body }),
    onSuccess: (user) => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast(`${user.email} pode entrar no app`)
    },
  })
}

export function useSetUserActive() {
  const queryClient = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: ({ id, active }) => api(`/users/${id}`, { method: 'PATCH', body: { active } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
    onError: (error) => toast(error.message, 'error'),
  })
}
