from sqlalchemy import delete
from fastapi.testclient import TestClient

from app.api.main import app
from app.database import SessionLocal
from app.models.user import User, UserInvitation
from app.config import settings


def _clean_users() -> None:
    with SessionLocal() as db:
        db.execute(delete(UserInvitation))
        db.execute(delete(User))
        db.commit()


def test_admin_invitation_onboarding_and_approval(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_secret_key", "test-session-secret")
    monkeypatch.setattr(settings, "auth_operator_email", "operator@example.com")
    monkeypatch.setattr(settings, "auth_password_hash", "configured-for-test")
    monkeypatch.setattr(settings, "auth_totp_secret", "JBSWY3DPEHPK3PXP")
    _clean_users()
    with TestClient(app) as client:
        created = client.post("/admin/user-invitations", json={"channel": "EMAIL", "email": "convidado@example.com"})
        assert created.status_code == 201
        invitation = created.json()
        assert invitation["delivery_status"] == "MANUAL_REQUIRED"
        token = invitation["invitation_url"].split("convite=", 1)[1]

        inspected = client.get(f"/onboarding/invitations/{token}")
        assert inspected.status_code == 200
        assert inspected.json()["destination_hint"] == "co***@example.com"

        completed = client.post(f"/onboarding/invitations/{token}/complete", json={
            "full_name": "Usuário Convidado",
            "phone": "85999999999",
            "document_type": "CPF",
            "document_number": "529.982.247-25",
            "password": "uma-senha-segura-123",
            "terms_accepted": True,
        })
        assert completed.status_code == 201
        assert completed.json()["status"] == "PENDING_APPROVAL"
        assert completed.json()["document_last4"] == "4725"

        reused = client.get(f"/onboarding/invitations/{token}")
        assert reused.status_code == 410

        approved = client.post(f"/admin/users/{completed.json()['id']}/approve")
        assert approved.status_code == 200
        assert approved.json()["status"] == "ACTIVE"

        login = client.post("/auth/login", json={
            "email": "convidado@example.com",
            "password": "uma-senha-segura-123",
            "totp_code": "",
        })
        assert login.status_code == 200
        assert login.json()["role"] == "MEMBER"
        assert client.get("/auth/session").json()["role"] == "MEMBER"
    _clean_users()


def test_onboarding_rejects_invalid_document() -> None:
    _clean_users()
    with TestClient(app) as client:
        invitation = client.post("/admin/user-invitations", json={"channel": "EMAIL", "email": "invalido@example.com"}).json()
        token = invitation["invitation_url"].split("convite=", 1)[1]
        response = client.post(f"/onboarding/invitations/{token}/complete", json={
            "full_name": "Documento Inválido",
            "phone": "85999999999",
            "document_type": "CPF",
            "document_number": "111.111.111-11",
            "password": "uma-senha-segura-123",
            "terms_accepted": True,
        })
        assert response.status_code == 422
        assert response.json()["detail"] == "CPF inválido."
    _clean_users()
