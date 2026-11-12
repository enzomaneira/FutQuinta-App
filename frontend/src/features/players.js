import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useToast } from '../components/Toast.jsx'
import { api } from '../lib/api.js'

export const playerKeys = {
  all: ['players'],
  list: (filters) => ['players', 'list', filters],
  detail: (id) => ['players', 'detail', Number(id)],
  slots: ['players', 'monthly-slots'],
}

/** filters: { type, position, status: 'active'|'inactive'|'all', q } */
export function usePlayers(filters = {}) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== '') params.set(key, value)
  }
  const query = params.toString()
  return useQuery({
    queryKey: playerKeys.list(filters),
    queryFn: () => api(`/players${query ? `?${query}` : ''}`),
    placeholderData: (previous) => previous, // evita "piscar" ao trocar filtro/busca
  })
}

export function usePlayer(id) {
  return useQuery({
    queryKey: playerKeys.detail(id),
    queryFn: () => api(`/players/${id}`),
  })
}

export function useMonthlySlots() {
  return useQuery({ queryKey: playerKeys.slots, queryFn: () => api('/players/monthly-slots') })
}

export function useCreatePlayer() {
  const queryClient = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: (body) => api('/players', { method: 'POST', body }),
    onSuccess: (player) => {
      toast(`${player.name} cadastrado`)
      queryClient.invalidateQueries({ queryKey: playerKeys.all })
    },
  })
}

/** Atualização otimista: a tela muda na hora e volta atrás se a API recusar. */
export function useUpdatePlayer(id) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const key = playerKeys.detail(id)
  return useMutation({
    mutationFn: (changes) => api(`/players/${id}`, { method: 'PATCH', body: changes }),
    onMutate: async (changes) => {
      await queryClient.cancelQueries({ queryKey: key })
      const previous = queryClient.getQueryData(key)
      if (previous) queryClient.setQueryData(key, { ...previous, ...changes })
      return { previous }
    },
    onError: (error, _changes, context) => {
      if (context?.previous) queryClient.setQueryData(key, context.previous)
      toast(error.message, 'error')
    },
    onSuccess: () => toast('Alterações salvas'),
    onSettled: () => queryClient.invalidateQueries({ queryKey: playerKeys.all }),
  })
}

export function useDeletePlayer() {
  const queryClient = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: (id) => api(`/players/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      toast('Jogador excluído')
      queryClient.invalidateQueries({ queryKey: playerKeys.all })
    },
    onError: (error) => toast(error.message, 'error'),
  })
}
