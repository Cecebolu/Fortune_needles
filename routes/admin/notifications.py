from flask import render_template, request, redirect, url_for, jsonify

from extensions import db
from models import Notification
from routes.admin import admin_bp, admin_required


def safe_link(link):
    """Only follow links inside this site."""

    if link and link.startswith("/") and not link.startswith("//"):
        return link

    return url_for("admin.admin_notifications")


@admin_bp.route("/notifications")
@admin_required
def admin_notifications():

    show = request.args.get("show", "all")

    query = Notification.query

    if show == "unread":
        query = query.filter_by(is_read=False)

    return render_template(
        "admin/notifications.html",
        notifications=query.order_by(Notification.created_at.desc()).limit(200).all(),
        show=show
    )


@admin_bp.route("/notifications/<int:notification_id>/open")
@admin_required
def open_notification(notification_id):

    notification = db.get_or_404(Notification, notification_id)

    if not notification.is_read:
        notification.is_read = True
        db.session.commit()

    return redirect(safe_link(notification.link))


@admin_bp.route("/notifications/read-all", methods=["POST"])
@admin_required
def read_all_notifications():

    Notification.query.filter_by(is_read=False).update({"is_read": True})
    db.session.commit()

    return redirect(request.referrer or url_for("admin.admin_notifications"))


@admin_bp.route("/notifications/feed")
@admin_required
def notifications_feed():
    """Polled by the admin pages to show new notifications without reloading."""

    after = request.args.get("after", 0, type=int)

    new_items = Notification.query.filter(Notification.id > after).order_by(Notification.id).limit(10).all()

    return jsonify({
        "unread": Notification.query.filter_by(is_read=False).count(),
        "items": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message or "",
                "icon": n.icon,
                "url": url_for("admin.open_notification", notification_id=n.id),
            }
            for n in new_items
        ],
    })
