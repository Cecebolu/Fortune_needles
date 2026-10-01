from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User

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
        username = request.form.get("username")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.signup"))

        existing = User.query.filter(
            (User.username == username) |
            (User.email == email) |
            (User.phone == phone)
        ).first()

        if existing:

            if existing.username == username:
                flash("Username already exists.", "warning")

            elif existing.email == email:
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

        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):

            login_user(user)

            flash(f"Welcome {user.first_name}!", "success")

            if user.role == "admin":
                return redirect(url_for("admin.admin_dashboard"))

            return redirect(url_for("customer.dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("auth/login.html")


# ==========================================
# LOGOUT
# ==========================================

@auth_bp.route("/logout")
@login_required
def logout():

    logout_user()

    flash("Logged out successfully.", "success")

    return redirect(url_for("public.home"))