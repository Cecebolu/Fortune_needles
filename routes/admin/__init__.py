import os
import uuid
from datetime import datetime
from functools import wraps

from flask import Blueprint, request, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import ContactMessage, Notification

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

ORDER_STATUSES = ["Received", "In Progress", "Ready", "Delivered", "Cancelled"]
PAYMENT_STATUSES = ["Pending", "Paid", "Refunded"]
APPOINTMENT_STATUSES = ["Pending", "Confirmed", "Completed", "Cancelled"]
DESIGN_STATUSES = ["Submitted", "Reviewed", "In Progress", "Completed", "Rejected"]


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

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):

        if current_user.role != "admin":
            abort(403)

        return view(*args, **kwargs)

    return wrapped


def save_image(file, subfolder):
    """Save an uploaded image under static/uploads/<subfolder>. Returns the filename, or None."""

    if not file or not file.filename:
        return None

    extension = file.filename.rsplit(".", 1)[-1].lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return None

    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"

    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(folder, exist_ok=True)

    file.save(os.path.join(folder, filename))

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


def form_float(name):

    try:
        return float(request.form.get(name))
    except (TypeError, ValueError):
        return None


# Register the admin pages (imported last so they can use the helpers above)
from routes.admin import (dashboard, products, orders, customers, bookings, reviews,  # noqa: E402,F401
                          content, reports, notifications)
