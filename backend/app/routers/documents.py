from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.database import get_db
from app.models import ActivityEvent, ComparisonDocument, Document, DocumentAccessRole, DocumentKind, DocumentVersion, EditorMode, EditorSession, ShareGrant, User
from app.routers.auth import get_current_user
from app.schemas.documents import CompareRequest, CompareResponse, CreateDocumentResponse, DocumentDetail, DocumentSummary, EditorConfigResponse, HistoryResponse, RestoreVersionResponse, ShareDocumentRequest, UpdateDocumentRequest
from app.services.documents import create_activity, create_document_from_upload, duplicate_document, list_documents_for_user, require_document_access, serialize_document, serialize_summary, set_share_grant, workspace_for_user
from app.services.onlyoffice import build_compare_descriptor, build_editor_config, history_data, history_entry
from app.services.storage import storage


router = APIRouter(prefix="/documents", tags=["documents"])


def _load_document(db: Session, document_id: str) -> Document:
    document = db.scalars(
        select(Document)
        .execution_options(populate_existing=True)
        .options(
            joinedload(Document.workspace),
            joinedload(Document.created_by),
            joinedload(Document.current_binary),
            joinedload(Document.versions).joinedload(DocumentVersion.binary),
            joinedload(Document.versions).joinedload(DocumentVersion.created_by),
            joinedload(Document.share_grants).joinedload(ShareGrant.shared_with_user),
            joinedload(Document.activities).joinedload(ActivityEvent.user),
        )
        .where(Document.id == document_id)
    ).unique().one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return document


@router.get("", response_model=list[DocumentSummary])
def list_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[DocumentSummary]:
    return [serialize_summary(document, role) for document, role in list_documents_for_user(db, current_user)]


