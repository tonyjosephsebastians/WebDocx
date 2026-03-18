import importlib

from app.tests.conftest import auth_headers


def _register(client, name: str, email: str):
    response = client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": "supersecret"},
    )
    assert response.status_code == 201
    return response.json()


def test_document_share_compare_and_restore(client):
    owner = _register(client, "Owner User", "owner@example.com")
    collaborator = _register(client, "Reviewer User", "reviewer@example.com")
    owner_token = owner["access_token"]

    first = client.post(
        "/api/documents",
        headers=auth_headers(owner_token),
        data={"title": "Master Draft", "workspace_id": owner["user"]["workspaces"][0]["id"]},
    )
    second = client.post(
        "/api/documents",
        headers=auth_headers(owner_token),
        data={"title": "Revised Draft", "workspace_id": owner["user"]["workspaces"][0]["id"]},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    first_id = first.json()["document"]["id"]
    second_id = second.json()["document"]["id"]

    share = client.post(
        f"/api/documents/{first_id}/share",
        headers=auth_headers(owner_token),
        json={"email": collaborator["user"]["email"], "role": "reviewer"},
    )
    assert share.status_code == 200
    assert share.json()["share_grants"][0]["role"] == "reviewer"

    comparison = client.post(
        f"/api/documents/{first_id}/compare",
        headers=auth_headers(owner_token),
        json={"revised_document_id": second_id},
    )
    assert comparison.status_code == 201
    comparison_document = comparison.json()["document"]
    assert comparison_document["kind"] == "comparison"
    assert comparison_document["comparison"]["original_document_id"] == first_id
    assert comparison_document["comparison"]["revised_document_id"] == second_id

    history_before = client.get(f"/api/documents/{first_id}/history", headers=auth_headers(owner_token))
    assert history_before.status_code == 200
    assert history_before.json()["versions"][0]["version_number"] == 1

    restore = client.post(f"/api/documents/{first_id}/history/1/restore", headers=auth_headers(owner_token))
    assert restore.status_code == 200
    assert restore.json()["document"]["latest_version_number"] == 2


def test_onlyoffice_callback_persists_versions(client, monkeypatch):
    registration = _register(client, "Callback User", "callback@example.com")
    token = registration["access_token"]
    document_response = client.post(
        "/api/documents",
        headers=auth_headers(token),
        data={"title": "Callback Draft", "workspace_id": registration["user"]["workspaces"][0]["id"]},
    )
    document = document_response.json()["document"]

    config_response = client.post(
        f"/api/documents/{document['id']}/editor-config?mode=edit",
        headers=auth_headers(token),
    )
    assert config_response.status_code == 200
    key = config_response.json()["config"]["document"]["key"]

    storage_module = importlib.import_module("app.services.storage")
    security_module = importlib.import_module("app.core.security")

    monkeypatch.setattr(
        storage_module.storage,
        "download_remote_file",
        lambda url: b"updated-docx-binary",
    )

    callback_token = security_module.sign_onlyoffice_payload({"key": key}, "outbox-secret-1234567890-1234567890")
    callback = client.post(
        f"/api/onlyoffice/callback?document_id={document['id']}",
        headers={"Authorization": f"Bearer {callback_token}"},
        json={
            "key": key,
            "status": 2,
            "url": "http://documentserver/download.docx",
            "changesurl": "http://documentserver/changes.zip",
            "history": {"changes": {"server": "value"}, "serverVersion": 3},
            "users": [registration["user"]["id"]],
        },
    )
    assert callback.status_code == 200
    assert callback.json() == {"error": 0}

    refreshed = client.get(f"/api/documents/{document['id']}", headers=auth_headers(token))
    assert refreshed.status_code == 200
    versions = refreshed.json()["versions"]
    assert versions[0]["version_number"] == 2
    assert versions[0]["history_server_version"] == 3
