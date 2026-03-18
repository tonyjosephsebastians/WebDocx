from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
import uuid

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    MEMBER = "member"


class DocumentAccessRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    COMMENTER = "commenter"
    VIEWER = "viewer"


class DocumentKind(StrEnum):
    STANDARD = "standard"
    COMPARISON = "comparison"


class EditorMode(StrEnum):
    VIEW = "view"
    COMMENT = "comment"
    REVIEW = "review"
    EDIT = "edit"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    memberships: Mapped[list[Membership]] = relationship(back_populates="user", cascade="all, delete-orphan")
    created_workspaces: Mapped[list[Workspace]] = relationship(back_populates="owner")
    created_documents: Mapped[list[Document]] = relationship(back_populates="created_by")
    shares_received: Mapped[list[ShareGrant]] = relationship(
        back_populates="shared_with_user",
        foreign_keys="ShareGrant.shared_with_user_id",
    )


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    owner: Mapped[User] = relationship(back_populates="created_workspaces")
    memberships: Mapped[list[Membership]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    documents: Mapped[list[Document]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_membership_workspace_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[WorkspaceRole] = mapped_column(Enum(WorkspaceRole), default=WorkspaceRole.MEMBER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    workspace: Mapped[Workspace] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class DocumentBinary(Base):
    __tablename__ = "document_binaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    path: Mapped[str] = mapped_column(String(512), unique=True)
    checksum: Mapped[str] = mapped_column(String(128), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    content_type: Mapped[str] = mapped_column(String(120), default="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    original_file_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    current_binary_id: Mapped[str] = mapped_column(ForeignKey("document_binaries.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[DocumentKind] = mapped_column(Enum(DocumentKind), default=DocumentKind.STANDARD)
    editor_key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    latest_version_number: Mapped[int] = mapped_column(Integer, default=1)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    workspace: Mapped[Workspace] = relationship(back_populates="documents")
    created_by: Mapped[User] = relationship(back_populates="created_documents")
    current_binary: Mapped[DocumentBinary] = relationship(foreign_keys=[current_binary_id])
    versions: Mapped[list[DocumentVersion]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.version_number",
    )
    share_grants: Mapped[list[ShareGrant]] = relationship(back_populates="document", cascade="all, delete-orphan")
    editor_sessions: Mapped[list[EditorSession]] = relationship(back_populates="document", cascade="all, delete-orphan")
    activities: Mapped[list[ActivityEvent]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "version_number", name="uq_document_versions_document_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    binary_id: Mapped[str] = mapped_column(ForeignKey("document_binaries.id"), index=True)
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    version_number: Mapped[int] = mapped_column(Integer)
    checkpoint: Mapped[bool] = mapped_column(Boolean, default=False)
    onlyoffice_key: Mapped[str] = mapped_column(String(120), index=True)
    changes_file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    history_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    history_server_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped[Document] = relationship(back_populates="versions")
    binary: Mapped[DocumentBinary] = relationship()
    created_by: Mapped[User | None] = relationship()


class EditorSession(Base):
    __tablename__ = "editor_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    onlyoffice_key: Mapped[str] = mapped_column(String(120), index=True)
    mode: Mapped[EditorMode] = mapped_column(Enum(EditorMode))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped[Document] = relationship(back_populates="editor_sessions")
    user: Mapped[User] = relationship()


class ShareGrant(Base):
    __tablename__ = "share_grants"
    __table_args__ = (UniqueConstraint("document_id", "shared_with_user_id", name="uq_share_document_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    shared_with_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[DocumentAccessRole] = mapped_column(Enum(DocumentAccessRole))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped[Document] = relationship(back_populates="share_grants")
    shared_with_user: Mapped[User] = relationship(
        back_populates="shares_received",
        foreign_keys=[shared_with_user_id],
    )
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])


class ComparisonDocument(Base):
    __tablename__ = "comparison_documents"
    __table_args__ = (UniqueConstraint("result_document_id", name="uq_comparison_result_document"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    revised_document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    result_document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    original_document: Mapped[Document] = relationship(foreign_keys=[original_document_id])
    revised_document: Mapped[Document] = relationship(foreign_keys=[revised_document_id])
    result_document: Mapped[Document] = relationship(foreign_keys=[result_document_id])
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped[Document | None] = relationship(back_populates="activities")
    workspace: Mapped[Workspace] = relationship()
    user: Mapped[User | None] = relationship()
