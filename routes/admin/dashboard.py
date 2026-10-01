from datetime import date

from flask import render_template

from models import User, Product, Appointment, CustomDesign
from routes.admin import admin_bp, admin_required


@admin_bp.route("/")
@admin_required
def admin_dashboard():

    return render_template(
        "admin/dashboard.html",
        total_customers=User.query.filter_by(role="customer").count(),
        total_appointments=Appointment.query.count(),
        total_designs=CustomDesign.query.count(),
        total_products=Product.query.count(),
        recent_appointments=Appointment.query.filter(
            Appointment.appointment_date >= date.today()
        ).order_by(
            Appointment.appointment_date,
            Appointment.appointment_time
        ).limit(5).all(),
        recent_designs=CustomDesign.query.order_by(
            CustomDesign.created_at.desc()
        ).limit(5).all()
    )
