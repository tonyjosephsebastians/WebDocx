from app.tests.conftest import auth_headers


def test_register_login_and_me(client):
    register = client.post(
        "/api/auth/register",
        json={
            "name": "Tony Editor",
            "email": "tony@example.com",
            "password": "supersecret",
            "workspace_name": "Tony Workspace",
        },
    )
    assert register.status_code == 201
    payload = register.json()
    assert payload["user"]["email"] == "tony@example.com"
    assert payload["user"]["workspaces"][0]["name"] == "Tony Workspace"

    login = client.post(
        "/api/auth/login",
        json={"email": "tony@example.com", "password": "supersecret"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["user"]["name"] == "Tony Editor"
