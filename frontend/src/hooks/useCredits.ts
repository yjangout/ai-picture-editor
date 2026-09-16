import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { creditsApi, type PackId } from '@/api/credits'
import { errorMessage, refreshWallet } from '@/hooks/useAuth'
import { toast } from '@/stores/toasts'

const CATALOG_KEY = ['credits', 'catalog'] as const
const LEDGER_KEY = ['credits', 'ledger'] as const

export function useCreditCatalog() {
  return useQuery({
    queryKey: CATALOG_KEY,
    queryFn: creditsApi.catalog,
    staleTime: 30_000,
  })
}

export function useCreditLedger() {
  return useQuery({ queryKey: LEDGER_KEY, queryFn: creditsApi.ledger })
}

export function useRecharge() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (packId: PackId) => creditsApi.recharge(packId),
    onSuccess: (catalog) => {
      queryClient.setQueryData(CATALOG_KEY, catalog)
      void queryClient.invalidateQueries({ queryKey: LEDGER_KEY })
      refreshWallet(queryClient)
      toast(`充值成功，当前余额 ${catalog.balance}`, 'ok')
    },
    onError: (error) => toast(errorMessage(error), 'danger'),
  })
}
