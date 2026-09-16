import { Link, useNavigate } from 'react-router-dom'

import AssetLibrary from '@/components/AssetLibrary'
import GenerateForm from '@/components/GenerateForm'
import ImageDropzone from '@/components/ImageDropzone'
import { ApiError } from '@/api/client'
import { errorMessage } from '@/hooks/useAuth'
import { useAssetLibrary, useUploadAsset } from '@/hooks/useAssets'
import { useCreditCatalog } from '@/hooks/useCredits'
import { useGenerate } from '@/hooks/useRun'
import { useCreateSession } from '@/hooks/useSessions'
import { readPromptDraft, savePromptDraft } from '@/lib/promptDraft'

export default function CreatePage() {
  const navigate = useNavigate()
  const { data: groups = [], isPending } = useAssetLibrary()
  const upload = useUploadAsset()
  const generate = useGenerate()
  const createSession = useCreateSession()
  const catalog = useCreditCatalog()

  const openEditor = (assetId: string) =>
    createSession.mutate(
      { current_asset_id: assetId },
      { onSuccess: (session) => navigate(`/editor/${session.id}`) },
    )

  return (
    <div className="mx-auto max-w-4xl px-8 py-10">
      <h1 className="text-ink mb-6 text-2xl font-semibold tracking-tight">创作</h1>

      <GenerateForm
        defaultPrompt={readPromptDraft()}
        pending={generate.isPending}
        costPerImage={catalog.data?.costs.generate}
        onSubmit={(input) =>
          generate.mutate(input, {
            onSuccess: (run) => {
              savePromptDraft('')
              navigate(`/candidates/${run.id}`)
            },
          })
        }
      />
      {generate.isError && (
        <p className="text-danger mt-2 text-sm">
          {errorMessage(generate.error)}
          {generate.error instanceof ApiError && generate.error.status === 402 && (
            <>
              {' '}
              <Link to="/credits" className="text-brand-strong underline-offset-2 hover:underline">
                去充值
              </Link>
            </>
          )}
        </p>
      )}

      <section className="mt-10">
        <h2 className="text-muted mb-3 text-sm font-medium">上传已有图片</h2>
        <ImageDropzone
          onFile={(file) => upload.mutate(file, { onSuccess: (asset) => openEditor(asset.id) })}
          disabled={upload.isPending || createSession.isPending}
        />
        {upload.isError && (
          <p className="text-danger mt-2 text-sm">{errorMessage(upload.error)}</p>
        )}
      </section>

      <section className="mt-10">
        <h2 className="text-muted mb-3 text-sm font-medium">历史素材</h2>

        {isPending ? (
          <p className="text-faint text-sm">加载中…</p>
        ) : groups.length === 0 ? (
          <p className="text-faint text-sm">还没有素材，先描述画面或上传一张图片。</p>
        ) : (
          <AssetLibrary
            groups={groups}
            onOpenSession={(sessionId) => navigate(`/editor/${sessionId}`)}
            onOpenAsset={openEditor}
          />
        )}
      </section>
    </div>
  )
}
