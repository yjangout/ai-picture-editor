import { api } from '@/api/client'

export type CreditKind = 'signup' | 'recharge' | 'gift' | 'consume' | 'refund'
export type PackId = 'starter' | 'standard' | 'pro'

export type CreditCosts = {
  generate: number
  edit: number
  upscale: number
  marketing: number
}

export type CreditPack = { id: PackId; label: string; credits: number }

export type CreditCatalog = {
  balance: number
  costs: CreditCosts
  packs: CreditPack[]
}

export type LedgerEntry = {
  id: string
  amount: number
  balance_after: number
  kind: CreditKind
  reason: string
  created_at: string
}

export const KIND_LABELS: Record<CreditKind, string> = {
  signup: '注册赠送',
  recharge: '充值',
  gift: '管理员赠送',
  consume: '消耗',
  refund: '退回',
}

export const creditsApi = {
  catalog: () => api.get<CreditCatalog>('/credits/catalog'),
  ledger: () => api.get<LedgerEntry[]>('/credits/ledger'),
  recharge: (pack_id: PackId) => api.post<CreditCatalog>('/credits/recharge', { pack_id }),
}
