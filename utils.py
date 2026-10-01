import re
import smtplib
from email.message import EmailMessage

from flask import current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from extensions import db
from models import User

# How long a password reset link works, by how it was sent
RESET_LINK_HOURS = {"email": 1, "admin": 24}


# ==========================================
# PHONE NUMBERS
# ==========================================

def whatsapp_digits(number):
    """Turn a Kenyan number like '+254 0114 725 119' or '0114725119' into '254114725119'."""

    digits = re.sub(r"\D", "", number or "")

    if digits.startswith("2540"):
        digits = "254" + digits[4:]
    elif digits.startswith("0"):
        digits = "254" + digits[1:]

    return digits


# ==========================================
# PASSWORD RESET LINKS
# ==========================================

def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="password-reset")


def make_reset_token(user, sent_by="email"):
    """A signed token for this user. It stops working once the password changes,
    because it carries a fingerprint of the current password hash."""

    return _serializer().dumps({"u": user.id, "p": user.password_hash[-16:], "by": sent_by})


def user_from_reset_token(token):
    """The user the token belongs to, or None if it is invalid, expired or already used."""

    try:
        data = _serializer().loads(token)
        max_hours = RESET_LINK_HOURS.get(data.get("by"), 1)
        _serializer().loads(token, max_age=max_hours * 3600)
    except (BadSignature, SignatureExpired):
        return None

    user = db.session.get(User, data.get("u"))

    if not user or user.password_hash[-16:] != data.get("p"):
        return None

    return user


# ==========================================
# EMAIL
# ==========================================

def email_configured():
    config = current_app.config
    return bool(config.get("MAIL_SERVER") and config.get("MAIL_USERNAME") and config.get("MAIL_PASSWORD"))


def send_email(to, subject, body):
    """Send a plain-text email. Returns True if it was sent."""

    if not email_configured():
        return False

    config = current_app.config

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.get("MAIL_FROM") or config["MAIL_USERNAME"]
    message["To"] = to
    message.set_content(body)

    try:
        with smtplib.SMTP(config["MAIL_SERVER"], int(config.get("MAIL_PORT") or 587), timeout=15) as smtp:
            smtp.starttls()
            smtp.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"])
            smtp.send_message(message)
        return True
    except (smtplib.SMTPException, OSError) as error:
        current_app.logger.warning("Email to %s failed: %s", to, error)
        return False
