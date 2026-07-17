from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    totp_code: str = Field(default="", pattern=r"^(|\d{6})$")


class SessionResponse(BaseModel):
    authenticated: bool = True
    email: EmailStr
    csrf_token: str
    role: str = "ADMIN"


class NativeSessionResponse(SessionResponse):
    session_token: str
