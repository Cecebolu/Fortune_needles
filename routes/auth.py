from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func, or_

from extensions import db
from models import User, Notification
from utils import whatsapp_digits, make_reset_token, user_from_reset_token, send_email

auth_bp = Blueprint("auth", __name__)


# ==========================================
# SIGNUP
# ==========================================

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():

    if current_user.is_authenticated:
        return redirect(url_for("customer.dashboard"))

    if request.method == "POST":

        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        phone = (request.form.get("phone") or "").strip()
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.signup"))

        existing = User.query.filter(
            (func.lower(User.username) == username.lower()) |
            (func.lower(User.email) == email) |
            (User.phone == phone)
        ).first()

        if existing:

            if existing.username.lower() == username.lower():
                flash("Username already exists.", "warning")

            elif existing.email.lower() == email:
                flash("Email already exists.", "warning")

            elif existing.phone == phone:
                flash("Phone number already exists.", "warning")

            return redirect(url_for("auth.signup"))

        user = User(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            phone=phone,
            role="customer"
        )

        user.set_password(password)

        db.session.add(user)
        db.session.flush()

        Notification.add(
            "customer",
            "New customer signed up",
            f"{user.first_name} {user.last_name} ({user.phone})",
            url_for("admin.customer_detail", user_id=user.id)
        )

        db.session.commit()

        flash("Account created successfully. Please login.", "success")

        return redirect(url_for("auth.login"))

    return render_template("auth/signup.html")


# ==========================================
# LOGIN
# ==========================================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        login_name = (request.form.get("username") or "").strip().lower()
        password = request.form.get("password")

        user = User.query.filter(or_(
            func.lower(User.username) == login_name,
            func.lower(User.email) == login_name
        )).first()

        if user and user.check_password(password):

            login_user(user)

            flash(f"Welcome {user.first_name}!", "success")

            next_page = request.args.get("next", "")

            if next_page.startswith("/") and not next_page.startswith("//"):
                return redirect(next_page)

            if user.role == "admin":
                return redirect(url_for("admin.admin_dashboard"))

            return redirect(url_for("customer.dashboard"))

        flash("Invalid username/email or password.", "danger")

    return render_template("auth/login.html")


# ==========================================
# LOGOUT
# ==========================================

@auth_bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():

    # Opening /logout directly doesn't log out; the confirmation box sends a POST
    if request.method == "GET":
        if current_user.role == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        return redirect(url_for("customer.dashboard"))

    logout_user()
    session.pop("cart", None)

    flash("Logged out successfully.", "success")

    return redirect(url_for("public.home"))

# ==========================================
# FORGOT / RESET PASSWORD
# ==========================================

MIN_PASSWORD_LENGTH = 6


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if current_user.is_authenticated:
        return redirect(url_for("customer.dashboard"))

    if request.method == "POST":

        lookup = (request.form.get("account") or "").strip()
        lowered = lookup.lower()
        phone_digits = whatsapp_digits(lookup)

        user = None
        if lookup:
            user = User.query.filter(or_(
                func.lower(User.username) == lowered,
                func.lower(User.email) == lowered
            )).first()
            if not user and len(phone_digits) >= 9:
                user = next((u for u in User.query.filter(User.phone.isnot(None))
                             if whatsapp_digits(u.phone) == phone_digits), None)

        emailed = False

        if user:
            link = url_for("auth.reset_password", token=make_reset_token(user, "email"), _external=True)
            emailed = send_email(
                user.email,
                "Reset your Fortune Needles password",
                f"Hello {user.first_name},\n\n"
                f"Click the link below to choose a new password. It works for 1 hour.\n\n{link}\n\n"
                "If you didn't ask for this, you can ignore this email.\n\nFortune Needles"
            )

            if user.role != "admin":
                Notification.add(
                    "password",
                    "Password reset requested",
                    f"{user.first_name} {user.last_name} ({user.phone})"
                    + (" - reset link emailed" if emailed else " - needs a reset link"),
                    url_for("admin.customer_detail", user_id=user.id) + "#password-reset"
                )
                db.session.commit()

        # Same answer whether or not the account exists, so this page can't be used to find accounts
        return render_template("auth/forgot_password.html", sent=True, emailed=emailed)

    return render_template("auth/forgot_password.html", sent=False)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):

    user = user_from_reset_token(token)

    if not user:
        flash("This reset link is invalid, has expired or was already used. Please ask for a new one.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":

        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        if len(password) < MIN_PASSWORD_LENGTH:
            flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        else:
            user.set_password(password)
            db.session.commit()

            if current_user.is_authenticated:
                logout_user()

            flash("Your password has been changed. Please log in with your new password.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", user=user, min_length=MIN_PASSWORD_LENGTH)
