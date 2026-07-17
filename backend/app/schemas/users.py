from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator


class InvitationCreate(BaseModel):
    channel: Literal["EMAIL", "TELEGRAM"]
    email: EmailStr | None = None
    telegram_chat_id: str | None = Field(default=None, min_length=2, max_length=64)

    @model_validator(mode="after")
    def validate_destination(self):
        if self.channel == "EMAIL" and not self.email:
            raise ValueError("Informe o e-mail do convidado.")
        if self.channel == "TELEGRAM" and not self.telegram_chat_id:
            raise ValueError("Informe o ID do chat do Telegram.")
        return self


class InvitationResponse(BaseModel):
    id: str
    channel: str
    destination: str
    status: str
    delivery_status: str
    delivery_error: str | None
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime
    invitation_url: str | None = None

    model_config = {"from_attributes": True}


class InvitationPublicResponse(BaseModel):
    channel: str
    destination_hint: str
    expires_at: datetime


class InvitationComplete(BaseModel):
    full_name: str = Field(min_length=3, max_length=160)
    email: EmailStr | None = None
    phone: str = Field(min_length=8, max_length=32)
    document_type: Literal["CPF", "CNPJ"]
    document_number: str = Field(min_length=11, max_length=24)
    password: str = Field(min_length=12, max_length=256)
    terms_accepted: Literal[True]


class UserResponse(BaseModel):
    id: str
    full_name: str
    email: EmailStr | None
    telegram_chat_id: str | None
    phone: str | None
    document_type: str
    document_last4: str
    role: str
    status: str
    terms_accepted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
