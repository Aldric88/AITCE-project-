import os
import json
import logging
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "Notes Market <onboarding@resend.dev>")

print(f"[email_service] RESEND_API_KEY={'SET ✅' if RESEND_API_KEY else 'NOT SET ❌'}", flush=True)


def send_email(to_email: str, subject: str, body: str) -> bool:
    return send_email_html(to_email, subject, f"<pre>{body}</pre>")


def send_email_html(to_email: str, subject: str, html_body: str) -> bool:
    if not RESEND_API_KEY:
        logger.warning("⚠️ RESEND_API_KEY not set — skipping email send")
        return False

    payload = json.dumps({
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }).encode()

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            logger.info(f"✅ Email sent via Resend to {to_email}: id={result.get('id')}")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        logger.error(f"❌ Resend API error {e.code} to {to_email}: {body}")
        return False
    except Exception as e:
        logger.error(f"❌ Email send failed to {to_email}: {e}")
        return False
