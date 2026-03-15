import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_USER)

print(f"[email_service] EMAIL_USER={'SET ✅' if EMAIL_USER else 'NOT SET ❌'}", flush=True)


def send_email(to_email: str, subject: str, body: str) -> bool:
    return send_email_html(to_email, subject, f"<pre>{body}</pre>")


def send_email_html(to_email: str, subject: str, html_body: str) -> bool:
    if not EMAIL_USER or not EMAIL_PASS:
        logger.warning("⚠️ EMAIL_USER or EMAIL_PASS not set — skipping email send")
        return False

    try:
        logger.info(f"📧 Sending email to {to_email} via {EMAIL_HOST}:{EMAIL_PORT}")
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=30)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())
        server.quit()
        logger.info(f"✅ Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Email send failed to {to_email}: {e}")
        return False
