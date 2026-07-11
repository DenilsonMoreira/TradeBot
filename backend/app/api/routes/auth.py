import hmac

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.config import settings
from app.core.security import create_session, verify_password, verify_totp
from app.schemas.auth import LoginRequest, SessionResponse


router = APIRouter(prefix="/auth", tags=["authentication"])
COOKIE_NAME = "tradebrain_session"


def auth_is_configured() -> bool:
    return all((settings.auth_secret_key, settings.auth_operator_email, settings.auth_password_hash, settings.auth_totp_secret))


@router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest, response: Response) -> SessionResponse:
    if not auth_is_configured():
        raise HTTPException(status_code=503, detail="Autenticação do operador não configurada.")
    email_ok = hmac.compare_digest(payload.email.lower(), settings.auth_operator_email.lower())
    password_ok = verify_password(payload.password, settings.auth_password_hash)
    totp_ok = verify_totp(settings.auth_totp_secret, payload.totp_code)
    if not (email_ok and password_ok and totp_ok):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")
    token, session = create_session(payload.email.lower(), settings.auth_secret_key, settings.auth_session_minutes)
    response.set_cookie(
        COOKIE_NAME, token, max_age=settings.auth_session_minutes * 60,
        httponly=True, secure=settings.auth_cookie_secure, samesite="strict", path="/",
    )
    return SessionResponse(email=session.email, csrf_token=session.csrf_token)


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", secure=settings.auth_cookie_secure, samesite="strict")


@router.get("/session", response_model=SessionResponse)
def session(request: Request) -> SessionResponse:
    from app.api.dependencies import get_operator_session
    current = get_operator_session(request)
    return SessionResponse(email=current.email, csrf_token=current.csrf_token)
