import * as Avatar from '@radix-ui/react-avatar'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from '@tanstack/react-router'
import { ArrowLeft, FolderGit2, Save, Share2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'

import { CompareDialog } from '../components/compare-dialog'
import { HistoryDrawer } from '../components/history-drawer'
import { OnlyOfficeEditor, type OnlyOfficeHandle } from '../components/onlyoffice-editor'
import { ShareDialog } from '../components/share-dialog'
import { api } from '../lib/api'
import { useSession } from '../lib/session'
import type { DocumentSummary, VersionEntry } from '../lib/types'
import { relativeTime } from '../lib/utils'

export function EditorPage() {
  const { documentId } = useParams({ from: '/documents/$documentId' })
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const session = useSession()
  const editorRef = useRef<OnlyOfficeHandle | null>(null)
  const [shareOpen, setShareOpen] = useState(false)
  const [compareOpen, setCompareOpen] = useState(false)

  useEffect(() => {
    if (session.ready && !session.token) {
      void navigate({ to: '/login' })
    }
  }, [navigate, session.ready, session.token])

  const documentQuery = useQuery({
    enabled: !!session.token,
    queryKey: ['document', documentId],
    queryFn: () => api.getDocument(session.token!, documentId),
  })

  const documentsQuery = useQuery({
    enabled: !!session.token,
    queryKey: ['documents', session.token],
    queryFn: () => api.listDocuments(session.token!),
  })

  const editorConfigQuery = useQuery({
    enabled: !!session.token,
    queryKey: ['editor-config', documentId],
    queryFn: () => api.getEditorConfig(session.token!, documentId, 'edit'),
  })

  const refreshDocument = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['document', documentId] }),
      queryClient.invalidateQueries({ queryKey: ['documents'] }),
      queryClient.invalidateQueries({ queryKey: ['editor-config', documentId] }),
    ])
  }

  const restoreMutation = useMutation({
    mutationFn: (version: VersionEntry) => api.restoreVersion(session.token!, documentId, version.version_number),
    onSuccess: async () => {
      toast.success('Document restored.')
      await refreshDocument()
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Unable to restore version.'),
  })

  const forceSaveMutation = useMutation({
    mutationFn: () => api.forceSave(session.token!, documentId),
    onSuccess: () => {
      toast.success('Checkpoint requested from ONLYOFFICE.')
      void refreshDocument()
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Unable to request a checkpoint.'),
  })

  const currentDocument = documentQuery.data

  if (!currentDocument || !editorConfigQuery.data || !session.token) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,#faf6ef_0%,#ede2d5_100%)]">
        <div className="rounded-full border border-stone-200 bg-white px-5 py-3 text-sm font-semibold text-stone-700">
          Loading document workspace...
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,#f7dcb5,transparent_22%),radial-gradient(circle_at_70%_20%,#c2e6dd,transparent_22%),linear-gradient(180deg,#faf6ef_0%,#ede2d5_100%)] px-5 py-5 lg:px-8">
      <ShareDialog
        document={currentDocument}
        onOpenChange={setShareOpen}
        onSubmit={async (payload) => {
          await api.shareDocument(session.token!, currentDocument.id, payload)
          toast.success('Sharing updated.')
          await refreshDocument()
        }}
        open={shareOpen}
      />

      <CompareDialog
        currentDocument={currentDocument}
        documents={(documentsQuery.data ?? []) as DocumentSummary[]}
        onOpenChange={setCompareOpen}
        onSubmit={async (revisedDocumentId) => {
          const response = await api.compareDocument(session.token!, currentDocument.id, revisedDocumentId)
          toast.success('Comparison draft ready.')
          await refreshDocument()
          await navigate({ to: '/documents/$documentId', params: { documentId: response.document.id } })
        }}
        open={compareOpen}
      />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <section className="rounded-[34px] border border-white/70 bg-white/72 p-6 shadow-[0_40px_120px_rgba(45,28,12,0.16)] backdrop-blur">
          <div className="rounded-[30px] border border-stone-200 bg-[linear-gradient(145deg,rgba(253,249,242,0.96),rgba(245,239,230,0.88))] p-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-3 text-sm text-stone-600">
                  <Link className="inline-flex items-center gap-2 text-stone-700 transition hover:text-stone-950" to="/">
                    <ArrowLeft className="h-4 w-4" />
                    Back to library
                  </Link>
                  <span className="text-stone-300">/</span>
                  <span>{currentDocument.workspace.name}</span>
                </div>
                <h1 className="mt-3 font-display text-4xl text-stone-950">{currentDocument.title}</h1>
                <p className="mt-2 text-sm text-stone-500">
                  Last updated {relativeTime(currentDocument.updated_at)} • role {currentDocument.current_role}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <CollaboratorStrip documentId={currentDocument.id} grants={currentDocument.share_grants} owner={currentDocument.created_by} />
                <button className="button-secondary" onClick={() => setShareOpen(true)} type="button">
                  <Share2 className="h-4 w-4" />
                  Share
                </button>
                <button className="button-secondary" onClick={() => setCompareOpen(true)} type="button">
                  <FolderGit2 className="h-4 w-4" />
                  Compare
                </button>
                <button className="button-primary" disabled={forceSaveMutation.isPending} onClick={() => forceSaveMutation.mutate()} type="button">
                  <Save className="h-4 w-4" />
                  {forceSaveMutation.isPending ? 'Saving...' : 'Checkpoint'}
                </button>
              </div>
            </div>

            {currentDocument.comparison ? (
              <div className="mt-5 rounded-[24px] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                This is a comparison draft. Use the outer “Apply compare” button if you want the revised document injected into the editor immediately.
              </div>
            ) : null}

            <div className="mt-5 flex items-center justify-between gap-4">
              <p className="text-sm text-stone-600">
                The enhanced UI lives outside the editor. Formatting, redlines, comments, and co-editing stay native to ONLYOFFICE.
              </p>
              {editorConfigQuery.data.compare_descriptor ? (
                <button className="button-secondary" onClick={() => editorRef.current?.applyCompare()} type="button">
                  <FolderGit2 className="h-4 w-4" />
                  Apply compare
                </button>
              ) : null}
            </div>
          </div>

          <div className="mt-5">
            <OnlyOfficeEditor
              compareDescriptor={editorConfigQuery.data.compare_descriptor}
              config={editorConfigQuery.data.config}
              documentId={documentId}
              documentServerUrl={editorConfigQuery.data.document_server_url}
              onRestored={refreshDocument}
              ref={editorRef}
              token={session.token}
            />
          </div>
        </section>

        <HistoryDrawer
          document={currentDocument}
          onRestoreVersion={async (version) => {
            await restoreMutation.mutateAsync(version)
          }}
        />
      </div>
    </main>
  )
}

function CollaboratorStrip({
  grants,
  owner,
  documentId,
}: {
  grants: { shared_with_user: { id: string; name: string } }[]
  owner: { id: string; name: string }
  documentId: string
}) {
  const people = [owner, ...grants.map((grant) => grant.shared_with_user)]

  return (
    <div className="flex items-center gap-2">
      {people.slice(0, 4).map((person) => (
        <Avatar.Root
          className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full border border-white bg-stone-200 text-xs font-bold uppercase tracking-[0.18em] text-stone-700"
          key={`${documentId}-${person.id}`}
        >
          <Avatar.Fallback>
            {person.name
              .split(' ')
              .map((part) => part[0])
              .join('')
              .slice(0, 2)}
          </Avatar.Fallback>
        </Avatar.Root>
      ))}
    </div>
  )
}
