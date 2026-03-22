import os
import json
import logging
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Notes Market")
EMAIL_FROM_ADDRESS = os.getenv("EMAIL_FROM_ADDRESS", "noreply@notesmarket.app")

print(f"[email_service] BREVO_API_KEY={'SET ✅' if BREVO_API_KEY else 'NOT SET ❌'}", flush=True)


def send_email(to_email: str, subject: str, body: str) -> bool:
    return send_email_html(to_email, subject, f"<pre>{body}</pre>")


def send_email_html(to_email: str, subject: str, html_body: str) -> bool:
    if not BREVO_API_KEY:
        logger.warning("⚠️ BREVO_API_KEY not set — skipping email send")
        return False

    payload = json.dumps({
        "sender": {"name": EMAIL_FROM_NAME, "email": EMAIL_FROM_ADDRESS},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_body,
    }).encode()

    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=payload,
        headers={
            "api-key": BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            logger.info(f"✅ Email sent via Brevo to {to_email}: messageId={result.get('messageId')}")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        logger.error(f"❌ Brevo API error {e.code} to {to_email}: {body}")
        return False
    except Exception as e:
        logger.error(f"❌ Email send failed to {to_email}: {e}")
        return False
