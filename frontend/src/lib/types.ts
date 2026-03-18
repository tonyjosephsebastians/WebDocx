export type DocumentRole = 'owner' | 'editor' | 'reviewer' | 'commenter' | 'viewer'
export type EditorMode = 'view' | 'comment' | 'review' | 'edit'
export type DocumentKind = 'standard' | 'comparison'

export interface Workspace {
  id: string
  name: string
  slug: string
}

export interface UserRef {
  id: string
  name: string
  email: string
}

export interface AuthUser extends UserRef {
  workspaces: Workspace[]
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  user: AuthUser
}

export interface ShareGrant {
  id: string
  role: DocumentRole
  created_at: string
  shared_with_user: UserRef
}

export interface VersionEntry {
  id: string
  version_number: number
  checkpoint: boolean
  onlyoffice_key: string
  created_at: string
  note: string | null
  history_server_version: number | null
  author: UserRef | null
}

export interface ActivityEntry {
  id: string
  type: string
  payload: Record<string, unknown> | null
  created_at: string
  user: UserRef | null
}

export interface ComparisonInfo {
  id: string
  original_document_id: string
  revised_document_id: string
  result_document_id: string
}

export interface DocumentSummary {
  id: string
  title: string
  file_name: string
  kind: DocumentKind
  updated_at: string
  latest_version_number: number
  current_role: DocumentRole
  workspace: Workspace
  created_by: UserRef
}

export interface DocumentDetail extends DocumentSummary {
  created_at: string
  share_grants: ShareGrant[]
  activity: ActivityEntry[]
  versions: VersionEntry[]
  comparison: ComparisonInfo | null
}

export interface EditorConfigResponse {
  document_server_url: string
  config: Record<string, unknown>
  mode: EditorMode
  compare_descriptor: Record<string, unknown> | null
}

export interface HistoryResponse {
  document_id: string
  versions: VersionEntry[]
}
