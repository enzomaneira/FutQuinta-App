import { useQuery } from '@tanstack/react-query'

import { api } from '../lib/api.js'

export const useHome = () => useQuery({ queryKey: ['home'], queryFn: () => api('/home') })

export const usePlayerProfile = (id) =>
  useQuery({ queryKey: ['players', 'profile', Number(id)], queryFn: () => api(`/players/${id}/profile`) })

export const useGameHistory = () =>
  useQuery({ queryKey: ['games', 'history'], queryFn: () => api('/games/history') })

export const useGameCharges = (id) =>
  useQuery({ queryKey: ['games', 'charges', Number(id)], queryFn: () => api(`/games/${id}/charges`) })
