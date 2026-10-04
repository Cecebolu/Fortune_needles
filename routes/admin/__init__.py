import os
import re
import uuid
from datetime import datetime
from functools import wraps

from flask import Blueprint, request, abort, current_app
from flask_login import login_required, current_user
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.utils import secure_filename

from sqlalchemy import and_, or_, func

from extensions import db
from models import ContactMessage, Notification, DESIGN_STAGE_NAMES

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

MAX_IMAGE_SIDE = 1600   # longest side of an uploaded photo, in pixels
IMAGE_QUALITY = 80      # WebP quality (0-100)

ORDER_STATUSES = ["Received", "In Progress", "Ready", "Delivered", "Cancelled"]
PAYMENT_STATUSES = ["Pending", "Paid", "Refunded"]
APPOINTMENT_STATUSES = ["Pending", "Confirmed", "Completed", "Cancelled"]
DESIGN_STATUSES = DESIGN_STAGE_NAMES + ["Rejected"]


# ==========================================
# HELPERS
# ==========================================

@admin_bp.context_processor
def inject_admin_globals():
    return {
        "now": datetime.now(),
        "unread_messages": ContactMessage.query.filter_by(is_read=False).count(),
        "unread_notifications": Notification.query.filter_by(is_read=False).count(),
        "recent_notifications": Notification.query.order_by(Notification.created_at.desc()).limit(6).all(),
        "latest_notification_id": db.session.query(db.func.max(Notification.id)).scalar() or 0
    }


@admin_bp.app_template_filter("dict_without")
def dict_without(args, key):
    """The current query string minus one key, e.g. to clear a search but keep the status filter."""
    from urllib.parse import urlencode
    return urlencode([(k, v) for k, v in args.items(multi=True) if k != key])


@admin_bp.app_template_filter("whatsapp")
def whatsapp_filter(text, phone):
    """{{ message|whatsapp(customer.phone) }} -> a wa.me link that opens WhatsApp with the message."""
    from notify import whatsapp_url
    return whatsapp_url(phone, text) or ""


@admin_bp.app_template_filter("timeago")
def timeago(moment):
    """Turn a UTC timestamp into 'just now', '5 min ago', '3 h ago' or a date."""

    seconds = (datetime.utcnow() - moment).total_seconds()

    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{int(seconds // 60)} min ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)} h ago"
    if seconds < 7 * 86400:
        return f"{int(seconds // 86400)} d ago"

    return moment.strftime("%d %b %Y")


def admin_required(view):
    """Any admin account: the owner or a staff member."""

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):

        if current_user.role != "admin":
            abort(403)

        return view(*args, **kwargs)

    return wrapped


# view name -> the section it belongs to, so menus can hide links a staff member can't open
VIEW_SECTIONS = {}

OWNER_ONLY = "owner"


def section_required(section):
    """Staff need `section` ticked on their account; the owner can always open it."""

    def decorator(view):

        VIEW_SECTIONS[view.__name__] = section

        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):

            allowed = current_user.is_owner if section == OWNER_ONLY else current_user.can(section)

            if current_user.role != "admin" or not allowed:
                abort(403)

            return view(*args, **kwargs)

        return wrapped

    return decorator


owner_required = section_required(OWNER_ONLY)


@admin_bp.app_template_global()
@admin_bp.app_template_test("can_open")
def can_open(endpoint):
    """{% if can_open('admin.admin_orders') %} - whether the current admin may open that page."""

    if not current_user.is_authenticated or current_user.role != "admin":
        return False

    section = VIEW_SECTIONS.get(endpoint.split(".")[-1])

    if section == OWNER_ONLY:
        return current_user.is_owner

    return current_user.can(section)


def save_image(file, subfolder):
    """Save an uploaded image under static/uploads/<subfolder>, resized and compressed.
    Returns the new filename, or None if the file is not a usable image."""

    if not file or not file.filename:
        return None

    extension = file.filename.rsplit(".", 1)[-1].lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return None

    try:
        image = Image.open(file.stream)
        image.load()
    except (UnidentifiedImageError, OSError):
        return None

    # Phone photos are often stored sideways with a "rotate me" note; apply it
    image = ImageOps.exif_transpose(image)

    # Shrink big photos; small ones are left at their size
    image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.LANCZOS)

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "transparency" in image.info or image.mode in ("LA", "P") else "RGB")

    name = os.path.splitext(secure_filename(file.filename))[0][:60] or "photo"
    filename = f"{uuid.uuid4().hex}_{name}.webp"

    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(folder, exist_ok=True)

    # WebP is much smaller than JPEG/PNG; saving fresh also drops hidden data such as GPS location
    image.save(os.path.join(folder, filename), "WEBP", quality=IMAGE_QUALITY, method=6)

    return filename


def delete_image(filename, subfolder):

    if not filename:
        return

    path = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder, filename)

    if os.path.exists(path):
        os.remove(path)


def form_date(name):

    value = request.form.get(name)

    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def search_condition(search, columns, phone_columns=()):
    """Every word typed must match one of the columns (so "flowers okuh" finds Flowers Okuh).
    Phone numbers match whatever their spacing or prefix: 0719 164 015, +254719164015, 0719164015."""

    conditions = []

    # A search that is only a phone number ("+254 719 164 015") is one number, not four words
    words = [search.replace(" ", "")] if re.fullmatch(r"[\d\s+()-]+", search.strip()) else search.split()

    for word in words:
        options = [column.ilike(f"%{word}%") for column in columns]

        digits = re.sub(r"\D", "", word)
        if digits.startswith("254"):
            digits = digits[3:]
        digits = digits.lstrip("0")
        if len(digits) >= 3:
            for column in phone_columns:
                stored = func.replace(func.replace(func.replace(column, " ", ""), "-", ""), "+", "")
                options.append(stored.ilike(f"%{digits}%"))

        conditions.append(or_(*options))

    return and_(*conditions)


def form_float(name):

    try:
        return float(request.form.get(name))
    except (TypeError, ValueError):
        return None


# Register the admin pages (imported last so they can use the helpers above)
from routes.admin import (dashboard, products, orders, customers, bookings, reviews,  # noqa: E402,F401
                          content, reports, notifications, staff)
