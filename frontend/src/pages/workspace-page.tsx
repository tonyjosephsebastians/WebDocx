import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { CloudUpload, FilePlus2, Files, FolderGit2, LogOut, RefreshCcw, Share2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'

import { CompareDialog } from '../components/compare-dialog'
import { DocumentCard } from '../components/document-card'
import { ShareDialog } from '../components/share-dialog'
import { api } from '../lib/api'
import { useSession } from '../lib/session'
import type { DocumentSummary } from '../lib/types'

export function WorkspacePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const session = useSession()
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [title, setTitle] = useState('')
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [selectedDocument, setSelectedDocument] = useState<DocumentSummary | null>(null)
  const [shareOpen, setShareOpen] = useState(false)
  const [compareOpen, setCompareOpen] = useState(false)

  useEffect(() => {
    if (session.ready && !session.token) {
      void navigate({ to: '/login' })
    }
  }, [navigate, session.ready, session.token])

  const documentsQuery = useQuery({
    enabled: !!session.token,
    queryKey: ['documents', session.token],
    queryFn: () => api.listDocuments(session.token!),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      api.createDocument(session.token!, {
        title: title || pendingFile?.name.replace(/\.docx$/i, '') || 'Untitled Document',
        workspaceId: session.user?.workspaces[0]?.id,
        file: pendingFile,
      }),
    onSuccess: ({ document }) => {
      toast.success('Document ready.')
      setTitle('')
      setPendingFile(null)
      void queryClient.invalidateQueries({ queryKey: ['documents'] })
      void navigate({ to: '/documents/$documentId', params: { documentId: document.id } })
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Unable to create the document.'),
  })

  const duplicateMutation = useMutation({
    mutationFn: (document: DocumentSummary) => api.duplicateDocument(session.token!, document.id),
    onSuccess: () => {
      toast.success('Document duplicated.')
      void queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Unable to duplicate the document.'),
  })

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,#f7dcb5,transparent_22%),radial-gradient(circle_at_70%_20%,#c2e6dd,transparent_22%),linear-gradient(180deg,#faf6ef_0%,#ede2d5_100%)] px-5 py-5 lg:px-8">
      <ShareDialog
        document={selectedDocument}
        onOpenChange={setShareOpen}
        onSubmit={async (payload) => {
          if (!selectedDocument) return
          await api.shareDocument(session.token!, selectedDocument.id, payload)
          toast.success('Sharing updated.')
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['documents'] }),
            queryClient.invalidateQueries({ queryKey: ['document', selectedDocument.id] }),
          ])
        }}
        open={shareOpen}
      />

      <CompareDialog
        currentDocument={selectedDocument}
        documents={documentsQuery.data ?? []}
        onOpenChange={setCompareOpen}
        onSubmit={async (revisedDocumentId) => {
          if (!selectedDocument) return
          const response = await api.compareDocument(session.token!, selectedDocument.id, revisedDocumentId)
          toast.success('Comparison draft created.')
          await queryClient.invalidateQueries({ queryKey: ['documents'] })
          await navigate({ to: '/documents/$documentId', params: { documentId: response.document.id } })
        }}
        open={compareOpen}
      />

      <div className="grid gap-5 lg:grid-cols-[18rem_minmax(0,1fr)]">
        <aside className="rounded-[34px] border border-white/70 bg-[linear-gradient(180deg,rgba(37,28,18,0.96),rgba(73,53,29,0.93))] p-6 text-white shadow-[0_40px_120px_rgba(45,28,12,0.25)]">
          <p className="text-xs uppercase tracking-[0.22em] text-white/60">Word workspace</p>
          <h1 className="mt-3 font-display text-4xl">Library</h1>
          <p className="mt-3 text-sm leading-6 text-white/75">
            Keep the editing engine inside ONLYOFFICE and shape the collaboration experience around it.
          </p>

          <div className="mt-8 rounded-[28px] border border-white/10 bg-white/5 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-white/55">Workspace</p>
            <p className="mt-2 text-xl font-semibold">{session.user?.workspaces[0]?.name ?? 'Workspace'}</p>
          </div>

          <div className="mt-4 grid gap-3">
            <button className="button-primary w-full justify-center" onClick={() => setPendingFile(null)} type="button">
              <FilePlus2 className="h-4 w-4" />
              Blank DOCX
            </button>
            <button className="button-secondary w-full justify-center" onClick={() => fileInputRef.current?.click()} type="button">
              <CloudUpload className="h-4 w-4" />
              Upload DOCX
            </button>
            <button
              className="button-ghost w-full justify-center text-white/80 hover:text-white"
              onClick={() => {
                session.logout()
                void navigate({ to: '/login' })
              }}
              type="button"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>

          <input
            accept=".docx"
            className="hidden"
            onChange={(event) => setPendingFile(event.target.files?.[0] ?? null)}
            ref={fileInputRef}
            type="file"
          />
        </aside>

        <section className="rounded-[34px] border border-white/70 bg-white/70 p-6 shadow-[0_40px_120px_rgba(45,28,12,0.16)] backdrop-blur">
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_19rem]">
            <div>
              <div className="rounded-[32px] border border-stone-200 bg-[linear-gradient(145deg,rgba(252,248,240,0.95),rgba(245,239,230,0.84))] p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em] text-stone-500">Authoring floor</p>
                    <h2 className="mt-3 font-display text-4xl text-stone-950">A better shell for Word-like work.</h2>
                  </div>
                  <button className="button-secondary" onClick={() => void documentsQuery.refetch()} type="button">
                    <RefreshCcw className="h-4 w-4" />
                    Refresh
                  </button>
                </div>

                <div className="mt-6 grid gap-4 md:grid-cols-[minmax(0,1fr)_auto]">
                  <input
                    className="input"
                    onChange={(event) => setTitle(event.target.value)}
                    placeholder={pendingFile ? `Upload title for ${pendingFile.name}` : 'Name your next blank document'}
                    value={title}
                  />
                  <button
                    className="button-primary"
                    disabled={createMutation.isPending}
                    onClick={() => createMutation.mutate()}
                    type="button"
                  >
                    {pendingFile ? <CloudUpload className="h-4 w-4" /> : <Files className="h-4 w-4" />}
                    {createMutation.isPending ? 'Creating...' : pendingFile ? 'Upload and open' : 'Create and open'}
                  </button>
                </div>
              </div>

              <div className="mt-6 grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
                {(documentsQuery.data ?? []).map((document) => (
                  <DocumentCard
                    document={document}
                    key={document.id}
                    onCompare={(item) => {
                      setSelectedDocument(item)
                      setCompareOpen(true)
                    }}
                    onDuplicate={(item) => duplicateMutation.mutate(item)}
                    onOpen={(item) => void navigate({ to: '/documents/$documentId', params: { documentId: item.id } })}
                    onShare={(item) => {
                      setSelectedDocument(item)
                      setShareOpen(true)
                    }}
                  />
                ))}
              </div>
            </div>

            <aside className="rounded-[30px] border border-stone-200 bg-stone-950 p-5 text-white">
              <p className="text-xs uppercase tracking-[0.22em] text-white/50">Workflow</p>
              <div className="mt-5 space-y-4">
                {[
                  ['Upload', 'Bring DOCX files in as-is and open them directly in ONLYOFFICE.'],
                  ['Compare', 'Spawn third-document comparison drafts so source files stay intact.'],
                  ['Redline', 'Use reviewer/commenter roles and built-in track changes.'],
                ].map(([heading, body]) => (
                  <div className="rounded-[24px] border border-white/10 bg-white/5 p-4" key={heading}>
                    <p className="font-semibold">{heading}</p>
                    <p className="mt-2 text-sm leading-6 text-white/70">{body}</p>
                  </div>
                ))}
              </div>

              <div className="mt-6 flex items-center gap-2 text-sm text-white/70">
                <Share2 className="h-4 w-4 text-amber-300" />
                Sharing is invite-only for existing app users.
              </div>
              <div className="mt-3 flex items-center gap-2 text-sm text-white/70">
                <FolderGit2 className="h-4 w-4 text-emerald-300" />
                Comparison drafts keep original and revised source files untouched.
              </div>
            </aside>
          </div>
        </section>
      </div>
    </main>
  )
}
