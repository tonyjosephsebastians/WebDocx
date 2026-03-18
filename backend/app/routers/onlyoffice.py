from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import verify_onlyoffice_token
from app.models import Document, DocumentVersion, EditorSession, ShareGrant, User
from app.routers.auth import get_current_user
from app.schemas.documents import ForceSaveResponse, OnlyOfficeCallbackPayload, OnlyOfficeCallbackResponse
from app.services.documents import create_activity, new_editor_key, store_binary_metadata
from app.services.onlyoffice import trigger_forcesave
from app.services.storage import storage


router = APIRouter(prefix="/onlyoffice", tags=["onlyoffice"])


def verify_callback_token(payload: OnlyOfficeCallbackPayload, authorization: str | None) -> None:
    settings = get_settings()
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    elif payload.token:
        token = payload.token
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing ONLYOFFICE signature.")
    try:
        verify_onlyoffice_token(token, settings.onlyoffice_outbox_secret)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid ONLYOFFICE signature.") from exc


def _load_document_by_editor_key(db: Session, key: str) -> Document | None:
    return db.scalars(
        select(Document)
        .options(
            joinedload(Document.workspace),
            joinedload(Document.current_binary),
            joinedload(Document.versions).joinedload(DocumentVersion.binary),
            joinedload(Document.share_grants).joinedload(ShareGrant.shared_with_user),
        )
        .where(Document.editor_key == key)
    ).unique().one_or_none()


@router.post("/callback", response_model=OnlyOfficeCallbackResponse)
def handle_callback(
    payload: OnlyOfficeCallbackPayload,
    document_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> OnlyOfficeCallbackResponse:
    verify_callback_token(payload, authorization)
    document = _load_document_by_editor_key(db, payload.key)
    if document is None and document_id:
        document = db.scalar(select(Document).where(Document.id == document_id))
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if payload.status == 1:
        sessions = db.scalars(select(EditorSession).where(EditorSession.onlyoffice_key == payload.key)).all()
        for session in sessions:
            session.last_seen_at = session.last_seen_at
        create_activity(
            db,
            document.workspace_id,
            document.id,
            payload.users[-1] if payload.users else None,
            "editor.presence",
            {"users": payload.users or [], "session_id": session_id},
        )
    elif payload.status in {2, 6}:
        if not payload.url:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Callback save URL missing.")
        metadata = storage.store_bytes(storage.download_remote_file(payload.url), document.file_name)
        binary = store_binary_metadata(db, metadata)
        changes_file_path = None
        if payload.changesurl:
            changes_file_path = storage.save_remote_artifact(payload.changesurl, f"{document.slug}-changes.zip", "application/zip")
        previous_key = document.editor_key
        document.current_binary_id = binary.id
        document.latest_version_number += 1
        document.editor_key = new_editor_key()
        db.add(
            DocumentVersion(
                document_id=document.id,
                binary_id=binary.id,
                created_by_id=payload.users[-1] if payload.users else None,
                version_number=document.latest_version_number,
                checkpoint=payload.status == 6,
                onlyoffice_key=previous_key,
                changes_file_path=changes_file_path,
                history_json=payload.history.get("changes") if payload.history else None,
                history_server_version=payload.history.get("serverVersion") if payload.history else None,
                note="Checkpoint save" if payload.status == 6 else "Saved from ONLYOFFICE",
            )
        )
        if payload.status == 2:
            sessions = db.scalars(select(EditorSession).where(EditorSession.onlyoffice_key == previous_key)).all()
            for session in sessions:
                session.is_active = False
        create_activity(
            db,
            document.workspace_id,
            document.id,
            payload.users[-1] if payload.users else None,
            "document.checkpointed" if payload.status == 6 else "document.saved",
            {"version_number": document.latest_version_number},
        )
    elif payload.status == 4:
        create_activity(db, document.workspace_id, document.id, None, "editor.closed", {"changed": False})
    db.commit()
    return OnlyOfficeCallbackResponse(error=0)


@router.post("/forcesave", response_model=ForceSaveResponse)
def request_force_save(
    document_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ForceSaveResponse:
    document = db.scalar(select(Document).where(Document.id == document_id))
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    payload = trigger_forcesave(document.editor_key, userdata=current_user.id)
    create_activity(db, document.workspace_id, document.id, current_user.id, "document.forcesave_requested", payload)
    db.commit()
    return ForceSaveResponse(ok=True, payload=payload)
