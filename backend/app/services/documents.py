from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
import re
import uuid
import zipfile

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    ActivityEvent,
    ComparisonDocument,
    Document,
    DocumentAccessRole,
    DocumentBinary,
    DocumentKind,
    DocumentVersion,
    Membership,
    ShareGrant,
    User,
    Workspace,
    WorkspaceRole,
)
from app.schemas.auth import AuthUser, WorkspaceSummary
from app.schemas.documents import (
    ActivityResponse,
    ComparisonInfo,
    DocumentDetail,
    DocumentSummary,
    ShareGrantResponse,
    UserRef,
    VersionResponse,
    WorkspaceRef,
)
from app.services.storage import storage


ROLE_ORDER = {
    DocumentAccessRole.VIEWER: 1,
    DocumentAccessRole.COMMENTER: 2,
    DocumentAccessRole.REVIEWER: 3,
    DocumentAccessRole.EDITOR: 4,
    DocumentAccessRole.OWNER: 5,
}


def slugify_text(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or uuid.uuid4().hex[:8]


def unique_slug(db: Session, model: type, source: str) -> str:
    base = slugify_text(source)
    candidate = base
    counter = 1
    while db.scalar(select(model).where(model.slug == candidate)) is not None:
        counter += 1
        candidate = f"{base}-{counter}"
    return candidate


def new_editor_key() -> str:
    return uuid.uuid4().hex


def build_blank_docx(title: str) -> bytes:
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "docProps/app.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>Word Workspace</Application>
</Properties>""",
        )
        archive.writestr(
            "docProps/core.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{title}</dc:title>
  <dc:creator>Word Workspace</dc:creator>
  <dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>
</cp:coreProperties>""",
        )
        archive.writestr(
            "word/styles.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
  </w:style>
</w:styles>""",
        )
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t xml:space="preserve"></w:t></w:r></w:p>
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
      <w:cols w:space="720"/>
      <w:docGrid w:linePitch="360"/>
    </w:sectPr>
  </w:body>
</w:document>""",
        )
    return buffer.getvalue()


def create_activity(
    db: Session,
    workspace_id: str,
    document_id: str | None,
    user_id: str | None,
    type_: str,
    payload: dict | None = None,
) -> ActivityEvent:
    event = ActivityEvent(
        workspace_id=workspace_id,
        document_id=document_id,
        user_id=user_id,
        type=type_,
        payload=payload,
    )
    db.add(event)
    return event


def store_binary_metadata(db: Session, metadata: dict) -> DocumentBinary:
    binary = DocumentBinary(**metadata)
    db.add(binary)
    db.flush()
    return binary


def create_workspace_for_user(db: Session, user: User, workspace_name: str) -> Workspace:
    workspace = Workspace(
        name=workspace_name,
        slug=unique_slug(db, Workspace, workspace_name),
        owner_id=user.id,
    )
    db.add(workspace)
    db.flush()
    db.add(Membership(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.OWNER))
    create_activity(db, workspace.id, None, user.id, "workspace.created", {"name": workspace.name})
    db.flush()
    return workspace


