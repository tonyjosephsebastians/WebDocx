from __future__ import annotations

import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient


def _purge_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name, None)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("APP_STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret-key-1234567890-1234567890")
    monkeypatch.setenv("APP_ONLYOFFICE_BROWSER_SECRET", "browser-secret-1234567890-1234567890")
    monkeypatch.setenv("APP_ONLYOFFICE_INBOX_SECRET", "inbox-secret-1234567890-1234567890")
    monkeypatch.setenv("APP_ONLYOFFICE_OUTBOX_SECRET", "outbox-secret-1234567890-1234567890")
    monkeypatch.setenv("APP_PUBLIC_URL", "http://testserver")
    monkeypatch.setenv("APP_ONLYOFFICE_DOCUMENT_SERVER_URL", "http://documentserver")

    _purge_app_modules()
    app_main = importlib.import_module("app.main")

    with TestClient(app_main.app) as test_client:
        yield test_client


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
