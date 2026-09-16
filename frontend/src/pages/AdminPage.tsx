import { useState } from 'react'

import type { AdminUser } from '@/api/admin'
import { KIND_LABELS } from '@/api/credits'
import { useAdminLedger, useAdminUsers, useGiftCredits, useSetRole } from '@/hooks/useAdmin'
import { useCurrentUser } from '@/hooks/useAuth'
import { formatDateTime } from '@/lib/format'

export default function AdminPage() {
  const { user: me } = useCurrentUser()
  const [query, setQuery] = useState('')
  const [draft, setDraft] = useState('')
  const users = useAdminUsers(query)
  const ledger = useAdminLedger()
  const gift = useGiftCredits()
  const setRole = useSetRole()
  const [target, setTarget] = useState<AdminUser | null>(null)
  const [amount, setAmount] = useState('100')
  const [reason, setReason] = useState('管理员赠送')

  const submitGift = () => {
    if (!target) return
    const value = Number(amount)
    if (!Number.isInteger(value) || value <= 0) return
    gift.mutate(
      { id: target.id, amount: value, reason },
      { onSuccess: () => setTarget(null) },
    )
  }

  return (
    <div className="mx-auto max-w-5xl px-8 py-10">
      <h1 className="text-ink text-2xl font-semibold tracking-tight">管理平台</h1>
      <p className="text-muted mt-1 text-sm">查看用户、赠送积分。充值由用户在积分页自助完成（模拟结算）。</p>

      <dl className="mt-6 grid grid-cols-3 gap-3">
        <Stat label="用户" value={users.data?.total} />
        <Stat label="管理员" value={users.data?.admin_count} />
        <Stat label="流通积分" value={users.data?.credits_total} />
      </dl>

      <form
        className="mt-8"
        onSubmit={(event) => {
          event.preventDefault()
          setQuery(draft.trim())
        }}
      >
        <label className="block">
          <span className="text-muted mb-1.5 block text-sm">搜索用户名</span>
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="输入后回车"
            className="border-line bg-paper text-ink placeholder:text-faint focus:border-brand rounded-control w-full max-w-sm border px-3.5 py-2.5 text-sm outline-none"
          />
        </label>
      </form>

      <div className="border-line bg-paper rounded-card mt-4 overflow-x-auto border">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="text-muted bg-soft">
            <tr>
              <th className="px-4 py-2.5 font-medium">用户</th>
              <th className="px-4 py-2.5 font-medium">角色</th>
              <th className="px-4 py-2.5 font-medium">积分</th>
              <th className="px-4 py-2.5 font-medium">注册</th>
              <th className="px-4 py-2.5 font-medium">操作</th>
            </tr>
          </thead>
          <tbody className="divide-line divide-y">
            {(users.data?.items ?? []).map((item) => (
              <tr key={item.id}>
                <td className="text-ink px-4 py-3 font-medium">{item.username}</td>
                <td className="text-muted px-4 py-3">{item.role === 'admin' ? '管理员' : '用户'}</td>
                <td className="text-ink px-4 py-3 tabular-nums">{item.credits}</td>
                <td className="text-faint px-4 py-3">{formatDateTime(item.created_at)}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setTarget(item)
                        setAmount('100')
                        setReason('管理员赠送')
                      }}
                      className="text-brand-strong hover:text-ink text-xs font-medium"
                    >
                      赠送
                    </button>
                    {item.id !== me?.id && (
                      <button
                        type="button"
                        disabled={setRole.isPending}
                        onClick={() =>
                          setRole.mutate({
                            id: item.id,
                            role: item.role === 'admin' ? 'user' : 'admin',
                          })
                        }
                        className="text-muted hover:text-ink text-xs font-medium"
                      >
                        {item.role === 'admin' ? '取消管理' : '设为管理'}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {users.isPending && <p className="text-faint px-4 py-6 text-sm">加载中…</p>}
        {users.data && users.data.items.length === 0 && (
          <p className="text-faint px-4 py-6 text-sm">没有匹配的用户。</p>
        )}
      </div>

      <section className="mt-10">
        <h2 className="text-ink text-sm font-medium">最近流水</h2>
        <ul className="border-line bg-paper rounded-card mt-3 divide-y border">
          {(ledger.data?.items ?? []).slice(0, 20).map((entry) => (
            <li key={entry.id} className="flex items-center justify-between gap-4 px-4 py-3 text-sm">
              <span className="text-ink">
                {KIND_LABELS[entry.kind]} · {entry.reason}
              </span>
              <span className={`tabular-nums ${entry.amount > 0 ? 'text-success' : 'text-ink'}`}>
                {entry.amount > 0 ? `+${entry.amount}` : entry.amount}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {target && (
        <div className="fixed inset-0 z-40 grid place-items-center bg-black/30 px-4">
          <div className="border-line bg-paper rounded-panel shadow-panel w-full max-w-sm border p-6">
            <h3 className="text-ink text-lg font-semibold">赠送积分</h3>
            <p className="text-muted mt-1 text-sm">
              给 {target.username}（当前 {target.credits}）
            </p>
            <label className="mt-4 block">
              <span className="text-muted mb-1.5 block text-sm">数量</span>
              <input
                type="number"
                min={1}
                max={10000}
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                className="border-line rounded-control w-full border px-3 py-2 text-sm outline-none"
              />
            </label>
            <label className="mt-3 block">
              <span className="text-muted mb-1.5 block text-sm">原因</span>
              <input
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                className="border-line rounded-control w-full border px-3 py-2 text-sm outline-none"
              />
            </label>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setTarget(null)} className="text-muted px-3 py-2 text-sm">
                取消
              </button>
              <button
                type="button"
                disabled={gift.isPending}
                onClick={submitGift}
                className="bg-ink hover:bg-dark rounded-control px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                {gift.isPending ? '处理中…' : '确认赠送'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number | undefined }) {
  return (
    <div className="border-line bg-paper rounded-card border px-4 py-3">
      <dt className="text-muted text-xs">{label}</dt>
      <dd className="text-ink mt-1 text-xl font-semibold tabular-nums">{value ?? '—'}</dd>
    </div>
  )
}
