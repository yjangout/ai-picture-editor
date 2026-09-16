import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { adminApi } from '@/api/admin'
import type { Role } from '@/api/auth'
import { errorMessage, refreshWallet } from '@/hooks/useAuth'
import { toast } from '@/stores/toasts'

const USERS_KEY = ['admin', 'users'] as const
const LEDGER_KEY = ['admin', 'ledger'] as const

export function useAdminUsers(q: string) {
  return useQuery({
    queryKey: [...USERS_KEY, q],
    queryFn: () => adminApi.users(q),
  })
}

export function useAdminLedger() {
  return useQuery({ queryKey: LEDGER_KEY, queryFn: adminApi.ledger })
}

export function useGiftCredits() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, amount, reason }: { id: string; amount: number; reason: string }) =>
      adminApi.gift(id, amount, reason),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: USERS_KEY })
      void queryClient.invalidateQueries({ queryKey: LEDGER_KEY })
      refreshWallet(queryClient)
      toast('已赠送积分', 'ok')
    },
    onError: (error) => toast(errorMessage(error), 'danger'),
  })
}

export function useSetRole() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, role }: { id: string; role: Role }) => adminApi.setRole(id, role),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: USERS_KEY })
      toast('角色已更新', 'ok')
    },
    onError: (error) => toast(errorMessage(error), 'danger'),
  })
}