def workspace_for_user(db: Session, user: User, workspace_id: str | None = None) -> Workspace:
    query = select(Workspace).options(joinedload(Workspace.owner))
    if workspace_id:
        query = query.where(Workspace.id == workspace_id)
    else:
        query = query.where(Workspace.owner_id == user.id)
    workspace = db.scalar(query)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    membership = db.scalar(
        select(Membership).where(Membership.workspace_id == workspace.id, Membership.user_id == user.id)
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not belong to this workspace.")
    return workspace


def role_for_document(document: Document, user: User) -> DocumentAccessRole | None:
    if document.created_by_id == user.id or document.workspace.owner_id == user.id:
        return DocumentAccessRole.OWNER
    for share in document.share_grants:
        if share.shared_with_user_id == user.id:
            return share.role
    return None


def _document_query() -> select:
    return select(Document).options(
        joinedload(Document.workspace),
        joinedload(Document.created_by),
        joinedload(Document.current_binary),
        joinedload(Document.versions).joinedload(DocumentVersion.binary),
        joinedload(Document.versions).joinedload(DocumentVersion.created_by),
        joinedload(Document.share_grants).joinedload(ShareGrant.shared_with_user),
        joinedload(Document.activities).joinedload(ActivityEvent.user),
    )


def require_document_access(
    db: Session,
    user: User,
    document_id: str,
    minimum_role: DocumentAccessRole = DocumentAccessRole.VIEWER,
) -> tuple[Document, DocumentAccessRole]:
    document = db.scalars(_document_query().where(Document.id == document_id)).unique().one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    role = role_for_document(document, user)
    if role is None or ROLE_ORDER[role] < ROLE_ORDER[minimum_role]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this document.")
    return document, role


def list_documents_for_user(db: Session, user: User) -> list[tuple[Document, DocumentAccessRole]]:
    documents = db.scalars(_document_query().order_by(Document.updated_at.desc())).unique().all()
    result: list[tuple[Document, DocumentAccessRole]] = []
    for document in documents:
        role = role_for_document(document, user)
        if role is not None:
            result.append((document, role))
    return result


def _user_ref(user: User | None) -> UserRef | None:
    if user is None:
        return None
    return UserRef(id=user.id, name=user.name, email=user.email)


def serialize_document(
    document: Document,
    current_role: DocumentAccessRole,
    comparison: ComparisonDocument | None = None,
) -> DocumentDetail:
    return DocumentDetail(
        id=document.id,
        title=document.title,
        file_name=document.file_name,
        kind=document.kind,
        created_at=document.created_at,
        updated_at=document.updated_at,
        latest_version_number=document.latest_version_number,
        current_role=current_role,
        workspace=WorkspaceRef(id=document.workspace.id, name=document.workspace.name, slug=document.workspace.slug),
        created_by=UserRef(id=document.created_by.id, name=document.created_by.name, email=document.created_by.email),
        share_grants=[
            ShareGrantResponse(
                id=share.id,
                role=share.role,
                shared_with_user=UserRef(
                    id=share.shared_with_user.id,
                    name=share.shared_with_user.name,
                    email=share.shared_with_user.email,
                ),
                created_at=share.created_at,
            )
            for share in sorted(document.share_grants, key=lambda item: item.created_at, reverse=True)
        ],
        activity=[
            ActivityResponse(
                id=event.id,
                type=event.type,
                payload=event.payload,
                created_at=event.created_at,
                user=_user_ref(event.user),
            )
            for event in sorted(document.activities, key=lambda item: item.created_at, reverse=True)[:20]
        ],
        versions=[
            VersionResponse(
                id=version.id,
                version_number=version.version_number,
                checkpoint=version.checkpoint,
                onlyoffice_key=version.onlyoffice_key,
                created_at=version.created_at,
                note=version.note,
                history_server_version=version.history_server_version,
                author=_user_ref(version.created_by),
            )
            for version in sorted(document.versions, key=lambda item: item.version_number, reverse=True)
        ],
        comparison=ComparisonInfo(
            id=comparison.id,
            original_document_id=comparison.original_document_id,
            revised_document_id=comparison.revised_document_id,
            result_document_id=comparison.result_document_id,
        )
        if comparison
        else None,
    )


def serialize_summary(document: Document, current_role: DocumentAccessRole) -> DocumentSummary:
    return DocumentSummary(
        id=document.id,
        title=document.title,
        file_name=document.file_name,
        kind=document.kind,
        updated_at=document.updated_at,
        latest_version_number=document.latest_version_number,
        current_role=current_role,
        workspace=WorkspaceRef(id=document.workspace.id, name=document.workspace.name, slug=document.workspace.slug),
        created_by=UserRef(id=document.created_by.id, name=document.created_by.name, email=document.created_by.email),
    )


def create_document_record(
    db: Session,
    user: User,
    workspace: Workspace,
    title: str,
    binary: DocumentBinary,
    kind: DocumentKind = DocumentKind.STANDARD,
    note: str | None = None,
) -> Document:
    document = Document(
        workspace_id=workspace.id,
        created_by_id=user.id,
        current_binary_id=binary.id,
        title=title,
        slug=unique_slug(db, Document, title),
        file_name=f"{slugify_text(title)}.docx",
        kind=kind,
        editor_key=new_editor_key(),
        latest_version_number=1,
    )
    db.add(document)
    db.flush()
    db.add(
        DocumentVersion(
            document_id=document.id,
            binary_id=binary.id,
            created_by_id=user.id,
            version_number=1,
            checkpoint=False,
            onlyoffice_key=document.editor_key,
            note=note,
        )
    )
    create_activity(db, workspace.id, document.id, user.id, "document.created", {"title": title})
    db.flush()
    return document


async def create_document_from_upload(
    db: Session,
    user: User,
    workspace: Workspace,
    title: str,
    upload: UploadFile | None,
) -> Document:
    if upload is not None:
        file_name = upload.filename or ""
        if not file_name.lower().endswith(".docx"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DOCX uploads are supported in this version.",
            )
        metadata = await storage.store_upload(upload, file_name)
    else:
        metadata = storage.store_bytes(build_blank_docx(title), f"{slugify_text(title)}.docx")
    binary = store_binary_metadata(db, metadata)
    return create_document_record(db, user, workspace, title, binary)


def duplicate_document(db: Session, source_document: Document, user: User, title: str | None = None) -> Document:
    metadata = storage.copy_existing(source_document.current_binary.path, source_document.file_name)
    binary = store_binary_metadata(db, metadata)
    return create_document_record(
        db,
        user,
        source_document.workspace,
        title or f"{source_document.title} Copy",
        binary,
        kind=source_document.kind,
        note=f"Duplicated from {source_document.title}",
    )


def ensure_workspace_membership(db: Session, workspace: Workspace, user: User) -> Membership:
    membership = db.scalar(
        select(Membership).where(Membership.workspace_id == workspace.id, Membership.user_id == user.id)
    )
    if membership is None:
        membership = Membership(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.MEMBER)
        db.add(membership)
        db.flush()
    return membership


def set_share_grant(
    db: Session,
    document: Document,
    current_user: User,
    target_user: User,
    role: DocumentAccessRole,
) -> ShareGrant:
    ensure_workspace_membership(db, document.workspace, target_user)
    grant = db.scalar(
        select(ShareGrant).where(
            ShareGrant.document_id == document.id,
            ShareGrant.shared_with_user_id == target_user.id,
        )
    )
    if grant is None:
        grant = ShareGrant(
            document_id=document.id,
            shared_with_user_id=target_user.id,
            created_by_id=current_user.id,
            role=role,
        )
        db.add(grant)
    else:
        grant.role = role
        grant.created_by_id = current_user.id
    create_activity(
        db,
        document.workspace_id,
        document.id,
        current_user.id,
        "document.shared",
        {"target_user_id": target_user.id, "role": role},
    )
    db.flush()
    return grant


def build_auth_user(user: User) -> AuthUser:
    return AuthUser(
        id=user.id,
        name=user.name,
        email=user.email,
        workspaces=[
            WorkspaceSummary(
                id=membership.workspace.id,
                name=membership.workspace.name,
                slug=membership.workspace.slug,
            )
            for membership in user.memberships
        ],
    )
