"""Telling customers about changes: on the website, by email and by SMS.

Every update is saved as a CustomerAlert (shown on the customer's Updates page).
Email is sent when MAIL_* settings exist; SMS when Africa's Talking settings exist.
WhatsApp can't be sent automatically without the paid WhatsApp Business API, so
the admin gets ready-made "Send on WhatsApp" links instead (see whatsapp_url).
"""
import json
from datetime import datetime
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from flask import current_app, url_for

from extensions import db
from models import CustomerAlert, StockAlert, Notification
from utils import send_email, whatsapp_digits


# ==========================================
# SMS (Africa's Talking)
# ==========================================

def sms_configured():
    config = current_app.config
    return bool(config.get("AT_USERNAME") and config.get("AT_API_KEY"))


def send_sms(phone, text):
    """Send an SMS through Africa's Talking. Returns True if it was accepted."""

    digits = whatsapp_digits(phone)
    if not sms_configured() or len(digits) < 9:
        return False

    config = current_app.config
    username = config["AT_USERNAME"]
    host = "api.sandbox.africastalking.com" if username == "sandbox" else "api.africastalking.com"

    fields = {"username": username, "to": "+" + digits, "message": text[:459]}
    if config.get("AT_SENDER_ID"):
        fields["from"] = config["AT_SENDER_ID"]

    request = Request(
        f"https://{host}/version1/messaging",
        data=urlencode(fields).encode(),
        headers={"apiKey": config["AT_API_KEY"], "Accept": "application/json",
                 "Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )

    try:
        with urlopen(request, timeout=15) as response:
            result = json.load(response)
        recipients = result.get("SMSMessageData", {}).get("Recipients", [])
        return any(r.get("status") == "Success" for r in recipients)
    except (OSError, ValueError) as error:
        current_app.logger.warning("SMS to %s failed: %s", phone, error)
        return False


# ==========================================
# WHATSAPP (manual, one tap for the admin)
# ==========================================

def whatsapp_url(phone, text):
    digits = whatsapp_digits(phone)
    return f"https://wa.me/{digits}?text={quote(text)}" if len(digits) >= 9 else None


# ==========================================
# CUSTOMER UPDATES
# ==========================================

def alert_customer(user, kind, title, message, link=None):
    """Save an update for the customer and send it by email/SMS where possible.
    The caller commits the session."""

    alert = CustomerAlert(user_id=user.id, kind=kind, title=title, message=message, link=link)
    db.session.add(alert)

    full_link = url_for("customer.updates", _external=True)

    if user.email:
        alert.emailed = send_email(
            user.email,
            f"Fortune Needles: {title}",
            f"Hello {user.first_name},\n\n{title}\n{message}\n\nSee all your updates: {full_link}\n\nFortune Needles"
        )

    if user.phone:
        alert.texted = send_sms(user.phone, f"Fortune Needles: {title}. {message}")

    return alert


def update_text(alert_title, alert_message, first_name):
    """The same update worded for WhatsApp."""
    return f"Hello {first_name}! {alert_title}.\n{alert_message}\n\nFortune Needles"


# ==========================================
# BACK IN STOCK
# ==========================================

def notify_if_restocked(product, old_stock):
    """Call after changing a product's stock. If it was sold out and now isn't,
    tell everyone on its waiting list. Returns how many were told."""

    if (old_stock or 0) > 0 or product.stock <= 0 or not product.is_available:
        return 0

    waiting = StockAlert.query.filter_by(product_id=product.id, notified_at=None).all()
    if not waiting:
        return 0

    title = f"{product.name} is back in stock"
    message = f"Good news! {product.name} is available again at KES {product.price:,.0f}. Order soon, stock is limited."
    shop_link = url_for("public.shop", _external=True)

    for entry in waiting:
        if entry.user:
            alert_customer(entry.user, "restock", title, message, url_for("public.shop"))
        else:
            if entry.email:
                send_email(entry.email, f"Fortune Needles: {title}",
                           f"Hello {entry.contact_name},\n\n{message}\n\nShop now: {shop_link}\n\nFortune Needles")
            if entry.phone:
                send_sms(entry.phone, f"Fortune Needles: {message}")
        entry.notified_at = datetime.utcnow()

    Notification.add(
        "restock",
        f"{product.name} is back in stock",
        f"{len(waiting)} waiting customer{'s' if len(waiting) != 1 else ''} told. Send WhatsApp messages from the product page.",
        url_for("admin.edit_product", product_id=product.id) + "#waiting-list"
    )

    return len(waiting)
