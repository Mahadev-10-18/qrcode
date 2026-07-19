import logging
import html
from email.mime.text import MIMEText
from ..config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html_body: str) -> bool:
    if not settings.smtp_host:
        logger.warning("SMTP not configured — skipping email send for subject '%s'", subject)
        return False

    import aiosmtplib

    msg = MIMEText(html_body, "html")
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=True,
            timeout=15,
        )
        logger.info("Email send succeeded for subject '%s'", subject)
        return True
    except Exception as e:
        logger.error("Email send failed for subject '%s': %s", subject, e)
        return False


def build_verification_email(verify_url: str) -> str:
    return f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;background:#f5f5f5;padding:40px">
<div style="max-width:480px;margin:auto;background:#fff;border-radius:12px;padding:32px">
<h2 style="margin-top:0">Verify your email</h2>
<p>Click the button below to verify your email address and activate your account.</p>
<a href="{verify_url}" style="display:inline-block;background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;margin:16px 0">Verify Email</a>
<p style="color:#666;font-size:13px">This link expires in {settings.verification_token_expire_hours} hours. If you did not create an account, ignore this email.</p>
</div></body></html>"""


def build_contact_alert_email(label: str, finder_phone: str = "", message: str = "") -> str:
    safe_label = html.escape(label)
    safe_phone = html.escape(finder_phone) if finder_phone else "Not provided"
    safe_message = html.escape(message) if message else "No message left"
    return f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;background:#f5f5f5;padding:40px">
<div style="max-width:480px;margin:auto;background:#fff;border-radius:12px;padding:32px">
<h2 style="margin-top:0">🚨 Someone found your {safe_label}</h2>
<p>Good news! A Good Samaritan has scanned your QR tag for <strong>{safe_label}</strong> and left you a message.</p>
<div style="background:#f0f0f0;border-radius:8px;padding:16px;margin:16px 0">
<p style="margin:0 0 8px 0;font-size:13px;color:#666">Finder's Phone</p>
<p style="margin:0;font-size:16px;font-weight:600">{safe_phone}</p>
</div>
<div style="background:#f0f0f0;border-radius:8px;padding:16px;margin:16px 0">
<p style="margin:0 0 8px 0;font-size:13px;color:#666">Message</p>
<p style="margin:0;font-size:15px">{safe_message}</p>
</div>
<p style="color:#666;font-size:13px">You can also log in to your TagMaster Pro dashboard to view all contact events.</p>
</div></body></html>"""


def build_password_reset_email(reset_url: str) -> str:
    return f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;background:#f5f5f5;padding:40px">
<div style="max-width:480px;margin:auto;background:#fff;border-radius:12px;padding:32px">
<h2 style="margin-top:0">Reset your password</h2>
<p>Click the button below to reset your password. This link is valid for {settings.reset_token_expire_minutes} minutes.</p>
<a href="{reset_url}" style="display:inline-block;background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;margin:16px 0">Reset Password</a>
<p style="color:#666;font-size:13px">If you did not request a password reset, ignore this email.</p>
</div></body></html>"""
