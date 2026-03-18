import { apiBaseUrl } from "./utils"
import type { DocumentDetail, DocumentSummary, EditorConfigResponse, HistoryResponse, TokenResponse } from "./types"

type ApiOptions = {
  method?: 'GET' | 'POST' | 'PATCH'
  token?: string | null
  body?: BodyInit | Record<string, unknown> | null
}

async function request<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers = new Headers()
  if (options.token) {
    headers.set('Authorization', `Bearer ${options.token}`)
  }

  let body: BodyInit | undefined
  if (options.body instanceof FormData || typeof options.body === 'string' || options.body instanceof URLSearchParams) {
    body = options.body
  } else if (options.body) {
    headers.set('Content-Type', 'application/json')
    body = JSON.stringify(options.body)
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body,
  })

  if (!response.ok) {
    const fallback = 'Request failed'
    const text = await response.text()
    let message = fallback
    try {
      const parsed = JSON.parse(text) as { detail?: string }
      message = parsed.detail ?? fallback
    } catch {
      if (text) {
        message = text
      }
    }
    throw new Error(message)
  }

  return response.json() as Promise<T>
}

export const api = {
  register(payload: { name: string; email: string; password: string; workspace_name?: string }) {
    return request<TokenResponse>('/auth/register', { method: 'POST', body: payload })
  },
  login(payload: { email: string; password: string }) {
    return request<TokenResponse>('/auth/login', { method: 'POST', body: payload })
  },
  me(token: string) {
    return request<TokenResponse>('/auth/me', { token })
  },
  listDocuments(token: string) {
    return request<DocumentSummary[]>('/documents', { token })
  },
  getDocument(token: string, documentId: string) {
    return request<DocumentDetail>(`/documents/${documentId}`, { token })
  },
  createDocument(token: string, payload: { title: string; workspaceId?: string; file?: File | null }) {
    const form = new FormData()
    form.set('title', payload.title)
    if (payload.workspaceId) {
      form.set('workspace_id', payload.workspaceId)
    }
    if (payload.file) {
      form.set('file', payload.file)
    }
    return request<{ document: DocumentDetail }>('/documents', {
      method: 'POST',
      token,
      body: form,
    })
  },
  duplicateDocument(token: string, documentId: string) {
    return request<{ document: DocumentDetail }>(`/documents/${documentId}/duplicate`, {
      method: 'POST',
      token,
    })
  },
  updateDocument(token: string, documentId: string, title: string) {
    return request<DocumentDetail>(`/documents/${documentId}`, {
      method: 'PATCH',
      token,
      body: { title },
    })
  },
  shareDocument(token: string, documentId: string, payload: { email: string; role: string }) {
    return request<DocumentDetail>(`/documents/${documentId}/share`, {
      method: 'POST',
      token,
      body: payload,
    })
  },
  compareDocument(token: string, documentId: string, revisedDocumentId: string) {
    return request<{ document: DocumentDetail }>(`/documents/${documentId}/compare`, {
      method: 'POST',
      token,
      body: { revised_document_id: revisedDocumentId },
    })
  },
  getEditorConfig(token: string, documentId: string, mode: string) {
    return request<EditorConfigResponse>(`/documents/${documentId}/editor-config?mode=${mode}`, {
      method: 'POST',
      token,
    })
  },
  getHistory(token: string, documentId: string) {
    return request<HistoryResponse>(`/documents/${documentId}/history`, { token })
  },
  getEditorHistory(token: string, documentId: string) {
    return request<Record<string, unknown>>(`/documents/${documentId}/history/editor`, { token })
  },
  getEditorHistoryVersion(token: string, documentId: string, versionNumber: number) {
    return request<Record<string, unknown>>(`/documents/${documentId}/history/${versionNumber}/editor`, { token })
  },
  restoreVersion(token: string, documentId: string, versionNumber: number) {
    return request<{ document: DocumentDetail }>(`/documents/${documentId}/history/${versionNumber}/restore`, {
      method: 'POST',
      token,
    })
  },
  forceSave(token: string, documentId: string) {
    return request<{ ok: boolean; payload: Record<string, unknown> }>(`/onlyoffice/forcesave?document_id=${documentId}`, {
      method: 'POST',
      token,
    })
  },
}
