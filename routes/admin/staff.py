from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user
from sqlalchemy import func

from extensions import db
from models import User, ADMIN_SECTIONS
from routes.admin import admin_bp, owner_required

MIN_PASSWORD_LENGTH = 6


def clean(name):
    return (request.form.get(name) or "").strip()


def ticked_sections():
    return ",".join(s for s in ADMIN_SECTIONS if request.form.get(f"section_{s}") == "on")


def section_groups():
    """[("Website", [("home", "Home page", ""), ...]), ...] in the order ADMIN_SECTIONS lists them."""
    groups = {}
    for key, (group, name, detail) in ADMIN_SECTIONS.items():
        groups.setdefault(group, []).append((key, name, detail))
    return list(groups.items())


def get_staff(user_id):
    """A staff account (never a customer, and never the owner, who can't be edited from here)."""
    return User.query.filter_by(id=user_id, role="admin", is_owner=False).first_or_404()


# ==========================================
# STAFF ACCOUNTS (owner only)
# ==========================================

@admin_bp.route("/staff", methods=["GET", "POST"])
@owner_required
def admin_staff():

    if request.method == "POST":

        username = clean("username")
        email = clean("email").lower()
        phone = clean("phone")
        password = request.form.get("password") or ""

        if not all([clean("first_name"), clean("last_name"), username, email, phone]):
            flash("Fill in every field to add a staff member.", "danger")
            return redirect(url_for("admin.admin_staff"))

        if len(password) < MIN_PASSWORD_LENGTH:
            flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
            return redirect(url_for("admin.admin_staff"))

        existing = User.query.filter(
            (func.lower(User.username) == username.lower()) |
            (func.lower(User.email) == email) |
            (User.phone == phone)
        ).first()

        if existing:
            taken = ("username" if existing.username.lower() == username.lower()
                     else "email" if existing.email.lower() == email else "phone number")
            flash(f"That {taken} is already used by another account.", "warning")
            return redirect(url_for("admin.admin_staff"))

        staff = User(
            first_name=clean("first_name"),
            last_name=clean("last_name"),
            username=username,
            email=email,
            phone=phone,
            role="admin",
            is_owner=False,
            permissions=ticked_sections()
        )
        staff.set_password(password)

        db.session.add(staff)
        db.session.commit()

        flash(f"{staff.first_name} can now log in as @{staff.username}.", "success")

        return redirect(url_for("admin.admin_staff"))

    return render_template(
        "admin/staff.html",
        team=User.query.filter_by(role="admin").order_by(User.is_owner.desc(), User.first_name).all(),
        sections=ADMIN_SECTIONS,
        section_groups=section_groups(),
        min_length=MIN_PASSWORD_LENGTH
    )


@admin_bp.route("/staff/<int:user_id>/permissions", methods=["POST"])
@owner_required
def update_staff_permissions(user_id):

    staff = get_staff(user_id)
    staff.permissions = ticked_sections()

    db.session.commit()

    flash(f"Updated what {staff.first_name} can open.", "success")

    return redirect(url_for("admin.admin_staff"))


@admin_bp.route("/staff/<int:user_id>/password", methods=["POST"])
@owner_required
def reset_staff_password(user_id):

    staff = get_staff(user_id)
    password = request.form.get("password") or ""

    if len(password) < MIN_PASSWORD_LENGTH:
        flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
        return redirect(url_for("admin.admin_staff"))

    staff.set_password(password)
    db.session.commit()

    flash(f"New password set for {staff.first_name}.", "success")

    return redirect(url_for("admin.admin_staff"))


@admin_bp.route("/staff/<int:user_id>/delete", methods=["POST"])
@owner_required
def delete_staff(user_id):

    staff = get_staff(user_id)

    if staff.id == current_user.id:
        flash("You can't remove your own account.", "warning")
        return redirect(url_for("admin.admin_staff"))

    db.session.delete(staff)
    db.session.commit()

    flash(f"{staff.first_name} {staff.last_name} can no longer log in.", "success")

    return redirect(url_for("admin.admin_staff"))
