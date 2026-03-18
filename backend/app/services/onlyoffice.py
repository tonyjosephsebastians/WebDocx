from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings
from app.core.security import sign_onlyoffice_payload
from app.models import Document, DocumentAccessRole, DocumentVersion, EditorMode, User
from app.services.documents import ROLE_ORDER


MODE_TO_MINIMUM_ROLE = {
    EditorMode.VIEW: DocumentAccessRole.VIEWER,
    EditorMode.COMMENT: DocumentAccessRole.COMMENTER,
    EditorMode.REVIEW: DocumentAccessRole.REVIEWER,
    EditorMode.EDIT: DocumentAccessRole.EDITOR,
}


def resolve_mode_for_role(requested_mode: EditorMode, actual_role: DocumentAccessRole) -> EditorMode:
    if ROLE_ORDER[actual_role] >= ROLE_ORDER[MODE_TO_MINIMUM_ROLE[requested_mode]]:
        return requested_mode
    if ROLE_ORDER[actual_role] >= ROLE_ORDER[DocumentAccessRole.REVIEWER]:
        return EditorMode.REVIEW
    if ROLE_ORDER[actual_role] >= ROLE_ORDER[DocumentAccessRole.COMMENTER]:
        return EditorMode.COMMENT
    return EditorMode.VIEW


def build_permissions(role: DocumentAccessRole, mode: EditorMode) -> dict[str, bool]:
    permissions = {
        "chat": True,
        "comment": False,
        "copy": True,
        "download": True,
        "edit": False,
        "print": True,
        "rename": role == DocumentAccessRole.OWNER,
        "review": False,
    }
    if mode == EditorMode.EDIT and ROLE_ORDER[role] >= ROLE_ORDER[DocumentAccessRole.EDITOR]:
        permissions["edit"] = True
        permissions["comment"] = True
        permissions["review"] = True
    elif mode == EditorMode.REVIEW and ROLE_ORDER[role] >= ROLE_ORDER[DocumentAccessRole.REVIEWER]:
        permissions["review"] = True
        permissions["comment"] = True
    elif mode == EditorMode.COMMENT and ROLE_ORDER[role] >= ROLE_ORDER[DocumentAccessRole.COMMENTER]:
        permissions["comment"] = True
    return permissions


def recent_file_item(document: Document, public_url: str) -> dict[str, str]:
    return {
        "folder": document.workspace.name,
        "title": document.title,
        "url": f"{public_url}/documents/{document.id}",
    }


def build_compare_descriptor(document_id: str, file_name: str, download_url: str) -> dict[str, Any]:
    settings = get_settings()
    payload = {
        "fileType": "docx",
        "key": document_id,
        "title": file_name,
        "url": download_url,
    }
    return {
        "fileType": "docx",
        "title": file_name,
        "url": download_url,
        "token": sign_onlyoffice_payload(payload, settings.onlyoffice_browser_secret),
    }


def build_editor_config(
    *,
    document: Document,
    user: User,
    role: DocumentAccessRole,
    mode: EditorMode,
    callback_url: str,
    download_url: str,
    recent_documents: list[Document],
) -> dict[str, Any]:
    settings = get_settings()
    resolved_mode = resolve_mode_for_role(mode, role)
    config = {
        "document": {
            "fileType": "docx",
            "key": document.editor_key,
            "title": document.file_name,
            "url": download_url,
            "permissions": build_permissions(role, resolved_mode),
        },
        "documentType": "word",
        "editorConfig": {
            "callbackUrl": callback_url,
            "coEditing": {"mode": "fast", "change": True},
            "customization": {
                "autosave": True,
                "compactHeader": False,
                "compactToolbar": False,
                "forcesave": True,
                "toolbarNoTabs": False,
                "uiTheme": "theme-light",
            },
            "lang": "en",
            "mode": "view" if resolved_mode == EditorMode.VIEW else "edit",
            "recent": [recent_file_item(item, settings.trimmed_public_url) for item in recent_documents[:6]],
            "user": {
                "group": document.workspace.name,
                "id": user.id,
                "name": user.name,
            },
        },
    }
    config["token"] = sign_onlyoffice_payload(config, settings.onlyoffice_browser_secret)
    return config


def history_entry(version: DocumentVersion) -> dict[str, Any]:
    return {
        "created": version.created_at.strftime("%Y-%m-%d %I:%M %p"),
        "key": version.onlyoffice_key,
        "user": {
            "id": version.created_by.id if version.created_by else "system",
            "name": version.created_by.name if version.created_by else "System",
        },
        "version": version.version_number,
        "changes": version.history_json,
        "serverVersion": version.history_server_version,
    }


def history_data(version: DocumentVersion, public_url: str, document_id: str, previous_version: DocumentVersion | None) -> dict[str, Any]:
    settings = get_settings()
    payload: dict[str, Any] = {
        "fileType": "docx",
        "key": version.onlyoffice_key,
        "url": f"{public_url}/api/documents/{document_id}/versions/{version.version_number}/download",
        "version": version.version_number,
    }
    if version.changes_file_path:
        payload["changesUrl"] = f"{public_url}/api/documents/{document_id}/versions/{version.version_number}/changes"
    if previous_version is not None:
        payload["previous"] = {
            "fileType": "docx",
            "key": previous_version.onlyoffice_key,
            "url": f"{public_url}/api/documents/{document_id}/versions/{previous_version.version_number}/download",
        }
    payload["token"] = sign_onlyoffice_payload(payload, settings.onlyoffice_browser_secret)
    return payload


def build_command_service_payload(key: str, userdata: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    payload: dict[str, Any] = {"c": "forcesave", "key": key}
    if userdata:
        payload["userdata"] = userdata
    payload["token"] = sign_onlyoffice_payload(payload, settings.onlyoffice_inbox_secret)
    return payload


def trigger_forcesave(key: str, userdata: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            f"{settings.trimmed_document_server_url}/coauthoring/CommandService.ashx",
            json=build_command_service_payload(key, userdata),
        )
        response.raise_for_status()
        return response.json()
