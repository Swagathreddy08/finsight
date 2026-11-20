from fastapi.testclient import TestClient


def test_registration_login_and_current_user(client: TestClient) -> None:
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "alex@example.com",
            "full_name": "Alex Example",
            "password": "a-secure-password",
        },
    )
    assert registration.status_code == 201
    registration_data = registration.json()
    assert registration_data["token_type"] == "bearer"
    assert registration_data["user"]["email"] == "alex@example.com"
    assert "refresh_token" not in registration_data
    cookie = registration.cookies.get("finsight_refresh")
    assert cookie is not None
    assert "httponly" in registration.headers["set-cookie"].lower()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "alex@example.com", "password": "a-secure-password"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["full_name"] == "Alex Example"


def test_duplicate_registration_is_rejected(client: TestClient) -> None:
    payload = {
        "email": "alex@example.com",
        "full_name": "Alex Example",
        "password": "a-secure-password",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    duplicate = client.post("/api/v1/auth/register", json=payload)
    assert duplicate.status_code == 409


def test_invalid_login_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_production_auth_rejects_untrusted_origins_and_sets_secure_cookie(
    client: TestClient,
    monkeypatch,
) -> None:
    from app.api.v1.endpoints import auth

    monkeypatch.setattr(auth.settings, "app_env", "production")
    monkeypatch.setattr(auth.settings, "frontend_url", "https://finsight.example")
    monkeypatch.setattr(auth.settings, "secure_cookies", True)
    payload = {
        "email": "origin@example.com",
        "full_name": "Origin Example",
        "password": "a-secure-password",
    }

    denied = client.post(
        "/api/v1/auth/register",
        json=payload,
        headers={"Origin": "https://untrusted.example"},
    )
    assert denied.status_code == 403

    accepted = client.post(
        "/api/v1/auth/register",
        json=payload,
        headers={"Origin": "https://finsight.example"},
    )
    assert accepted.status_code == 201
    assert "secure" in accepted.headers["set-cookie"].lower()


def test_refresh_rotates_tokens_and_logout_revokes_the_session(client: TestClient) -> None:
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@example.com",
            "full_name": "Refresh Example",
            "password": "a-secure-password",
        },
    )
    initial = registration.json()
    initial_cookie = registration.cookies.get("finsight_refresh")
    assert initial_cookie is not None

    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    rotated = refreshed.json()
    assert "refresh_token" not in rotated
    rotated_cookie = refreshed.cookies.get("finsight_refresh")
    assert rotated_cookie is not None
    assert rotated_cookie != initial_cookie
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {rotated['access_token']}"},
    ).status_code == 200

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    assert "max-age=0" in logout.headers["set-cookie"].lower()
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {rotated['access_token']}"},
    ).status_code == 401
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_reusing_a_rotated_refresh_token_revokes_its_session(client: TestClient) -> None:
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "replay@example.com",
            "full_name": "Replay Example",
            "password": "a-secure-password",
        },
    )
    initial = registration.json()
    initial_cookie = registration.cookies.get("finsight_refresh")
    assert initial_cookie is not None
    rotated_response = client.post("/api/v1/auth/refresh")
    assert rotated_response.status_code == 200
    rotated = rotated_response.json()
    rotated_cookie = rotated_response.cookies.get("finsight_refresh")
    assert rotated_cookie is not None

    client.cookies.set("finsight_refresh", initial_cookie)
    replay = client.post(
        "/api/v1/auth/refresh",
    )
    assert replay.status_code == 401
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {rotated['access_token']}"},
    ).status_code == 401
    client.cookies.set("finsight_refresh", rotated_cookie)
    assert client.post(
        "/api/v1/auth/refresh",
    ).status_code == 401
