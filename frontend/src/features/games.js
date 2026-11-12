import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useToast } from '../components/Toast.jsx'
import { api } from '../lib/api.js'

export const gameKeys = {
  all: ['games'],
  current: ['games', 'current'],
  detail: (id) => ['games', 'detail', Number(id)],
  calendar: (month) => ['games', 'calendar', month ?? 'atual'],
}

export function useCurrentGame() {
  return useQuery({ queryKey: gameKeys.current, queryFn: () => api('/games/current') })
}

export function useGame(id) {
  return useQuery({ queryKey: gameKeys.detail(id), queryFn: () => api(`/games/${id}`) })
}

export function useCalendar(month) {
  return useQuery({
    queryKey: gameKeys.calendar(month),
    queryFn: () => api(`/calendar${month ? `?month=${month}` : ''}`),
    placeholderData: (previous) => previous,
  })
}

/**
 * Ações sobre um jogo. Toda rota devolve o jogo atualizado, que substitui o
 * cache na hora. `optimistic(game)` permite mudar a tela antes da resposta.
 *
 * Uso: action.mutate({ path: '/players/3/confirm', success: 'Confirmado' })
 */
export function useGameAction(gameId) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const keys = [gameKeys.detail(gameId), gameKeys.current]

  return useMutation({
    mutationFn: ({ path, method = 'POST', body }) =>
      api(`/games/${gameId}${path}`, { method, body }),
    onMutate: async ({ optimistic }) => {
      if (!optimistic) return {}
      await Promise.all(keys.map((queryKey) => queryClient.cancelQueries({ queryKey })))
      const previous = keys.map((key) => [key, queryClient.getQueryData(key)])
      for (const [key, data] of previous) {
        if (data?.id === Number(gameId)) queryClient.setQueryData(key, optimistic(data))
      }
      return { previous }
    },
    onError: (error, _vars, context) => {
      for (const [key, data] of context?.previous ?? []) queryClient.setQueryData(key, data)
      toast(error.message, 'error')
    },
    onSuccess: (game, { success }) => {
      queryClient.setQueryData(gameKeys.detail(game.id), game)
      const current = queryClient.getQueryData(gameKeys.current)
      if (current?.id === game.id) queryClient.setQueryData(gameKeys.current, game)
      queryClient.invalidateQueries({ queryKey: ['games', 'calendar'] })
      if (success) toast(success)
    },
  })
}

export function useCreateGame() {
  const queryClient = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: (date) => api('/games', { method: 'POST', body: { date } }),
    onSuccess: () => {
      toast('Jogo criado e lista aberta')
      queryClient.invalidateQueries({ queryKey: gameKeys.all })
    },
    onError: (error) => toast(error.message, 'error'),
  })
}

/** Muda o status de um jogador na cópia local (atualização otimista). */
export function withStatus(game, playerId, status) {
  const patch = (list) => list.map((a) => (a.player_id === playerId ? { ...a, status } : a))
  return {
    ...game,
    lineup: { goalkeeper: patch(game.lineup.goalkeeper), field: patch(game.lineup.field) },
  }
}
