import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { Copy, FolderGit2, MoreHorizontal, Share2 } from 'lucide-react'

import type { DocumentSummary } from '../lib/types'
import { cn, relativeTime } from '../lib/utils'

type Props = {
  document: DocumentSummary
  onOpen: (document: DocumentSummary) => void
  onDuplicate: (document: DocumentSummary) => void
  onShare: (document: DocumentSummary) => void
  onCompare: (document: DocumentSummary) => void
}

export function DocumentCard({ document, onOpen, onDuplicate, onShare, onCompare }: Props) {
  return (
    <article className="group rounded-[28px] border border-white/60 bg-white/80 p-5 shadow-[0_20px_60px_rgba(99,85,63,0.12)] backdrop-blur">
      <div className="mb-4 flex items-start justify-between gap-4">
        <button
          className="text-left"
          onClick={() => onOpen(document)}
          type="button"
        >
          <p className="text-xs uppercase tracking-[0.24em] text-stone-500">{document.workspace.name}</p>
          <h3 className="mt-2 font-display text-2xl text-stone-950">{document.title}</h3>
          <p className="mt-2 text-sm text-stone-500">{document.file_name}</p>
        </button>
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button className="rounded-full border border-stone-200 bg-stone-50 p-2 text-stone-500 transition hover:border-stone-300 hover:text-stone-800">
              <MoreHorizontal className="h-4 w-4" />
            </button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Portal>
            <DropdownMenu.Content className="z-50 min-w-44 rounded-2xl border border-stone-200 bg-white p-2 shadow-xl" sideOffset={8}>
              <DropdownMenu.Item className="menu-item" onSelect={() => onDuplicate(document)}>
                <Copy className="h-4 w-4" />
                Duplicate
              </DropdownMenu.Item>
              <DropdownMenu.Item className="menu-item" onSelect={() => onShare(document)}>
                <Share2 className="h-4 w-4" />
                Share
              </DropdownMenu.Item>
              <DropdownMenu.Item className="menu-item" onSelect={() => onCompare(document)}>
                <FolderGit2 className="h-4 w-4" />
                Compare
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>

      <div className="rounded-[22px] border border-stone-200/80 bg-[linear-gradient(135deg,rgba(248,245,236,0.9),rgba(241,236,226,0.75))] p-4">
        <div className="mb-3 flex items-center justify-between text-sm text-stone-600">
          <span className={cn('rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em]', roleClass(document.current_role))}>
            {document.current_role}
          </span>
          <span>{relativeTime(document.updated_at)}</span>
        </div>
        <div className="flex items-center justify-between text-sm text-stone-600">
          <span>{document.kind === 'comparison' ? 'Comparison draft' : 'Workspace document'}</span>
          <span>v{document.latest_version_number}</span>
        </div>
      </div>
    </article>
  )
}

function roleClass(role: DocumentSummary['current_role']) {
  switch (role) {
    case 'owner':
      return 'bg-amber-100 text-amber-800'
    case 'editor':
      return 'bg-emerald-100 text-emerald-800'
    case 'reviewer':
      return 'bg-sky-100 text-sky-800'
    case 'commenter':
      return 'bg-rose-100 text-rose-800'
    default:
      return 'bg-stone-200 text-stone-700'
  }
}
