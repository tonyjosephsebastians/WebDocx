import { forwardRef, useCallback, useEffect, useId, useImperativeHandle, useRef, useState } from 'react'
import { toast } from 'sonner'

import { api } from '../lib/api'

type Props = {
  documentId: string
  documentServerUrl: string
  config: Record<string, unknown>
  token: string
  compareDescriptor: Record<string, unknown> | null
  onRestored: () => Promise<void>
}

export type OnlyOfficeHandle = {
  applyCompare: () => void
}

function loadScript(documentServerUrl: string) {
  return new Promise<void>((resolve, reject) => {
    if (window.DocsAPI) {
      resolve()
      return
    }

    const src = `${documentServerUrl.replace(/\/$/, '')}/web-apps/apps/api/documents/api.js`
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${src}"]`)
    if (existing) {
      existing.addEventListener('load', () => resolve(), { once: true })
      existing.addEventListener('error', () => reject(new Error('Failed to load ONLYOFFICE Docs API.')), { once: true })
      return
    }

    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load ONLYOFFICE Docs API.'))
    document.body.appendChild(script)
  })
}

export const OnlyOfficeEditor = forwardRef<OnlyOfficeHandle, Props>(function OnlyOfficeEditor(
  { documentId, documentServerUrl, config, token, compareDescriptor, onRestored },
  ref,
) {
  const containerId = useId().replace(/:/g, '')
  const editorRef = useRef<{
    destroyEditor?: () => void
    refreshHistory?: (payload: Record<string, unknown>) => void
    setHistoryData?: (payload: Record<string, unknown>) => void
    setRequestedDocument?: (payload: Record<string, unknown>) => void
    setRevisedFile?: (payload: Record<string, unknown>) => void
  } | null>(null)
  const [loading, setLoading] = useState(true)

  const applyCompare = useCallback(() => {
    if (!compareDescriptor) {
      toast.error('No comparison source is attached to this draft yet.')
      return
    }
    if (editorRef.current?.setRequestedDocument) {
      editorRef.current.setRequestedDocument(compareDescriptor)
      return
    }
    if (editorRef.current?.setRevisedFile) {
      editorRef.current.setRevisedFile(compareDescriptor)
      return
    }
    toast.error('This ONLYOFFICE build does not expose compare injection methods.')
  }, [compareDescriptor])

  useImperativeHandle(ref, () => ({ applyCompare }))

  useEffect(() => {
    let cancelled = false

    const boot = async () => {
      setLoading(true)
      try {
        await loadScript(documentServerUrl)
        if (cancelled) {
          return
        }

        editorRef.current?.destroyEditor?.()
        editorRef.current = new window.DocsAPI!.DocEditor(containerId, {
          ...config,
          events: {
            onDocumentReady() {
              setLoading(false)
            },
            async onRequestHistory() {
              const payload = await api.getEditorHistory(token, documentId)
              editorRef.current?.refreshHistory?.(payload)
            },
            async onRequestHistoryData(event: { data: number }) {
              const payload = await api.getEditorHistoryVersion(token, documentId, event.data)
              editorRef.current?.setHistoryData?.(payload)
            },
            async onRequestRestore(event: { data: { version: number } }) {
              await api.restoreVersion(token, documentId, event.data.version)
              await onRestored()
              toast.success(`Restored version ${event.data.version}.`)
            },
            onRequestHistoryClose() {
              void onRestored()
            },
            onRequestSelectDocument() {
              applyCompare()
            },
            onRequestCompareFile() {
              applyCompare()
            },
            onError(event: { data?: { errorDescription?: string } }) {
              toast.error(event.data?.errorDescription ?? 'ONLYOFFICE reported an editor error.')
            },
          },
        })
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unable to initialize ONLYOFFICE.'
        toast.error(message)
        setLoading(false)
      }
    }

    void boot()
    return () => {
      cancelled = true
      editorRef.current?.destroyEditor?.()
      editorRef.current = null
    }
  }, [applyCompare, compareDescriptor, config, containerId, documentId, documentServerUrl, onRestored, token])

  return (
    <div className="relative h-full min-h-[42rem] overflow-hidden rounded-[34px] border border-white/70 bg-[linear-gradient(180deg,#f4efe6_0%,#f7f3ec_35%,#ede3d7_100%)] shadow-[0_40px_120px_rgba(45,28,12,0.18)]">
      {loading ? (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/70 backdrop-blur">
          <div className="rounded-full border border-stone-200 bg-white px-5 py-3 text-sm font-semibold text-stone-700">
            Loading editor...
          </div>
        </div>
      ) : null}
      <div className="h-full min-h-[42rem]" id={containerId} />
    </div>
  )
})
