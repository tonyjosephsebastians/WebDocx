from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import DocumentAccessRole, DocumentKind, EditorMode


class WorkspaceRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str


class UserRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr


class ShareGrantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: DocumentAccessRole
    shared_with_user: UserRef
    created_at: datetime


class VersionResponse(BaseModel):
    id: str
    version_number: int
    checkpoint: bool
    onlyoffice_key: str
    created_at: datetime
    note: str | None
    history_server_version: int | None
    author: UserRef | None


class ActivityResponse(BaseModel):
    id: str
    type: str
    payload: dict[str, Any] | None
    created_at: datetime
    user: UserRef | None


class ComparisonInfo(BaseModel):
    id: str
    original_document_id: str
    revised_document_id: str
    result_document_id: str


class DocumentSummary(BaseModel):
    id: str
    title: str
    file_name: str
    kind: DocumentKind
    updated_at: datetime
    latest_version_number: int
    current_role: DocumentAccessRole
    workspace: WorkspaceRef
    created_by: UserRef


class DocumentDetail(DocumentSummary):
    created_at: datetime
    share_grants: list[ShareGrantResponse]
    activity: list[ActivityResponse]
    versions: list[VersionResponse]
    comparison: ComparisonInfo | None = None


class ShareDocumentRequest(BaseModel):
    email: EmailStr
    role: DocumentAccessRole


class UpdateDocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class CreateDocumentResponse(BaseModel):
    document: DocumentDetail


class EditorConfigResponse(BaseModel):
    document_server_url: str
    config: dict[str, Any]
    mode: EditorMode
    compare_descriptor: dict[str, Any] | None = None


class RestoreVersionResponse(BaseModel):
    document: DocumentDetail


class CompareRequest(BaseModel):
    revised_document_id: str


class CompareResponse(BaseModel):
    document: DocumentDetail


class HistoryResponse(BaseModel):
    document_id: str
    versions: list[VersionResponse]


class OnlyOfficeCallbackPayload(BaseModel):
    actions: list[dict[str, Any]] | None = None
    changesurl: str | None = None
    filetype: str | None = None
    forcesavetype: int | None = None
    formsdataurl: str | None = None
    history: dict[str, Any] | None = None
    key: str
    status: int
    token: str | None = None
    url: str | None = None
    userdata: str | None = None
    users: list[str] | None = None


class OnlyOfficeCallbackResponse(BaseModel):
    error: int


class ForceSaveResponse(BaseModel):
    ok: bool
    payload: dict[str, Any]
