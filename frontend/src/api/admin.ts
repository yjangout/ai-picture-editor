import { api } from '@/api/client'
import type { LedgerEntry } from '@/api/credits'
import type { Role, User } from '@/api/auth'

export type AdminUser = User & { created_at: string }

export type AdminUserList = {
  items: AdminUser[]
  total: number
  admin_count: number
  credits_total: number
}

export type AdminLedgerList = {
  items: LedgerEntry[]
  total: number
}

export const adminApi = {
  users: (q = '') => api.get<AdminUserList>(`/admin/users${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  user: (id: string) => api.get<AdminUser>(`/admin/users/${id}`),
  gift: (id: string, amount: number, reason: string) =>
    api.post<AdminUser>(`/admin/users/${id}/gift`, { amount, reason }),
  setRole: (id: string, role: Role) => api.patch<AdminUser>(`/admin/users/${id}`, { role }),
  ledger: () => api.get<AdminLedgerList>('/admin/ledger'),
}