@router.post("", response_model=CreateDocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    title: str = Form(...),
    workspace_id: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CreateDocumentResponse:
    workspace = workspace_for_user(db, current_user, workspace_id)
    document = await create_document_from_upload(db, current_user, workspace, title.strip(), file)
    db.commit()
    document = _load_document(db, document.id)
    return CreateDocumentResponse(document=serialize_document(document, DocumentAccessRole.OWNER))


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DocumentDetail:
    document, role = require_document_access(db, current_user, document_id)
    comparison = db.scalar(select(ComparisonDocument).where(ComparisonDocument.result_document_id == document.id))
    return serialize_document(document, role, comparison)


@router.patch("/{document_id}", response_model=DocumentDetail)
def update_document(
    document_id: str,
    payload: UpdateDocumentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentDetail:
    document, role = require_document_access(db, current_user, document_id, DocumentAccessRole.OWNER)
    document.title = payload.title.strip()
    document.file_name = f"{document.title.strip().replace(' ', '-').lower()}.docx"
    create_activity(db, document.workspace_id, document.id, current_user.id, "document.renamed", {"title": document.title})
    db.commit()
    document = _load_document(db, document.id)
    return serialize_document(document, role)


@router.post("/{document_id}/duplicate", response_model=CreateDocumentResponse, status_code=status.HTTP_201_CREATED)
def duplicate(document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CreateDocumentResponse:
    document, _ = require_document_access(db, current_user, document_id, DocumentAccessRole.VIEWER)
    duplicate_doc = duplicate_document(db, document, current_user)
    db.commit()
    duplicate_doc = _load_document(db, duplicate_doc.id)
    return CreateDocumentResponse(document=serialize_document(duplicate_doc, DocumentAccessRole.OWNER))


@router.post("/{document_id}/share", response_model=DocumentDetail)
def share_document(
    document_id: str,
    payload: ShareDocumentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentDetail:
    document, role = require_document_access(db, current_user, document_id, DocumentAccessRole.OWNER)
    target_user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found.")
    set_share_grant(db, document, current_user, target_user, payload.role)
    db.commit()
    document = _load_document(db, document.id)
    return serialize_document(document, role)


@router.post("/{document_id}/editor-config", response_model=EditorConfigResponse)
def get_editor_config(
    document_id: str,
    mode: EditorMode = Query(default=EditorMode.EDIT),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EditorConfigResponse:
    document, role = require_document_access(db, current_user, document_id, DocumentAccessRole.VIEWER)
    recent_documents = [item for item, _ in list_documents_for_user(db, current_user) if item.id != document.id]
    session = EditorSession(document_id=document.id, user_id=current_user.id, onlyoffice_key=document.editor_key, mode=mode)
    db.add(session)
    create_activity(db, document.workspace_id, document.id, current_user.id, "editor.opened", {"mode": mode.value})
    db.commit()
    settings = get_settings()
    config = build_editor_config(
        document=document,
        user=current_user,
        role=role,
        mode=mode,
        callback_url=f"{settings.trimmed_public_url}{settings.api_prefix}/onlyoffice/callback?document_id={document.id}&session_id={session.id}",
        download_url=f"{settings.trimmed_public_url}{settings.api_prefix}/documents/{document.id}/download",
        recent_documents=recent_documents,
    )
    comparison = db.scalar(select(ComparisonDocument).where(ComparisonDocument.result_document_id == document.id))
    compare_descriptor = None
    if comparison is not None:
        revised_document = _load_document(db, comparison.revised_document_id)
        compare_descriptor = build_compare_descriptor(
            revised_document.id,
            revised_document.file_name,
            f"{settings.trimmed_public_url}{settings.api_prefix}/documents/{revised_document.id}/download",
        )
    return EditorConfigResponse(
        document_server_url=settings.trimmed_document_server_url,
        config=config,
        mode=mode,
        compare_descriptor=compare_descriptor,
    )


@router.get("/{document_id}/history", response_model=HistoryResponse)
def get_history(document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> HistoryResponse:
    document, _ = require_document_access(db, current_user, document_id)
    versions = [
        {
            "id": version.id,
            "version_number": version.version_number,
            "checkpoint": version.checkpoint,
            "onlyoffice_key": version.onlyoffice_key,
            "created_at": version.created_at,
            "note": version.note,
            "history_server_version": version.history_server_version,
            "author": version.created_by,
        }
        for version in sorted(document.versions, key=lambda item: item.version_number, reverse=True)
    ]
    return HistoryResponse(document_id=document.id, versions=versions)


@router.get("/{document_id}/history/editor")
def get_history_for_editor(document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    document, _ = require_document_access(db, current_user, document_id)
    visible_versions = [version for version in sorted(document.versions, key=lambda item: item.version_number) if not version.checkpoint]
    return {
        "currentVersion": visible_versions[-1].version_number if visible_versions else document.latest_version_number,
        "history": [history_entry(version) for version in visible_versions],
    }


@router.get("/{document_id}/history/{version_number}/editor")
def get_history_version_for_editor(
    document_id: str,
    version_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    document, _ = require_document_access(db, current_user, document_id)
    visible_versions = sorted([version for version in document.versions if not version.checkpoint], key=lambda item: item.version_number)
    version = next((item for item in visible_versions if item.version_number == version_number), None)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found.")
    index = visible_versions.index(version)
    previous_version = visible_versions[index - 1] if index > 0 else None
    settings = get_settings()
    return history_data(version, settings.trimmed_public_url, document.id, previous_version)


@router.post("/{document_id}/history/{version_number}/restore", response_model=RestoreVersionResponse)
def restore_version(
    document_id: str,
    version_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RestoreVersionResponse:
    document, role = require_document_access(db, current_user, document_id, DocumentAccessRole.OWNER)
    version = next((item for item in document.versions if item.version_number == version_number), None)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found.")
    document.current_binary_id = version.binary_id
    document.latest_version_number += 1
    document.editor_key = f"{document.id}-{document.latest_version_number}"
    db.add(
        DocumentVersion(
            document_id=document.id,
            binary_id=version.binary_id,
            created_by_id=current_user.id,
            version_number=document.latest_version_number,
            checkpoint=False,
            onlyoffice_key=document.editor_key,
            history_json=version.history_json,
            history_server_version=version.history_server_version,
            note=f"Restored from version {version_number}",
        )
    )
    create_activity(db, document.workspace_id, document.id, current_user.id, "document.restored", {"version_number": version_number})
    db.commit()
    document = _load_document(db, document.id)
    return RestoreVersionResponse(document=serialize_document(document, role))


@router.post("/{document_id}/compare", response_model=CompareResponse, status_code=status.HTTP_201_CREATED)
def compare_documents(
    document_id: str,
    payload: CompareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompareResponse:
    source_document, _ = require_document_access(db, current_user, document_id)
    revised_document, _ = require_document_access(db, current_user, payload.revised_document_id)
    result_document = duplicate_document(db, source_document, current_user, f"{source_document.title} vs {revised_document.title}")
    result_document.kind = DocumentKind.COMPARISON
    record = ComparisonDocument(
        original_document_id=source_document.id,
        revised_document_id=revised_document.id,
        result_document_id=result_document.id,
        created_by_id=current_user.id,
    )
    db.add(record)
    create_activity(
        db,
        source_document.workspace_id,
        result_document.id,
        current_user.id,
        "document.compared",
        {"original_document_id": source_document.id, "revised_document_id": revised_document.id},
    )
    db.commit()
    result_document = _load_document(db, result_document.id)
    return CompareResponse(document=serialize_document(result_document, DocumentAccessRole.OWNER, record))


@router.get("/{document_id}/download")
def download_document(document_id: str, db: Session = Depends(get_db)) -> FileResponse:
    document = _load_document(db, document_id)
    return FileResponse(storage.resolve(document.current_binary.path), media_type=document.current_binary.content_type, filename=document.file_name)


@router.get("/{document_id}/versions/{version_number}/download")
def download_version(document_id: str, version_number: int, db: Session = Depends(get_db)) -> FileResponse:
    document = _load_document(db, document_id)
    version = next((item for item in document.versions if item.version_number == version_number), None)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found.")
    return FileResponse(storage.resolve(version.binary.path), media_type=version.binary.content_type, filename=document.file_name)


@router.get("/{document_id}/versions/{version_number}/changes")
def download_version_changes(document_id: str, version_number: int, db: Session = Depends(get_db)) -> FileResponse:
    document = _load_document(db, document_id)
    version = next((item for item in document.versions if item.version_number == version_number), None)
    if version is None or not version.changes_file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Changes archive not found.")
    return FileResponse(storage.resolve(version.changes_file_path), media_type="application/zip", filename=f"{document.slug}-v{version.version_number}-changes.zip")
