from collections import Counter
from datetime import date, datetime

from flask import render_template, request
from sqlalchemy import func

from extensions import db
from models import User, Order, OrderItem, Product, Appointment, CustomDesign
from routes.admin import admin_bp, admin_required, ORDER_STATUSES, APPOINTMENT_STATUSES


def month_starts(count):
    """The first day of each of the last `count` months, oldest first."""

    today = date.today()
    year, month = today.year, today.month
    months = []

    for _ in range(count):
        months.append(date(year, month, 1))
        month -= 1
        if month == 0:
            year, month = year - 1, 12

    return list(reversed(months))


@admin_bp.route("/reports")
@admin_required
def admin_reports():

    months_back = request.args.get("months", 6, type=int)
    if months_back not in (3, 6, 12):
        months_back = 6

    months = month_starts(months_back)
    since = datetime.combine(months[0], datetime.min.time())

    orders = Order.query.filter(Order.created_at >= since).all()
    paid = [o for o in orders if o.payment_status == "Paid" and o.order_status != "Cancelled"]

    # Revenue per month (paid orders only)
    revenue_by_month = Counter()
    for order in paid:
        revenue_by_month[(order.created_at.year, order.created_at.month)] += order.total or 0

    monthly = [
        {
            "label": m.strftime("%b %Y"),
            "short": m.strftime("%b"),
            "revenue": revenue_by_month.get((m.year, m.month), 0),
            "orders": sum(1 for o in orders if (o.created_at.year, o.created_at.month) == (m.year, m.month)),
        }
        for m in months
    ]

    revenue = sum(o.total or 0 for o in paid)

    # Top products by quantity sold (excluding cancelled orders)
    top_products = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label("quantity"),
        func.sum(OrderItem.subtotal).label("sales")
    ).join(OrderItem, OrderItem.product_id == Product.id).join(
        Order, OrderItem.order_id == Order.id
    ).filter(
        Order.created_at >= since,
        Order.order_status != "Cancelled"
    ).group_by(Product.name).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()

    appointments = Appointment.query.filter(Appointment.appointment_date >= months[0]).all()

    return render_template(
        "admin/reports.html",
        months_back=months_back,
        monthly=monthly,
        max_revenue=max((m["revenue"] for m in monthly), default=0),
        revenue=revenue,
        order_count=len(orders),
        average_order=(revenue / len(paid)) if paid else 0,
        unpaid=sum(o.total or 0 for o in orders
                   if o.payment_status == "Pending" and o.order_status != "Cancelled"),
        new_customers=User.query.filter(User.role == "customer", User.created_at >= since).count(),
        orders_by_status=[(s, sum(1 for o in orders if o.order_status == s)) for s in ORDER_STATUSES],
        appointments_by_status=[(s, sum(1 for a in appointments if a.status == s)) for s in APPOINTMENT_STATUSES],
        services=Counter(a.service or "Other" for a in appointments).most_common(),
        designs=CustomDesign.query.filter(CustomDesign.created_at >= since).count(),
        top_products=top_products
    )
