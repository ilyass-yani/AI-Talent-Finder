import os
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import partial


SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER)
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "AI Talent Finder")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def _send_email_sync(to_email: str, subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM_EMAIL, to_email, msg.as_string())


async def send_email(to_email: str, subject: str, html_body: str) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, partial(_send_email_sync, to_email, subject, html_body))


async def send_password_reset_email(to_email: str, reset_token: str) -> None:
    reset_url = f"{FRONTEND_URL}/auth/reset-password?token={reset_token}"
    subject = "Réinitialisation de votre mot de passe – AI Talent Finder"
    html_body = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; background: #f8fafc; padding: 40px 0;">
      <div style="max-width: 520px; margin: 0 auto; background: #fff; border-radius: 16px;
                  border: 1px solid #e2e8f0; padding: 40px;">
        <div style="text-align: center; margin-bottom: 32px;">
          <div style="display: inline-block; background: linear-gradient(135deg, #4f46e5, #6366f1);
                      border-radius: 12px; padding: 12px 16px;">
            <span style="color: #fff; font-weight: 800; font-size: 18px;">AI Talent Finder</span>
          </div>
        </div>
        <h2 style="color: #0f172a; font-size: 22px; margin: 0 0 12px;">
          Réinitialisation de votre mot de passe
        </h2>
        <p style="color: #475569; font-size: 15px; line-height: 1.6; margin: 0 0 28px;">
          Nous avons reçu une demande de réinitialisation du mot de passe associé à votre compte
          <strong>{to_email}</strong>. Cliquez sur le bouton ci-dessous pour choisir un nouveau mot de passe.
        </p>
        <div style="text-align: center; margin-bottom: 28px;">
          <a href="{reset_url}"
             style="display: inline-block; background: linear-gradient(135deg, #4f46e5, #6366f1);
                    color: #fff; text-decoration: none; padding: 14px 32px;
                    border-radius: 10px; font-weight: 700; font-size: 15px;">
            Réinitialiser mon mot de passe
          </a>
        </div>
        <p style="color: #94a3b8; font-size: 13px; line-height: 1.6; margin: 0 0 8px;">
          Ce lien est valable pendant <strong>2 heures</strong>. Si vous n'avez pas fait cette demande,
          ignorez simplement cet email.
        </p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">
        <p style="color: #cbd5e1; font-size: 12px; text-align: center; margin: 0;">
          &copy; 2026 AI Talent Finder. Tous droits réservés.
        </p>
      </div>
    </body>
    </html>
    """
    await send_email(to_email, subject, html_body)
