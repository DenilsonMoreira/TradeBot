import base64
import getpass
import secrets

from app.core.security import hash_password


def main() -> None:
    password = getpass.getpass("Nova senha do operador (mínimo 12 caracteres): ")
    if len(password) < 12:
        raise SystemExit("A senha precisa ter no mínimo 12 caracteres.")
    print(f"AUTH_SECRET_KEY={secrets.token_urlsafe(48)}")
    print(f"AUTH_PASSWORD_HASH={hash_password(password)}")
    print(f"AUTH_TOTP_SECRET={base64.b32encode(secrets.token_bytes(20)).decode().rstrip('=')}")


if __name__ == "__main__":
    main()
