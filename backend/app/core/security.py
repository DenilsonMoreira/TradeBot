import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
from dataclasses import dataclass


PASSWORD_ITERATIONS = 600_000


@dataclass(frozen=True)
class OperatorSession:
    email: str
    csrf_token: str
    expires_at: int
    role: str = "ADMIN"


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    actual_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), actual_salt, PASSWORD_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        base64.urlsafe_b64encode(actual_salt).decode().rstrip("="),
        base64.urlsafe_b64encode(digest).decode().rstrip("="),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), _decode(salt), int(iterations)
        )
        return hmac.compare_digest(actual, _decode(expected))
    except (ValueError, TypeError):
        return False


def verify_totp(secret: str, code: str, *, now: int | None = None) -> bool:
    if not code.isdigit() or len(code) != 6:
        return False
    timestamp = int(time.time() if now is None else now)
    try:
        key = base64.b32decode(secret.upper().replace(" ", ""), casefold=True)
    except Exception:
        return False
    for drift in (-1, 0, 1):
        counter = timestamp // 30 + drift
        digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        value = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
        if hmac.compare_digest(f"{value:06d}", code):
            return True
    return False


def create_session(email: str, secret_key: str, ttl_minutes: int, *, role: str = "ADMIN") -> tuple[str, OperatorSession]:
    session = OperatorSession(
        email=email,
        csrf_token=secrets.token_urlsafe(24),
        expires_at=int(time.time()) + ttl_minutes * 60,
        role=role,
    )
    payload = _encode(json.dumps(session.__dict__, separators=(",", ":")).encode())
    signature = _encode(hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}", session


def read_session(token: str, secret_key: str, *, now: int | None = None) -> OperatorSession | None:
    try:
        payload, signature = token.split(".", 1)
        expected = _encode(hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(_decode(payload))
        session = OperatorSession(**data)
        if session.expires_at <= int(time.time() if now is None else now):
            return None
        return session
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
