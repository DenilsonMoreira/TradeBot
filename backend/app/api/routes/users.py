import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin_csrf, require_admin_session
from app.config import settings
from app.core.security import OperatorSession, hash_password
from app.database import get_db
from app.models.user import User, UserInvitation
from app.models.audit import AuditEvent
from app.schemas.users import (
    InvitationComplete,
    InvitationCreate,
    InvitationPublicResponse,
    InvitationResponse,
    UserResponse,
)
from app.services.invitation_delivery_service import InvitationDeliveryError, InvitationDeliveryService


router = APIRouter(tags=["users"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _invitation_url(token: str) -> str:
    return f"{settings.public_web_url.rstrip('/')}?convite={token}"


def _destination(payload: InvitationCreate) -> str:
    return str(payload.email).lower() if payload.channel == "EMAIL" else payload.telegram_chat_id.strip()


def _mask_destination(channel: str, destination: str) -> str:
    if channel == "EMAIL":
        name, domain = destination.split("@", 1)
        return f"{name[:2]}***@{domain}"
    return f"***{destination[-4:]}"


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def _valid_document(kind: str, value: str) -> bool:
    digits = _digits(value)
    length = 11 if kind == "CPF" else 14
    if len(digits) != length or len(set(digits)) == 1:
        return False
    if kind == "CPF":
        for size in (9, 10):
            total = sum(int(digits[index]) * (size + 1 - index) for index in range(size))
            check = (total * 10 % 11) % 10
            if check != int(digits[size]):
                return False
        return True
    weights = ((5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2), (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    base = digits[:12]
    for weights_set in weights:
        total = sum(int(number) * weight for number, weight in zip(base, weights_set))
        check = 0 if total % 11 < 2 else 11 - total % 11
        base += str(check)
    return base == digits


def _document_fingerprint(value: str) -> str:
    return hmac.new(settings.auth_secret_key.encode(), _digits(value).encode(), hashlib.sha256).hexdigest()


def _audit(db: Session, actor: str, action: str, resource: str, resource_id: str, details: dict | None = None) -> None:
    db.add(AuditEvent(actor=actor, action=action, resource=resource, resource_id=resource_id, details=details or {}))


def _find_valid_invitation(db: Session, token: str) -> UserInvitation:
    invitation = db.scalar(select(UserInvitation).where(UserInvitation.token_hash == _token_hash(token)))
    if invitation is None or invitation.status != "PENDING" or invitation.expires_at <= _now():
        raise HTTPException(status_code=410, detail="Este convite é inválido, expirou ou já foi utilizado.")
    return invitation


async def _deliver(invitation: UserInvitation, token: str) -> None:
    try:
        await InvitationDeliveryService().send(invitation.channel, invitation.destination, _invitation_url(token))
        invitation.delivery_status = "SENT"
        invitation.delivery_error = None
    except InvitationDeliveryError as error:
        invitation.delivery_status = "MANUAL_REQUIRED"
        invitation.delivery_error = str(error)[:500]


@router.get("/admin/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), _: OperatorSession = Depends(require_admin_session)):
    return list(db.scalars(select(User).order_by(User.created_at.desc())).all())


@router.get("/admin/user-invitations", response_model=list[InvitationResponse])
def list_invitations(db: Session = Depends(get_db), _: OperatorSession = Depends(require_admin_session)):
    return list(db.scalars(select(UserInvitation).order_by(UserInvitation.created_at.desc())).all())


@router.post("/admin/user-invitations", response_model=InvitationResponse, status_code=201)
async def create_invitation(payload: InvitationCreate, db: Session = Depends(get_db), admin: OperatorSession = Depends(require_admin_csrf)):
    destination = _destination(payload)
    existing = db.scalar(select(UserInvitation).where(UserInvitation.destination == destination, UserInvitation.status == "PENDING", UserInvitation.expires_at > _now()))
    if existing:
        raise HTTPException(status_code=409, detail="Já existe um convite válido para esse destino.")
    if payload.channel == "EMAIL" and db.scalar(select(User).where(User.email == destination)):
        raise HTTPException(status_code=409, detail="Já existe um usuário com esse e-mail.")
    token = secrets.token_urlsafe(32)
    invitation = UserInvitation(
        invited_by=admin.email,
        channel=payload.channel,
        destination=destination,
        token_hash=_token_hash(token),
        expires_at=_now() + timedelta(hours=settings.user_invitation_hours),
    )
    db.add(invitation)
    db.flush()
    await _deliver(invitation, token)
    _audit(db, admin.email, "USER_INVITATION_CREATED", "user_invitation", invitation.id, {"channel": invitation.channel, "delivery_status": invitation.delivery_status})
    db.commit()
    db.refresh(invitation)
    response = InvitationResponse.model_validate(invitation)
    response.invitation_url = _invitation_url(token)
    return response


@router.post("/admin/user-invitations/{invitation_id}/resend", response_model=InvitationResponse)
async def resend_invitation(invitation_id: str, db: Session = Depends(get_db), admin: OperatorSession = Depends(require_admin_csrf)):
    invitation = db.get(UserInvitation, invitation_id)
    if invitation is None or invitation.status != "PENDING":
        raise HTTPException(status_code=404, detail="Convite pendente não encontrado.")
    token = secrets.token_urlsafe(32)
    invitation.token_hash = _token_hash(token)
    invitation.expires_at = _now() + timedelta(hours=settings.user_invitation_hours)
    await _deliver(invitation, token)
    _audit(db, admin.email, "USER_INVITATION_RESENT", "user_invitation", invitation.id, {"channel": invitation.channel, "delivery_status": invitation.delivery_status})
    db.commit()
    db.refresh(invitation)
    response = InvitationResponse.model_validate(invitation)
    response.invitation_url = _invitation_url(token)
    return response


@router.post("/admin/user-invitations/{invitation_id}/revoke", status_code=204)
def revoke_invitation(invitation_id: str, db: Session = Depends(get_db), admin: OperatorSession = Depends(require_admin_csrf)):
    invitation = db.get(UserInvitation, invitation_id)
    if invitation is None or invitation.status != "PENDING":
        raise HTTPException(status_code=404, detail="Convite pendente não encontrado.")
    invitation.status = "REVOKED"
    invitation.revoked_at = _now()
    _audit(db, admin.email, "USER_INVITATION_REVOKED", "user_invitation", invitation.id)
    db.commit()


@router.post("/admin/users/{user_id}/approve", response_model=UserResponse)
def approve_user(user_id: str, db: Session = Depends(get_db), admin: OperatorSession = Depends(require_admin_csrf)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    user.status = "ACTIVE"
    _audit(db, admin.email, "USER_APPROVED", "user", user.id)
    db.commit()
    db.refresh(user)
    return user


@router.get("/onboarding/invitations/{token}", response_model=InvitationPublicResponse)
def inspect_invitation(token: str, db: Session = Depends(get_db)):
    invitation = _find_valid_invitation(db, token)
    return InvitationPublicResponse(channel=invitation.channel, destination_hint=_mask_destination(invitation.channel, invitation.destination), expires_at=invitation.expires_at)


@router.post("/onboarding/invitations/{token}/complete", response_model=UserResponse, status_code=201)
def complete_invitation(token: str, payload: InvitationComplete, db: Session = Depends(get_db)):
    invitation = _find_valid_invitation(db, token)
    if not _valid_document(payload.document_type, payload.document_number):
        raise HTTPException(status_code=422, detail=f"{payload.document_type} inválido.")
    email = invitation.destination if invitation.channel == "EMAIL" else (str(payload.email).lower() if payload.email else None)
    if not email:
        raise HTTPException(status_code=422, detail="Informe um e-mail para acessar sua conta.")
    if db.scalar(select(User).where(or_(User.email == email, User.document_fingerprint == _document_fingerprint(payload.document_number)))):
        raise HTTPException(status_code=409, detail="Já existe um cadastro com esse e-mail ou documento.")
    user = User(
        full_name=payload.full_name.strip(),
        email=email,
        telegram_chat_id=invitation.destination if invitation.channel == "TELEGRAM" else None,
        phone=payload.phone.strip(),
        document_type=payload.document_type,
        document_fingerprint=_document_fingerprint(payload.document_number),
        document_last4=_digits(payload.document_number)[-4:],
        password_hash=hash_password(payload.password),
        terms_accepted=True,
        terms_accepted_at=_now(),
    )
    db.add(user)
    db.flush()
    invitation.status = "ACCEPTED"
    invitation.accepted_at = _now()
    invitation.user_id = user.id
    _audit(db, email, "USER_REGISTRATION_COMPLETED", "user", user.id, {"channel": invitation.channel})
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cadastro já existente.") from error
    db.refresh(user)
    return user
