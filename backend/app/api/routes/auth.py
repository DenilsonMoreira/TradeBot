import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.config import settings
from app.core.rate_limit import LoginRateLimiter
from app.core.security import create_session, verify_password, verify_totp
from app.schemas.auth import LoginRequest, NativeSessionResponse, SessionResponse


router = APIRouter(prefix="/auth", tags=["authentication"])
COOKIE_NAME = "tradebrain_session"
login_rate_limiter = LoginRateLimiter(
    max_attempts=settings.auth_max_attempts,
    window_seconds=settings.auth_attempt_window_seconds,
    lockout_seconds=settings.auth_lockout_seconds,
)


def auth_is_configured() -> bool:
    return all((settings.auth_secret_key, settings.auth_operator_email, settings.auth_password_hash, settings.auth_totp_secret))


def _rate_limit_key(payload: LoginRequest, request: Request) -> str:
    client_ip = request.client.host if request.client else "unknown"
    identity = f"{client_ip}|{payload.email.strip().lower()}".encode()
    return hmac.new(settings.auth_secret_key.encode(), identity, hashlib.sha256).hexdigest()


def _raise_rate_limit(retry_after: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Muitas tentativas de acesso. Aguarde antes de tentar novamente.",
        headers={"Retry-After": str(retry_after)},
    )


def authenticate(payload: LoginRequest, request: Request):
    if not auth_is_configured():
        raise HTTPException(status_code=503, detail="Autenticação do operador não configurada.")
    rate_limit_key = _rate_limit_key(payload, request)
    retry_after = login_rate_limiter.retry_after(rate_limit_key)
    if retry_after:
        _raise_rate_limit(retry_after)
    email_ok = hmac.compare_digest(payload.email.lower(), settings.auth_operator_email.lower())
    password_ok = verify_password(payload.password, settings.auth_password_hash)
    totp_ok = verify_totp(settings.auth_totp_secret, payload.totp_code)
    if not (email_ok and password_ok and totp_ok):
        retry_after = login_rate_limiter.register_failure(rate_limit_key)
        if retry_after:
            _raise_rate_limit(retry_after)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")
    login_rate_limiter.register_success(rate_limit_key)
    return create_session(payload.email.lower(), settings.auth_secret_key, settings.auth_session_minutes)


@router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest, request: Request, response: Response) -> SessionResponse:
    token, session = authenticate(payload, request)
    response.set_cookie(
        COOKIE_NAME, token, max_age=settings.auth_session_minutes * 60,
        httponly=True, secure=settings.auth_cookie_secure, samesite="strict", path="/",
    )
    return SessionResponse(email=session.email, csrf_token=session.csrf_token)


@router.post("/mobile-login", response_model=NativeSessionResponse)
def mobile_login(payload: LoginRequest, request: Request) -> NativeSessionResponse:
    token, session = authenticate(payload, request)
    return NativeSessionResponse(
        email=session.email,
        csrf_token=session.csrf_token,
        session_token=token,
    )


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", secure=settings.auth_cookie_secure, samesite="strict")


@router.get("/session", response_model=SessionResponse)
def session(request: Request) -> SessionResponse:
    from app.api.dependencies import get_operator_session
    current = get_operator_session(request)
    return SessionResponse(email=current.email, csrf_token=current.csrf_token)
