from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from extensions import db
from models import (Appointment, CustomDesign, Service, Notification, Product, Order, OrderItem, Review,
                    DismissedAlert)

customer_bp = Blueprint("customer", __name__)


# ==========================================
# DASHBOARD
# ==========================================

@customer_bp.route("/dashboard")
@login_required
def dashboard():

    if current_user.role == "admin":
        return redirect(url_for("admin.admin_dashboard"))

    appointments = Appointment.query.filter_by(user_id=current_user.id).order_by(
        Appointment.appointment_date.desc()
    ).all()

    designs = CustomDesign.query.filter_by(user_id=current_user.id).order_by(
        CustomDesign.created_at.desc()
    ).all()

    orders = Order.query.filter_by(user_id=current_user.id).order_by(
        Order.created_at.desc()
    ).all()

    return render_template(
        "customer/dashboard.html",
        appointments=appointments,
        designs=designs,
        orders=orders,
        alerts=dashboard_alerts(appointments, designs, orders)
    )


def dashboard_alerts(appointments, designs, orders):
    """Highlight banners for the customer, minus any they have closed."""

    today = datetime.now().date()
    alerts = []

    for a in appointments:
        if a.appointment_date < today:
            continue
        when = f"{a.appointment_date.strftime('%A %d %B %Y')} at {a.appointment_time.strftime('%I:%M %p')}"
        if a.status == "Confirmed":
            alerts.append(dict(key=f"appointment-{a.id}-Confirmed", style="success", icon="bi-calendar-check-fill",
                               title=f"Your {a.service} is confirmed!", text=f"{when}. See you then."))
        elif a.status == "Pending":
            alerts.append(dict(key=f"appointment-{a.id}-Pending", style="warning", icon="bi-hourglass-split",
                               title=f"{a.service} awaiting confirmation",
                               text=f"Requested for {when}. We will confirm shortly."))

    for o in orders:
        if o.order_status == "Ready":
            alerts.append(dict(key=f"order-{o.id}-Ready", style="primary", icon="bi-bag-check-fill",
                               title=f"Order {o.tracking_code} is ready!",
                               text="Your order is ready for collection or delivery."))

    to_review = products_to_review()
    if to_review:
        more = f" and {len(to_review) - 1} more" if len(to_review) > 1 else ""
        alerts.append(dict(key="review-" + "-".join(str(p.id) for p in to_review), style="gold", icon="bi-star-fill",
                           title=f"How was your {to_review[0].name}{more}?",
                           text="Leave a quick star rating. It only takes a moment.",
                           link=url_for("customer.reviews"), link_text="Rate now"))

    for d in designs:
        if d.estimated_price and d.status not in ("Completed", "Rejected"):
            ready = f"Ready by {d.expected_completion.strftime('%d %B %Y')}." if d.expected_completion else "Contact us to go ahead."
            alerts.append(dict(key=f"quote-{d.id}-{d.estimated_price:.0f}-{d.expected_completion}", style="info",
                               icon="bi-tag-fill",
                               title=f"Quote for your {d.clothing_type}: KES {d.estimated_price:,.0f}", text=ready))

    closed = {row.key for row in DismissedAlert.query.filter_by(user_id=current_user.id)}

    return [alert for alert in alerts if alert["key"] not in closed]


@customer_bp.route("/dashboard/alerts/dismiss", methods=["POST"])
@login_required
def dismiss_alert():

    key = (request.form.get("key") or "").strip()[:120]

    if key and not DismissedAlert.query.filter_by(user_id=current_user.id, key=key).first():
        db.session.add(DismissedAlert(user_id=current_user.id, key=key))
        db.session.commit()

    if request.headers.get("X-Requested-With") == "fetch":
        return ("", 204)

    return redirect(url_for("customer.dashboard"))


# ==========================================
# BOOK APPOINTMENT
# ==========================================

@customer_bp.route("/appointment", methods=["GET", "POST"])
@login_required
def appointment():

    if request.method == "POST":

        try:
            appointment_date = datetime.strptime(
                request.form.get("appointment_date", ""), "%Y-%m-%d"
            ).date()
            appointment_time = datetime.strptime(
                request.form.get("appointment_time", ""), "%H:%M"
            ).time()
        except ValueError:
            flash("Please choose a valid date and time.", "danger")
            return redirect(url_for("customer.appointment"))

        if appointment_date < datetime.now().date():
            flash("Appointment date cannot be in the past.", "danger")
            return redirect(url_for("customer.appointment"))

        booking = Appointment(
            user_id=current_user.id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            service=request.form.get("service"),
            phone=request.form.get("phone"),
            notes=request.form.get("notes")
        )

        db.session.add(booking)

        Notification.add(
            "appointment",
            "New appointment booked",
            f"{current_user.first_name} {current_user.last_name}: {booking.service}, "
            f"{appointment_date.strftime('%d %b')} at {appointment_time.strftime('%I:%M %p')}",
            url_for("admin.admin_appointments", when="all")
        )

        db.session.commit()

        flash("Appointment booked. We will confirm shortly.", "success")

        return redirect(url_for("customer.dashboard"))

    return render_template("customer/appointment.html", services=Service.active())


