import { QueryClient } from '@tanstack/react-query'

import { ApiError } from './api.js'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // Não insiste em erros de autenticação/validação; só em falhas de rede/servidor
      retry: (failureCount, error) =>
        !(error instanceof ApiError && error.status < 500) && failureCount < 2,
    },
  },
})
