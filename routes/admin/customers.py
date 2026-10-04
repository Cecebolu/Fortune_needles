from urllib.parse import quote

from flask import render_template, request, redirect, url_for, flash, session

from extensions import db
from models import User, Measurement
from routes.admin import admin_bp, section_required, form_float, search_condition
from utils import make_reset_token, whatsapp_digits, RESET_LINK_HOURS

MEASUREMENT_FIELDS = [
    ("chest", "Chest"),
    ("waist", "Waist"),
    ("hips", "Hips"),
    ("shoulder", "Shoulder"),
    ("sleeve", "Sleeve"),
    ("neck", "Neck"),
    ("inseam", "Inseam"),
    ("height", "Height"),
]


def search_customers(search):

    query = User.query.filter_by(role="customer")

    if search:
        query = query.filter(search_condition(
            search,
            [User.first_name, User.last_name, User.username, User.email, User.phone],
            phone_columns=[User.phone]
        ))

    return query.order_by(User.created_at.desc()).all()


# ==========================================
# CUSTOMERS
# ==========================================

@admin_bp.route("/customers")
@section_required("customers")
def admin_customers():

    search = (request.args.get("q") or "").strip()

    return render_template(
        "admin/customers.html",
        customers=search_customers(search),
        search=search
    )


@admin_bp.route("/customers/<int:user_id>")
@section_required("customers")
def customer_detail(user_id):

    customer = db.get_or_404(User, user_id)

    # A reset link just created for this customer (shown once, kept out of the URL)
    reset = session.pop("reset_link", None)
    reset_link = reset["link"] if reset and reset.get("user_id") == customer.id else None

    whatsapp_url = None
    if reset_link and customer.phone:
        text = (f"Hello {customer.first_name}, here is your link to reset your Fortune Needles password "
                f"(it works for {RESET_LINK_HOURS['admin']} hours):\n{reset_link}")
        whatsapp_url = f"https://wa.me/{whatsapp_digits(customer.phone)}?text={quote(text)}"

    return render_template(
        "admin/customer_detail.html",
        customer=customer,
        fields=MEASUREMENT_FIELDS,
        total_spent=sum(order.total or 0 for order in customer.orders
                        if order.payment_status == "Paid"),
        reset_link=reset_link,
        reset_whatsapp_url=whatsapp_url,
        reset_hours=RESET_LINK_HOURS["admin"]
    )


@admin_bp.route("/customers/<int:user_id>/reset-link", methods=["POST"])
@section_required("customers")
def create_reset_link(user_id):

    customer = db.get_or_404(User, user_id)

    session["reset_link"] = {
        "user_id": customer.id,
        "link": url_for("auth.reset_password", token=make_reset_token(customer, "admin"), _external=True)
    }

    flash(f"Reset link created for {customer.first_name}. Send it to them below.", "success")

    return redirect(url_for("admin.customer_detail", user_id=customer.id) + "#password-reset")


# ==========================================
# MEASUREMENTS
# ==========================================

@admin_bp.route("/measurements")
@section_required("customers")
def admin_measurements():

    search = (request.args.get("q") or "").strip()

    return render_template(
        "admin/measurements.html",
        customers=search_customers(search),
        fields=MEASUREMENT_FIELDS,
        search=search
    )


@admin_bp.route("/customers/<int:user_id>/measurements", methods=["POST"])
@section_required("customers")
def save_measurements(user_id):

    customer = db.get_or_404(User, user_id)

    measurement = customer.measurements or Measurement(user_id=customer.id)

    for field, _label in MEASUREMENT_FIELDS:
        setattr(measurement, field, form_float(field))

    db.session.add(measurement)
    db.session.commit()

    flash(f"Measurements saved for {customer.first_name}.", "success")

    return redirect(url_for("admin.customer_detail", user_id=customer.id))
