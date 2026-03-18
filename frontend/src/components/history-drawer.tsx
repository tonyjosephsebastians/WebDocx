import * as Avatar from '@radix-ui/react-avatar'
import * as ScrollArea from '@radix-ui/react-scroll-area'
import * as Tabs from '@radix-ui/react-tabs'
import { Clock3, History, RefreshCw, Sparkles } from 'lucide-react'

import type { ActivityEntry, DocumentDetail, VersionEntry } from '../lib/types'
import { cn, fullDate, relativeTime } from '../lib/utils'

type Props = {
  document: DocumentDetail
  onRestoreVersion: (version: VersionEntry) => Promise<void>
}

export function HistoryDrawer({ document, onRestoreVersion }: Props) {
  return (
    <aside className="flex h-full min-h-[42rem] flex-col rounded-[32px] border border-white/70 bg-white/70 shadow-[0_30px_90px_rgba(46,31,9,0.15)] backdrop-blur">
      <div className="border-b border-stone-200/80 p-5">
        <p className="text-xs uppercase tracking-[0.2em] text-stone-500">Inspector</p>
        <h2 className="mt-2 font-display text-3xl text-stone-950">Version craft</h2>
      </div>

      <Tabs.Root className="flex min-h-0 flex-1 flex-col" defaultValue="versions">
        <Tabs.List className="grid grid-cols-2 gap-2 px-5 pt-4">
          <Tabs.Trigger className="tab-trigger" value="versions">
            <History className="h-4 w-4" />
            Versions
          </Tabs.Trigger>
          <Tabs.Trigger className="tab-trigger" value="activity">
            <Clock3 className="h-4 w-4" />
            Activity
          </Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content className="min-h-0 flex-1 px-3 pb-3 pt-4" value="versions">
          <ScrollArea.Root className="h-full overflow-hidden rounded-[24px] border border-stone-200 bg-stone-50/70">
            <ScrollArea.Viewport className="h-full p-3">
              <div className="space-y-3">
                {document.versions.map((version) => (
                  <article className="rounded-[22px] border border-stone-200 bg-white p-4" key={version.id}>
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="rounded-full bg-stone-950 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-white">
                            v{version.version_number}
                          </span>
                          {version.checkpoint ? (
                            <span className="rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-800">
                              checkpoint
                            </span>
                          ) : null}
                        </div>
                        <p className="mt-3 text-sm font-semibold text-stone-900">
                          {version.author?.name ?? 'System'}
                        </p>
                        <p className="mt-1 text-xs text-stone-500" title={fullDate(version.created_at)}>
                          {relativeTime(version.created_at)}
                        </p>
                        {version.note ? <p className="mt-3 text-sm text-stone-600">{version.note}</p> : null}
                      </div>
                      {!version.checkpoint ? (
                        <button
                          className="inline-flex items-center gap-2 rounded-full border border-stone-200 px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-stone-700 transition hover:border-stone-300 hover:text-stone-950"
                          onClick={() => onRestoreVersion(version)}
                          type="button"
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                          Restore
                        </button>
                      ) : null}
                    </div>
                  </article>
                ))}
              </div>
            </ScrollArea.Viewport>
          </ScrollArea.Root>
        </Tabs.Content>

        <Tabs.Content className="min-h-0 flex-1 px-3 pb-3 pt-4" value="activity">
          <ScrollArea.Root className="h-full overflow-hidden rounded-[24px] border border-stone-200 bg-stone-50/70">
            <ScrollArea.Viewport className="h-full p-3">
              <div className="space-y-3">
                {document.activity.map((entry) => (
                  <ActivityCard entry={entry} key={entry.id} />
                ))}
              </div>
            </ScrollArea.Viewport>
          </ScrollArea.Root>
        </Tabs.Content>
      </Tabs.Root>
    </aside>
  )
}

function ActivityCard({ entry }: { entry: ActivityEntry }) {
  return (
    <article className="rounded-[22px] border border-stone-200 bg-white p-4">
      <div className="flex items-start gap-3">
        <Avatar.Root className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-stone-200">
          <Avatar.Fallback className="text-xs font-bold uppercase tracking-[0.18em] text-stone-700">
            {(entry.user?.name ?? 'System')
              .split(' ')
              .map((part) => part[0])
              .join('')
              .slice(0, 2)}
          </Avatar.Fallback>
        </Avatar.Root>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-semibold text-stone-900">{entry.user?.name ?? 'System'}</p>
              <p className="mt-1 text-sm capitalize text-stone-600">
                {entry.type.replaceAll('.', ' ')}
              </p>
            </div>
            <Sparkles className="h-4 w-4 shrink-0 text-amber-500" />
          </div>
          <p className="mt-2 text-xs text-stone-500" title={fullDate(entry.created_at)}>
            {relativeTime(entry.created_at)}
          </p>
          {entry.payload ? (
            <pre className={cn('mt-3 overflow-auto rounded-2xl bg-stone-100 p-3 text-[11px] text-stone-600')}>
              {JSON.stringify(entry.payload, null, 2)}
            </pre>
          ) : null}
        </div>
      </div>
    </article>
  )
}
