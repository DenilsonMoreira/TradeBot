import base64
import hashlib
import hmac
import struct

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import require_operator_csrf
from app.api.routes.auth import login_rate_limiter, router
from app.config import settings
from app.core.rate_limit import LoginRateLimiter
from app.core.security import create_session, hash_password, read_session, verify_password, verify_totp


def test_password_hash_roundtrip() -> None:
    encoded = hash_password("uma-senha-realmente-forte", salt=b"0123456789abcdef")
    assert verify_password("uma-senha-realmente-forte", encoded)
    assert not verify_password("senha-errada", encoded)


def test_signed_session_rejects_tampering_and_expiration() -> None:
    token, session = create_session("operator@example.com", "secret", 30)
    assert read_session(token, "secret").email == session.email
    assert read_session(token + "x", "secret") is None
    assert read_session(token, "secret", now=session.expires_at) is None


def test_totp_accepts_current_code() -> None:
    secret = "JBSWY3DPEHPK3PXP"
    now = 1_700_000_000
    key = base64.b32decode(secret)
    counter = now // 30
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 15
    code = f"{(struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff) % 1_000_000:06d}"
    assert verify_totp(secret, code, now=now)
    assert not verify_totp(secret, "000000", now=now)


def _current_totp(secret: str) -> str:
    import time
    key = base64.b32decode(secret)
    digest = hmac.new(key, struct.pack(">Q", int(time.time()) // 30), hashlib.sha1).digest()
    offset = digest[-1] & 15
    return f"{(struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff) % 1_000_000:06d}"


def test_login_cookie_session_and_csrf(monkeypatch) -> None:
    secret = "JBSWY3DPEHPK3PXP"
    monkeypatch.setattr(settings, "auth_secret_key", "session-secret")
    monkeypatch.setattr(settings, "auth_operator_email", "operator@example.com")
    monkeypatch.setattr(settings, "auth_password_hash", hash_password("uma-senha-realmente-forte"))
    monkeypatch.setattr(settings, "auth_totp_secret", secret)

    test_app = FastAPI()
    test_app.include_router(router)

    @test_app.post("/protected")
    def protected(_session=Depends(require_operator_csrf)):
        return {"ok": True}

    with TestClient(test_app) as client:
        response = client.post("/auth/login", json={
            "email": "operator@example.com",
            "password": "uma-senha-realmente-forte",
            "totp_code": _current_totp(secret),
        })
        assert response.status_code == 200
        csrf = response.json()["csrf_token"]
        assert "HttpOnly" in response.headers["set-cookie"]
        assert client.get("/auth/session").status_code == 200
        assert client.post("/protected").status_code == 403
        assert client.post("/protected", headers={"X-CSRF-Token": csrf}).json() == {"ok": True}


def test_login_rejects_invalid_credentials(monkeypatch) -> None:
    login_rate_limiter.reset()
    monkeypatch.setattr(settings, "auth_secret_key", "session-secret")
    monkeypatch.setattr(settings, "auth_operator_email", "operator@example.com")
    monkeypatch.setattr(settings, "auth_password_hash", hash_password("uma-senha-realmente-forte"))
    monkeypatch.setattr(settings, "auth_totp_secret", "JBSWY3DPEHPK3PXP")
    test_app = FastAPI()
    test_app.include_router(router)
    with TestClient(test_app) as client:
        response = client.post("/auth/login", json={
            "email": "operator@example.com",
            "password": "senha-incorreta-123",
            "totp_code": "123456",
        })
    assert response.status_code == 401


def test_login_blocks_repeated_invalid_credentials(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_secret_key", "session-secret")
    monkeypatch.setattr(settings, "auth_operator_email", "operator@example.com")
    monkeypatch.setattr(settings, "auth_password_hash", hash_password("uma-senha-realmente-forte"))
    monkeypatch.setattr(settings, "auth_totp_secret", "JBSWY3DPEHPK3PXP")
    login_rate_limiter.reset()
    test_app = FastAPI()
    test_app.include_router(router)
    payload = {
        "email": "operator@example.com",
        "password": "senha-incorreta-123",
        "totp_code": "123456",
    }

    with TestClient(test_app) as client:
        responses = [client.post("/auth/login", json=payload) for _ in range(settings.auth_max_attempts)]
        blocked = client.post("/auth/login", json=payload)

    assert [response.status_code for response in responses[:-1]] == [401] * (settings.auth_max_attempts - 1)
    assert responses[-1].status_code == 429
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    login_rate_limiter.reset()


def test_rate_limiter_expires_lockout() -> None:
    now = [100.0]
    limiter = LoginRateLimiter(2, 60, 30, clock=lambda: now[0])
    assert limiter.register_failure("opaque") == 0
    assert limiter.register_failure("opaque") == 30
    assert limiter.retry_after("opaque") == 30
    now[0] += 31
    assert limiter.retry_after("opaque") == 0


def test_mobile_login_returns_bearer_session(monkeypatch) -> None:
    secret = "JBSWY3DPEHPK3PXP"
    monkeypatch.setattr(settings, "auth_secret_key", "session-secret")
    monkeypatch.setattr(settings, "auth_operator_email", "operator@example.com")
    monkeypatch.setattr(settings, "auth_password_hash", hash_password("uma-senha-realmente-forte"))
    monkeypatch.setattr(settings, "auth_totp_secret", secret)
    test_app = FastAPI()
    test_app.include_router(router)
    with TestClient(test_app) as client:
        login = client.post("/auth/mobile-login", json={
            "email": "operator@example.com",
            "password": "uma-senha-realmente-forte",
            "totp_code": _current_totp(secret),
        })
        token = login.json()["session_token"]
        session = client.get("/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert login.status_code == 200
    assert "tradebrain_session" not in login.cookies
    assert session.status_code == 200
