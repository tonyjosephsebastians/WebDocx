import * as Dialog from '@radix-ui/react-dialog'
import * as Select from '@radix-ui/react-select'
import { ChevronDown, X } from 'lucide-react'
import { useState } from 'react'

import type { DocumentSummary } from '../lib/types'

type Props = {
  document: DocumentSummary | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (payload: { email: string; role: string }) => Promise<void>
}

const roles = ['viewer', 'commenter', 'reviewer', 'editor'] as const

export function ShareDialog({ document, open, onOpenChange, onSubmit }: Props) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<(typeof roles)[number]>('editor')
  const [submitting, setSubmitting] = useState(false)

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-stone-950/30 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,30rem)] -translate-x-1/2 -translate-y-1/2 rounded-[32px] border border-white/50 bg-[linear-gradient(145deg,rgba(255,253,249,0.98),rgba(244,238,229,0.95))] p-7 shadow-[0_30px_80px_rgba(32,22,12,0.25)]">
          <div className="flex items-start justify-between gap-4">
            <div>
              <Dialog.Title className="font-display text-3xl text-stone-950">Share document</Dialog.Title>
              <Dialog.Description className="mt-2 text-sm text-stone-600">
                Invite an existing app user to collaborate on {document?.title ?? 'this document'}.
              </Dialog.Description>
            </div>
            <Dialog.Close className="rounded-full border border-stone-200 p-2 text-stone-500 transition hover:text-stone-900">
              <X className="h-4 w-4" />
            </Dialog.Close>
          </div>

          <form
            className="mt-8 space-y-4"
            onSubmit={async (event) => {
              event.preventDefault()
              setSubmitting(true)
              try {
                await onSubmit({ email, role })
                setEmail('')
                setRole('editor')
                onOpenChange(false)
              } finally {
                setSubmitting(false)
              }
            }}
          >
            <label className="block">
              <span className="mb-2 block text-sm font-semibold text-stone-700">Email</span>
              <input
                className="input"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="teammate@example.com"
                required
                type="email"
                value={email}
              />
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-semibold text-stone-700">Role</span>
              <Select.Root onValueChange={(value) => setRole(value as (typeof roles)[number])} value={role}>
                <Select.Trigger className="input flex items-center justify-between">
                  <Select.Value />
                  <ChevronDown className="h-4 w-4 text-stone-500" />
                </Select.Trigger>
                <Select.Portal>
                  <Select.Content className="z-50 overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-xl">
                    <Select.Viewport className="p-2">
                      {roles.map((item) => (
                        <Select.Item className="menu-item" key={item} value={item}>
                          <Select.ItemText>{item}</Select.ItemText>
                        </Select.Item>
                      ))}
                    </Select.Viewport>
                  </Select.Content>
                </Select.Portal>
              </Select.Root>
            </label>

            <button className="button-primary w-full" disabled={submitting} type="submit">
              {submitting ? 'Sharing...' : 'Share document'}
            </button>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
