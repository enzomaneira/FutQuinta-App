import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useToast } from '../components/Toast.jsx'
import { api } from '../lib/api.js'

export const financeKeys = {
  all: ['finance'],
  cash: ['finance', 'cash'],
  fees: (month) => ['finance', 'fees', month],
  dropIns: (month) => ['finance', 'drop-ins', month],
  expenses: (month) => ['finance', 'expenses', month],
  statement: (month) => ['finance', 'statement', month],
  open: ['finance', 'open'],
}

const keep = { placeholderData: (previous) => previous }

export const useCash = () => useQuery({ queryKey: financeKeys.cash, queryFn: () => api('/finance/cash') })

export const useMonthlyFees = (month) =>
  useQuery({ queryKey: financeKeys.fees(month), queryFn: () => api(`/finance/monthly-fees?month=${month}`), ...keep })

export const useDropInCharges = (month) =>
  useQuery({ queryKey: financeKeys.dropIns(month), queryFn: () => api(`/finance/drop-ins?month=${month}`), ...keep })

export const useExpenses = (month) =>
  useQuery({ queryKey: financeKeys.expenses(month), queryFn: () => api(`/expenses?month=${month}`), ...keep })

export const useStatement = (month) =>
  useQuery({ queryKey: financeKeys.statement(month), queryFn: () => api(`/finance/statement?month=${month}`), ...keep })

function useInvalidateFinance() {
  const queryClient = useQueryClient()
  return () => {
    queryClient.invalidateQueries({ queryKey: financeKeys.all })
    queryClient.invalidateQueries({ queryKey: ['players'] }) // situação de pagamento
    queryClient.invalidateQueries({ queryKey: ['home'] })
    queryClient.invalidateQueries({ queryKey: ['games', 'charges'] })
  }
}

const OPTIMISTIC_STATUS = { pay: 'paid', 'undo-payment': 'pending', waive: 'waived', unwaive: 'pending' }

/**
 * Ações numa cobrança (pagar, desfazer, isentar). Atualização otimista: a
 * linha muda na hora em todas as listas do financeiro; volta se der erro.
 * Uso: action.mutate({ id, action: 'pay', body: { method: 'pix' }, success })
 */
export function useChargeAction() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const invalidate = useInvalidateFinance()
  return useMutation({
    mutationFn: ({ id, action, body }) => api(`/charges/${id}/${action}`, { method: 'POST', body }),
    onMutate: async ({ id, action }) => {
      await queryClient.cancelQueries({ queryKey: financeKeys.all })
      const snapshot = queryClient.getQueriesData({ queryKey: financeKeys.all })
      queryClient.setQueriesData({ queryKey: financeKeys.all }, (data) =>
        Array.isArray(data)
          ? data.map((c) => (c.id === id && 'status' in c ? { ...c, status: OPTIMISTIC_STATUS[action] } : c))
          : data,
      )
      return { snapshot }
    },
    onError: (error, _vars, context) => {
      for (const [key, data] of context?.snapshot ?? []) queryClient.setQueryData(key, data)
      toast(error.message, 'error')
    },
    onSuccess: (_charge, { success }) => success && toast(success),
    onSettled: invalidate,
  })
}

export function useGenerateFees() {
  const toast = useToast()
  const invalidate = useInvalidateFinance()
  return useMutation({
    mutationFn: (month) => api('/finance/monthly-fees/generate', { method: 'POST', body: { month } }),
    onSuccess: ({ created }) => {
      toast(created ? `${created} mensalidade${created > 1 ? 's' : ''} gerada${created > 1 ? 's' : ''}` : 'Nenhuma mensalidade faltando')
      invalidate()
    },
    onError: (error) => toast(error.message, 'error'),
  })
}

export function useCreateExpense() {
  const toast = useToast()
  const invalidate = useInvalidateFinance()
  return useMutation({
    mutationFn: (body) => api('/expenses', { method: 'POST', body }),
    onSuccess: () => {
      toast('Despesa lançada')
      invalidate()
    },
  })
}

export function useDeleteExpense() {
  const toast = useToast()
  const invalidate = useInvalidateFinance()
  return useMutation({
    mutationFn: (id) => api(`/expenses/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      toast('Despesa apagada')
      invalidate()
    },
    onError: (error) => toast(error.message, 'error'),
  })
}
