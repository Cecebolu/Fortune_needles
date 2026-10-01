from datetime import date

from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import Appointment, CustomDesign
from routes.admin import (admin_bp, admin_required, form_date, form_float,
                          APPOINTMENT_STATUSES, DESIGN_STATUSES)


# ==========================================
# APPOINTMENTS
# ==========================================

@admin_bp.route("/appointments")
@admin_required
def admin_appointments():

    status = request.args.get("status")
    when = request.args.get("when", "upcoming")

    query = Appointment.query

    if status in APPOINTMENT_STATUSES:
        query = query.filter(Appointment.status == status)

    if when == "upcoming":
        query = query.filter(Appointment.appointment_date >= date.today()).order_by(
            Appointment.appointment_date, Appointment.appointment_time)
    elif when == "past":
        query = query.filter(Appointment.appointment_date < date.today()).order_by(
            Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
    else:
        when = "all"
        query = query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())

    return render_template(
        "admin/appointments.html",
        appointments=query.all(),
        status=status,
        when=when,
        statuses=APPOINTMENT_STATUSES,
        today=date.today()
    )


@admin_bp.route("/appointments/<int:appointment_id>/status", methods=["POST"])
@admin_required
def update_appointment(appointment_id):

    appointment = db.get_or_404(Appointment, appointment_id)
    status = request.form.get("status")

    if status in APPOINTMENT_STATUSES:
        appointment.status = status
        db.session.commit()
        flash(f"Appointment for {appointment.customer.first_name} marked {status}.", "success")

    return redirect(request.referrer or url_for("admin.admin_appointments"))


# ==========================================
# DESIGN REQUESTS
# ==========================================

@admin_bp.route("/designs")
@admin_required
def admin_designs():

    status = request.args.get("status")

    query = CustomDesign.query

    if status in DESIGN_STATUSES:
        query = query.filter(CustomDesign.status == status)

    return render_template(
        "admin/designs.html",
        designs=query.order_by(CustomDesign.created_at.desc()).all(),
        status=status,
        statuses=DESIGN_STATUSES
    )


@admin_bp.route("/designs/<int:design_id>", methods=["POST"])
@admin_required
def update_design(design_id):

    design = db.get_or_404(CustomDesign, design_id)
    status = request.form.get("status")

    if status in DESIGN_STATUSES:
        design.status = status

    design.estimated_price = form_float("estimated_price")
    design.expected_completion = form_date("expected_completion")

    db.session.commit()

    flash(f"Design request from {design.customer.first_name} updated.", "success")

    return redirect(request.referrer or url_for("admin.admin_designs"))
