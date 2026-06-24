import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import settings

logger = logging.getLogger(__name__)


def send_verification_email(to_email: str, verification_link: str) -> None:
    if not settings.GMAIL_APP_PASSWORD:
        logger.warning("[Email] GMAIL_APP_PASSWORD no configurado — email no enviado a %s", to_email)
        return

    subject = "Verificá tu cuenta en Petlink"
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 30px; margin: 0;">
      <div style="max-width: 520px; margin: 0 auto; background: white; border-radius: 16px; padding: 36px; box-shadow: 0 4px 24px rgba(0,0,0,0.08);">
        <h2 style="color: #2E7D32; margin-top: 0;">Bienvenido a Petlink 🐾</h2>
        <p style="color: #444; font-size: 16px;">Gracias por registrarte. Hacé clic en el botón para verificar tu cuenta:</p>
        <div style="text-align: center; margin: 32px 0;">
          <a href="{verification_link}"
             style="display: inline-block; background: #2E7D32; color: white; padding: 14px 32px;
                    border-radius: 10px; text-decoration: none; font-weight: bold; font-size: 16px;">
            Verificar mi cuenta
          </a>
        </div>
        <p style="color: #888; font-size: 13px;">El link expira en 24 horas. Si no creaste esta cuenta, ignorá este email.</p>
      </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.GMAIL_USER
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
            server.sendmail(settings.GMAIL_USER, to_email, msg.as_string())
        logger.info("[Email] Verificación enviada a %s", to_email)
    except Exception as exc:
        logger.error("[Email] Error enviando a %s: %s", to_email, exc)
