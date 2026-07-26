from starlette.testclient import TestClient
from app.main import app
from app.core.security import create_access_token, is_token_revoked, revoke_token

client = TestClient(app)


def test_token_revocation_helper():
    token = create_access_token({"sub": "123", "role": "student", "jti": "test-jti-123"}, expires_delta=15)
    payload = {"sub": "123", "role": "student", "jti": "test-jti-123", "exp": 9999999999}
    
    assert is_token_revoked(token, payload) is False
    
    revoke_token(token, payload)
    
    assert is_token_revoked(token, payload) is True


def test_logout_endpoint_revokes_token():
    token = create_access_token({"sub": "999", "phone": "+919999999999", "role": "student"}, expires_delta=15)
    
    # Verify token is valid before logout
    headers = {"Authorization": f"Bearer {token}"}
    res_before = client.get("/v1/users/me", headers=headers)
    # Token works (or user not found 404, but NOT 401 token revoked)
    assert res_before.status_code != 401 or res_before.json().get("detail") != "Token has been revoked"

    # Logout
    logout_res = client.post("/v1/auth/logout", json={"refresh_token": "dummy"}, headers=headers)
    assert logout_res.status_code == 200

    # Token is now revoked
    res_after = client.get("/v1/users/me", headers=headers)
    assert res_after.status_code == 401
    assert res_after.json()["detail"] == "Token has been revoked"
