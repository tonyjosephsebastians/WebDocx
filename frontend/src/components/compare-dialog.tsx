import * as Dialog from '@radix-ui/react-dialog'
import { ArrowRightLeft, Search, X } from 'lucide-react'
import { useMemo, useState } from 'react'

import type { DocumentSummary } from '../lib/types'
import { cn } from '../lib/utils'

type Props = {
  currentDocument: DocumentSummary | null
  documents: DocumentSummary[]
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (revisedDocumentId: string) => Promise<void>
}

export function CompareDialog({ currentDocument, documents, open, onOpenChange, onSubmit }: Props) {
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const candidates = useMemo(
    () =>
      documents.filter((document) => {
        if (document.id === currentDocument?.id) {
          return false
        }
        const needle = query.trim().toLowerCase()
        if (!needle) {
          return true
        }
        return `${document.title} ${document.file_name}`.toLowerCase().includes(needle)
      }),
    [currentDocument?.id, documents, query],
  )

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-stone-950/30 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,42rem)] -translate-x-1/2 -translate-y-1/2 rounded-[32px] border border-white/50 bg-[linear-gradient(145deg,rgba(255,253,249,0.98),rgba(244,238,229,0.95))] p-7 shadow-[0_30px_80px_rgba(32,22,12,0.25)]">
          <div className="flex items-start justify-between gap-4">
            <div>
              <Dialog.Title className="font-display text-3xl text-stone-950">Create comparison draft</Dialog.Title>
              <Dialog.Description className="mt-2 text-sm text-stone-600">
                Duplicate {currentDocument?.title ?? 'this document'} and compare it against another workspace file.
              </Dialog.Description>
            </div>
            <Dialog.Close className="rounded-full border border-stone-200 p-2 text-stone-500 transition hover:text-stone-900">
              <X className="h-4 w-4" />
            </Dialog.Close>
          </div>

          <div className="mt-6 flex items-center gap-3 rounded-2xl border border-stone-200 bg-white px-4 py-3">
            <Search className="h-4 w-4 text-stone-400" />
            <input
              className="w-full bg-transparent text-sm text-stone-800 outline-none"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search documents"
              value={query}
            />
          </div>

          <div className="mt-4 max-h-80 space-y-3 overflow-y-auto pr-1">
            {candidates.map((document) => (
              <button
                className={cn(
                  'w-full rounded-[24px] border px-4 py-4 text-left transition',
                  selectedId === document.id
                    ? 'border-stone-900 bg-stone-950 text-white'
                    : 'border-stone-200 bg-white text-stone-900 hover:border-stone-300',
                )}
                key={document.id}
                onClick={() => setSelectedId(document.id)}
                type="button"
              >
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="font-semibold">{document.title}</p>
                    <p className={cn('mt-1 text-sm', selectedId === document.id ? 'text-white/75' : 'text-stone-500')}>
                      {document.file_name}
                    </p>
                  </div>
                  <ArrowRightLeft className={cn('h-4 w-4', selectedId === document.id ? 'text-amber-300' : 'text-stone-400')} />
                </div>
              </button>
            ))}
          </div>

          <button
            className="button-primary mt-6 w-full"
            disabled={!selectedId || submitting}
            onClick={async () => {
              if (!selectedId) {
                return
              }
              setSubmitting(true)
              try {
                await onSubmit(selectedId)
                setSelectedId(null)
                setQuery('')
                onOpenChange(false)
              } finally {
                setSubmitting(false)
              }
            }}
            type="button"
          >
            {submitting ? 'Creating comparison...' : 'Create comparison draft'}
          </button>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
