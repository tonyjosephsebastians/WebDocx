from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import uuid

import httpx
from fastapi import UploadFile

from app.core.config import get_settings


DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class FilesystemStorage:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.root = self.settings.resolved_storage_root
        self.root.mkdir(parents=True, exist_ok=True)

    def _target_path(self, suffix: str) -> Path:
        segment = uuid.uuid4().hex
        directory = self.root / segment[:2] / segment[2:4]
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{segment}{suffix}"

    def _write_bytes(self, payload: bytes, file_name: str, content_type: str) -> dict:
        suffix = Path(file_name).suffix or ".docx"
        target = self._target_path(suffix)
        target.write_bytes(payload)
        return {
            "path": str(target.relative_to(self.root)),
            "checksum": sha256(payload).hexdigest(),
            "size_bytes": len(payload),
            "content_type": content_type,
            "original_file_name": file_name,
        }

    async def store_upload(self, upload: UploadFile, file_name: str | None = None) -> dict:
        payload = await upload.read()
        final_name = file_name or upload.filename or "document.docx"
        return self._write_bytes(payload, final_name, upload.content_type or DOCX_CONTENT_TYPE)

    def store_bytes(self, payload: bytes, file_name: str, content_type: str = DOCX_CONTENT_TYPE) -> dict:
        return self._write_bytes(payload, file_name, content_type)

    def download_remote_file(self, url: str) -> bytes:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.content

    def copy_existing(self, relative_path: str, file_name: str, content_type: str = DOCX_CONTENT_TYPE) -> dict:
        path = self.resolve(relative_path)
        return self._write_bytes(path.read_bytes(), file_name, content_type)

    def resolve(self, relative_path: str) -> Path:
        return self.root / relative_path

    def save_remote_artifact(self, url: str, file_name: str, content_type: str = "application/octet-stream") -> str:
        payload = self.download_remote_file(url)
        metadata = self._write_bytes(payload, file_name, content_type)
        return metadata["path"]


storage = FilesystemStorage()
