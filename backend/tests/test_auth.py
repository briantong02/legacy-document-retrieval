from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.main import app


def test_auth_me_returns_current_user() -> None:
    app.dependency_overrides[get_current_user] = lambda: type(
        "User",
        (),
        {
            "username": "test.user@dux.local",
            "display_name": "Test User",
            "email": "test.user@dux.local",
            "groups": ["group-1"],
        },
    )()

    try:
        client = TestClient(app)
        response = client.get("/api/auth/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["username"] == "test.user@dux.local"
    assert payload["data"]["displayName"] == "Test User"
    assert payload["data"]["groups"] == ["group-1"]
