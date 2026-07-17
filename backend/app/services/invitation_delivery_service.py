import asyncio
import smtplib
from email.message import EmailMessage

import httpx

from app.config import settings


class InvitationDeliveryError(RuntimeError):
    pass


class InvitationDeliveryService:
    async def send(self, channel: str, destination: str, invitation_url: str) -> None:
        if channel == "EMAIL":
            await asyncio.to_thread(self._send_email, destination, invitation_url)
            return
        if channel == "TELEGRAM":
            await self._send_telegram(destination, invitation_url)
            return
        raise InvitationDeliveryError("Canal de convite não suportado.")

    def _send_email(self, destination: str, invitation_url: str) -> None:
        if not settings.smtp_host or not settings.smtp_from_email:
            raise InvitationDeliveryError("Envio de e-mail ainda não configurado no servidor.")
        message = EmailMessage()
        message["Subject"] = "Seu convite para o TradeBrain"
        message["From"] = settings.smtp_from_email
        message["To"] = destination
        message.set_content(
            "Você foi convidado para o TradeBrain.\n\n"
            f"Conclua seu cadastro neste link: {invitation_url}\n\n"
            "O link é pessoal, expira e pode ser usado somente uma vez."
        )
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                if settings.smtp_use_tls:
                    smtp.starttls()
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as error:
            raise InvitationDeliveryError(f"Falha no envio por e-mail: {error}") from error

    async def _send_telegram(self, chat_id: str, invitation_url: str) -> None:
        if not settings.telegram_bot_token:
            raise InvitationDeliveryError("Bot do Telegram ainda não configurado no servidor.")
        message = (
            "Você foi convidado para o TradeBrain.\n\n"
            f"Conclua seu cadastro: {invitation_url}\n\n"
            "O link é pessoal, expira e pode ser usado somente uma vez."
        )
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
                )
                response.raise_for_status()
                if not response.json().get("ok"):
                    raise InvitationDeliveryError("O Telegram recusou o envio do convite.")
        except httpx.HTTPError as error:
            raise InvitationDeliveryError(f"Falha no envio pelo Telegram: {error}") from error
