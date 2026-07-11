import base64
import getpass
import secrets
import sys
from pathlib import Path
from urllib.parse import quote, urlencode

import qrcode

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password


def build_totp_uri(email: str, secret: str) -> str:
    label = quote(f"TradeBrain:{email}", safe="")
    query = urlencode({
        "secret": secret,
        "issuer": "TradeBrain",
        "algorithm": "SHA1",
        "digits": 6,
        "period": 30,
    })
    return f"otpauth://totp/{label}?{query}"


def main() -> None:
    email = input("E-mail do operador: ").strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise SystemExit("Informe um e-mail válido para o operador.")
    password = getpass.getpass("Nova senha do operador (mínimo 12 caracteres): ")
    if len(password) < 12:
        raise SystemExit("A senha precisa ter no mínimo 12 caracteres.")
    totp_secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")
    qr_path = Path(__file__).resolve().parent / "tradebrain-authenticator.png"
    qrcode.make(build_totp_uri(email, totp_secret)).save(qr_path)

    print(f"AUTH_OPERATOR_EMAIL={email}")
    print(f"AUTH_SECRET_KEY={secrets.token_urlsafe(48)}")
    # O Compose interpola "$VAR" até mesmo em valores do env_file. Emitir "$$"
    # preserva os separadores literais do formato PBKDF2 dentro do contêiner.
    compose_password_hash = hash_password(password).replace("$", "$$")
    print(f"AUTH_PASSWORD_HASH={compose_password_hash}")
    print(f"AUTH_TOTP_SECRET={totp_secret}")
    print(f"QR Code salvo em: {qr_path}")
    print("Abra a imagem e escaneie no aplicativo autenticador. Apague-a após o cadastro.")


if __name__ == "__main__":
    main()
