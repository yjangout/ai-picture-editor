import { KIND_LABELS } from '@/api/credits'
import { useCreditCatalog, useCreditLedger, useRecharge } from '@/hooks/useCredits'
import { formatDateTime } from '@/lib/format'

export default function CreditsPage() {
  const catalog = useCreditCatalog()
  const ledger = useCreditLedger()
  const recharge = useRecharge()
  const balance = catalog.data?.balance ?? 0

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <h1 className="text-ink text-2xl font-semibold tracking-tight">积分</h1>
      <p className="text-muted mt-1 text-sm">生成与 AI 修图会消耗积分，失败会退回。充值为模拟结算，即时到账。</p>

      <section className="border-line bg-paper shadow-panel rounded-panel mt-6 border p-6">
        <p className="text-muted text-sm">当前余额</p>
        <p className="text-ink mt-1 text-4xl font-semibold tabular-nums">{balance}</p>
        <dl className="text-faint mt-4 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
          <div>文生图 {catalog.data?.costs.generate ?? '—'} / 张</div>
          <div>AI 编辑 {catalog.data?.costs.edit ?? '—'} / 张</div>
          <div>超分 {catalog.data?.costs.upscale ?? '—'} / 次</div>
          <div>营销图 {catalog.data?.costs.marketing ?? '—'} / 张</div>
        </dl>
      </section>

      <section className="mt-8">
        <h2 className="text-ink text-sm font-medium">充值套餐</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          {(catalog.data?.packs ?? []).map((pack) => (
            <button
              key={pack.id}
              type="button"
              disabled={recharge.isPending}
              onClick={() => recharge.mutate(pack.id)}
              className="border-line bg-paper hover:border-brand rounded-card border p-4 text-left transition-colors disabled:opacity-50"
            >
              <p className="text-muted text-xs">{pack.label}</p>
              <p className="text-ink mt-1 text-2xl font-semibold tabular-nums">{pack.credits}</p>
              <p className="text-faint mt-2 text-xs">模拟结算 · 即时到账</p>
            </button>
          ))}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-ink text-sm font-medium">近期明细</h2>
        {ledger.isPending ? (
          <p className="text-faint mt-3 text-sm">加载中…</p>
        ) : !ledger.data?.length ? (
          <p className="text-faint mt-3 text-sm">还没有流水。</p>
        ) : (
          <ul className="border-line bg-paper rounded-card mt-3 divide-y border">
            {ledger.data.map((entry) => (
              <li key={entry.id} className="flex items-center justify-between gap-4 px-4 py-3">
                <div>
                  <p className="text-ink text-sm">{entry.reason}</p>
                  <p className="text-faint mt-0.5 text-xs">
                    {KIND_LABELS[entry.kind]} · {formatDateTime(entry.created_at)}
                  </p>
                </div>
                <span
                  className={`text-sm font-medium tabular-nums ${
                    entry.amount > 0 ? 'text-success' : 'text-ink'
                  }`}
                >
                  {entry.amount > 0 ? `+${entry.amount}` : entry.amount}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
