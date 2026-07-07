import logging
import asyncio
import smtplib
import datetime
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ai_orchestration.core.config import (
    SITE_URL, PROJECT_NAME, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
)
from ai_orchestration.core.celery_app import celery_app

# Requirement 9: Structured Logging
logger = logging.getLogger("SnLag_MailService")

# Enhanced SMTP configuration
SMTP_TIMEOUT = 30
SIGNAL_LOG = "neural_signals.log"

def get_otp_template(code, purpose):
    """MODERN HTML EMAIL TEMPLATE"""
    title = "Verify Your Account" if purpose == "registration" else "Authorize Login"
    action_text = "to finalize your Signly node initialization." if purpose == "registration" else "to establish a secure neural link."

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ margin: 0; padding: 0; background-color: #f8fafc; }}
            .container {{ font-family: sans-serif; max-width: 500px; margin: 40px auto; padding: 40px; border-radius: 24px; background: #ffffff; border: 1px solid #f1f5f9; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            .logo {{ color: #f97316; font-size: 24px; font-weight: 900; margin-bottom: 24px; }}
            h1 {{ color: #0f172a; font-size: 22px; font-weight: 800; margin-bottom: 16px; }}
            .code-box {{ background: #fff7ed; border-radius: 12px; padding: 32px; text-align: center; margin: 24px 0; border: 1px solid #ffedd5; }}
            .code {{ font-size: 32px; font-weight: 900; letter-spacing: 0.2em; color: #ea580c; }}
            .footer {{ color: #94a3b8; font-size: 11px; text-align: center; margin-top: 32px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">Signly</div>
            <h1>{title}</h1>
            <p>Verification request for your Signly node. Use the token below {action_text}</p>
            <div class="code-box"><span class="code">{code}</span></div>
            <p>Access Point: <a href="{SITE_URL}">{SITE_URL}</a></p>
            <div class="footer">Signly Platform Security • Automated Transmission</div>
        </div>
    </body>
    </html>
    """

def _send_sync(to_email: str, subject: str, html_content: str, code: str = None):
    """Synchronous SMTP worker"""
    msg = MIMEMultipart('alternative')
    msg['From'] = SMTP_USER
    msg['To'] = to_email
    msg['Subject'] = subject

    text_content = f"Signly Security Code: {code}" if code else "Welcome to Signly"
    msg.attach(MIMEText(text_content, 'plain'))
    msg.attach(MIMEText(html_content, 'html'))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"SMTP Failure for {to_email}: {e}")
        raise

# API Compatibility Layer
async def send_verification_signal(email: str, code: str, purpose: str):
    """API Bridge: Offloads verification signal to Celery"""
    logger.info(f"Mail Bridge: Offloading verification for {email} to worker.")
    send_verification_task.delay(email, code, purpose)
    return True

async def send_welcome_signal(email: str, name: str):
    """API Bridge: Offloads welcome signal to Celery"""
    logger.info(f"Mail Bridge: Offloading welcome for {email} to worker.")
    send_welcome_task.delay(email, name)
    return True

# Requirement 5: Task Queue Reliability
@celery_app.task(
    name="ai_orchestration.services.mail_service.send_verification_task",
    queue="high_priority",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=5
)
def send_verification_task(email: str, code: str, purpose: str):
    """Background task executor for verification signals"""
    logger.info(f"Mail Worker: Transmitting code to {email}")
    html = get_otp_template(code, purpose)
    _send_sync(email, f"Signly Security Code: {code}", html, code)

    with open(SIGNAL_LOG, "a") as f:
        f.write(f"[{datetime.datetime.utcnow()}] VERIFIED signal to {email}\n")

@celery_app.task(
    name="ai_orchestration.services.mail_service.send_welcome_task",
    queue="high_priority",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3
)
def send_welcome_task(email: str, name: str):
    """Background task executor for welcome signals"""
    logger.info(f"Mail Worker: Transmitting welcome to {email}")
    # Simple template for background worker
    html = f"<h1>Welcome to Signly, {name}</h1><p>Your node is active.</p>"
    _send_sync(email, "Welcome to Signly 🚀", html)
