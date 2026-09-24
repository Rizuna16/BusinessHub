"""
Email abstraction layer for BusinessHub.

Provides a pluggable email sending interface.
Production uses Resend adapter.
Testing uses FakeEmailProvider.
"""
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("email")


class AbstractEmailProvider(ABC):
    @abstractmethod
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """Send an email. Returns True on success, False on failure."""
        pass


class ResendEmailProvider(AbstractEmailProvider):
    """Production email provider using Resend API."""

    def __init__(self, api_key: str, from_email: str):
        self.api_key = api_key
        self.from_email = from_email

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        try:
            import resend

            resend.api_key = self.api_key
            params: resend.Emails.SendParams = {
                "from": self.from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
                "text": text_body,
            }
            resend.Emails.send(params)
            return True
        except Exception as e:
            logger.error(f"Email delivery failed to {to_email}: {type(e).__name__}")
            return False


class FakeEmailProvider(AbstractEmailProvider):
    """Test fake that records sent emails without delivering."""

    def __init__(self):
        self.sent: list[dict] = []

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        self.sent.append({
            "to": to_email,
            "subject": subject,
            "html": html_body,
            "text": text_body,
        })
        return True


class NoOpEmailProvider(AbstractEmailProvider):
    """Silently discards all emails. For development when Resend is not configured."""

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        logger.info(f"[NoOp Email] To: {to_email} | Subject: {subject}")
        return True


def get_email_provider() -> AbstractEmailProvider:
    """Factory: returns configured email provider."""
    from app.core.config import settings

    if settings.resend_api_key:
        return ResendEmailProvider(
            api_key=settings.resend_api_key,
            from_email=settings.email_from,
        )
    return NoOpEmailProvider()


def build_password_reset_email(
    reset_url: str,
    expires_minutes: int,
) -> tuple[str, str, str]:
    """Build password reset email content. Returns (subject, html, text)."""
    subject = "BusinessHub — Reset Password"
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1e293b;">BusinessHub</h2>
        <p>Anda telah meminta reset password untuk akun BusinessHub Anda.</p>
        <p>Klik link di bawah untuk membuat password baru:</p>
        <p style="margin: 24px 0;">
            <a href="{reset_url}"
               style="background-color: #3b82f6; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 6px; font-weight: bold;">
                Reset Password
            </a>
        </p>
        <p style="color: #64748b; font-size: 14px;">
            Link ini berlaku selama {expires_minutes} menit.
            Jika Anda tidak meminta reset password, abaikan email ini.
        </p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
        <p style="color: #94a3b8; font-size: 12px;">
            Email ini dikirim secara otomatis oleh BusinessHub. Jangan balas email ini.
        </p>
    </div>
    """
    text_body = (
        f"BusinessHub — Reset Password\n\n"
        f"Anda telah meminta reset password.\n"
        f"Buka link berikut: {reset_url}\n\n"
        f"Link berlaku selama {expires_minutes} menit.\n"
        f"Jika Anda tidak meminta reset, abaikan email ini."
    )
    return subject, html_body, text_body
