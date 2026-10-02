from datetime import date

from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import Appointment, CustomDesign, DesignUpdate, DESIGN_STAGES
from notify import alert_customer
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

    if status in APPOINTMENT_STATUSES and status != appointment.status:
        appointment.status = status

        when = (f"{appointment.appointment_date.strftime('%A %d %B')} at "
                f"{appointment.appointment_time.strftime('%I:%M %p')}")
        messages = {
            "Confirmed": (f"Your {appointment.service} is confirmed", f"See you on {when}."),
            "Cancelled": (f"Your {appointment.service} on {when} was cancelled",
                          "Please book another time or contact us if you have questions."),
        }
        if status in messages:
            title, message = messages[status]
            alert_customer(appointment.customer, "appointment", title, message, url_for("customer.dashboard"))

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


STAGE_TEXT = {name: text for name, _icon, text in DESIGN_STAGES}


def move_design(design, stage, note):
    """Record a stage change (or a note) and tell the customer."""

    outfit = (design.clothing_type or "outfit").lower()

    if stage == "Rejected":
        title = f"About your {outfit} request"
        message = note or "Unfortunately we can't make this design. Please contact us to discuss other options."
    else:
        title = f"Your {outfit}: {stage}"
        message = STAGE_TEXT.get(stage, "")
        if stage == "Quoted" and design.estimated_price:
            message = f"Price: KES {design.estimated_price:,.0f}."
            if design.expected_completion:
                message += f" Ready by {design.expected_completion.strftime('%d %B %Y')}."
        if note:
            message = f"{message} {note}".strip()

    design.status = stage
    db.session.add(DesignUpdate(design_id=design.id, stage=stage, note=note or None))
    alert_customer(design.customer, "design", title, message, url_for("customer.dashboard"))


@admin_bp.route("/designs/<int:design_id>", methods=["POST"])
@admin_required
def update_design(design_id):

    design = db.get_or_404(CustomDesign, design_id)
    stage = request.form.get("status")
    note = (request.form.get("note") or "").strip()

    design.estimated_price = form_float("estimated_price")
    design.expected_completion = form_date("expected_completion")

    if stage in DESIGN_STATUSES and (stage != design.status or note):
        move_design(design, stage, note)
        flash(f"{design.customer.first_name} has been told: {stage}.", "success")
    else:
        flash(f"Design request from {design.customer.first_name} saved.", "success")

    db.session.commit()

    return redirect(request.referrer or url_for("admin.admin_designs"))


@admin_bp.route("/designs/<int:design_id>/next", methods=["POST"])
@admin_required
def advance_design(design_id):

    design = db.get_or_404(CustomDesign, design_id)
    stage = design.next_stage

    if stage:
        move_design(design, stage, (request.form.get("note") or "").strip())
        db.session.commit()
        flash(f"Moved to {stage}. {design.customer.first_name} has been told.", "success")

    return redirect(request.referrer or url_for("admin.admin_designs"))