# ==========================================
# DESIGN MY OUTFIT
# ==========================================

def chosen_fabric():

    fabric = (request.form.get("fabric") or "").strip()

    if fabric == "Other":
        return (request.form.get("fabric_other") or "").strip() or None

    return fabric or None


@customer_bp.route("/design", methods=["GET", "POST"])
@login_required
def design():

    if request.method == "POST":

        notes = request.form.get("notes") or ""
        gender = request.form.get("gender")

        custom_design = CustomDesign(
            user_id=current_user.id,
            clothing_type=request.form.get("outfit_type"),
            fabric=chosen_fabric(),
            color=request.form.get("color"),
            description=f"For: {gender}\n{notes}".strip() if gender else notes
        )

        db.session.add(custom_design)

        Notification.add(
            "design",
            "New design request",
            f"{current_user.first_name} {current_user.last_name}: "
            f"{(custom_design.clothing_type or 'outfit').title()} in {custom_design.fabric or 'any fabric'}",
            url_for("admin.admin_designs", status="Submitted")
        )

        db.session.commit()

        flash("Design request submitted. We will get back to you.", "success")

        return redirect(url_for("customer.dashboard"))

    return render_template("customer/design.html")


# ==========================================
# REVIEWS
# ==========================================

def purchased_products():
    """Products this customer has ordered (cancelled orders don't count)."""

    return Product.query.join(OrderItem, OrderItem.product_id == Product.id).join(
        Order, OrderItem.order_id == Order.id
    ).filter(
        Order.user_id == current_user.id,
        Order.order_status != "Cancelled"
    ).distinct().order_by(Product.name).all()


def products_to_review():

    reviewed = {r.product_id for r in Review.query.filter_by(user_id=current_user.id)}

    return [p for p in purchased_products() if p.id not in reviewed]


@customer_bp.route("/my-reviews", methods=["GET", "POST"])
@login_required
def reviews():

    if request.method == "POST":

        rating = request.form.get("rating", type=int)
        comment = (request.form.get("comment") or "").strip() or None
        product_id = request.form.get("product_id", type=int)

        if rating not in range(1, 6):
            flash("Please choose a star rating from 1 to 5.", "danger")
            return redirect(url_for("customer.reviews"))

        if product_id and product_id not in {p.id for p in purchased_products()}:
            flash("You can only review products you have ordered.", "danger")
            return redirect(url_for("customer.reviews"))

        review = Review.query.filter_by(user_id=current_user.id, product_id=product_id or None).first()
        is_new = review is None

        if is_new:
            review = Review(user_id=current_user.id, product_id=product_id or None)
            db.session.add(review)

        review.rating = rating
        review.comment = comment

        if is_new:
            product = db.session.get(Product, product_id) if product_id else None
            Notification.add(
                "review",
                f"New {rating}-star review",
                f"{current_user.first_name} {current_user.last_name} on "
                f"{product.name if product else 'our service'}"
                + (f": {comment[:60]}" if comment else ""),
                url_for("admin.admin_reviews")
            )

        db.session.commit()

        flash("Thank you for your review!" if is_new else "Your review has been updated.", "success")

        return redirect(url_for("customer.reviews"))

    my_reviews = Review.query.filter_by(user_id=current_user.id).order_by(Review.created_at.desc()).all()

    return render_template(
        "customer/reviews.html",
        to_review=products_to_review(),
        my_reviews=my_reviews,
        general_review=next((r for r in my_reviews if r.product_id is None), None),
        editing=request.args.get("edit", type=int)
    )


@customer_bp.route("/my-reviews/<int:review_id>/delete", methods=["POST"])
@login_required
def delete_review(review_id):

    review = db.get_or_404(Review, review_id)

    if review.user_id != current_user.id:
        abort(403)

    db.session.delete(review)
    db.session.commit()

    flash("Review deleted.", "success")

    return redirect(url_for("customer.reviews"))
