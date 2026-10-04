from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import User, Product, Order, OrderItem
from notify import alert_customer, notify_if_restocked
from routes.admin import admin_bp, section_required, form_date, search_condition, ORDER_STATUSES, PAYMENT_STATUSES


@admin_bp.route("/orders")
@section_required("shop")
def admin_orders():

    status = request.args.get("status")
    search = (request.args.get("q") or "").strip()

    query = Order.query.join(User, Order.user_id == User.id)

    if status in ORDER_STATUSES:
        query = query.filter(Order.order_status == status)

    if search:
        query = query.filter(search_condition(
            search,
            [Order.tracking_code, User.first_name, User.last_name, User.username, User.phone],
            phone_columns=[User.phone]
        ))

    orders = query.order_by(Order.created_at.desc()).all()

    return render_template(
        "admin/orders.html",
        orders=orders,
        status=status,
        search=search,
        statuses=ORDER_STATUSES
    )


@admin_bp.route("/orders/new", methods=["GET", "POST"])
@section_required("shop")
def add_order():

    customers = User.query.filter_by(role="customer").order_by(User.first_name, User.last_name).all()
    products = Product.query.filter(Product.stock > 0).order_by(Product.name).all()

    if request.method == "POST":

        customer = db.session.get(User, request.form.get("user_id", type=int) or 0)

        if not customer:
            flash("Please choose a customer.", "danger")
            return redirect(url_for("admin.add_order"))

        # Combine repeated products into one line each
        wanted = {}
        for product_id, quantity in zip(request.form.getlist("product_id"), request.form.getlist("quantity")):
            if product_id and quantity and int(quantity) > 0:
                wanted[int(product_id)] = wanted.get(int(product_id), 0) + int(quantity)

        if not wanted:
            flash("Add at least one product to the order.", "danger")
            return redirect(url_for("admin.add_order"))

        order = Order(
            user_id=customer.id,
            tracking_code=Order.new_tracking_code(),
            payment_status=request.form.get("payment_status") if request.form.get("payment_status") in PAYMENT_STATUSES else "Pending",
            delivery_date=form_date("delivery_date")
        )

        total = 0

        for product_id, quantity in wanted.items():

            product = db.session.get(Product, product_id)

            if not product:
                continue

            if product.stock < quantity:
                db.session.rollback()
                flash(f"Only {product.stock} of {product.name} left in stock.", "danger")
                return redirect(url_for("admin.add_order"))

            product.stock -= quantity
            subtotal = product.price * quantity
            total += subtotal

            order.items.append(OrderItem(
                product_id=product.id,
                quantity=quantity,
                price=product.price,
                subtotal=subtotal
            ))

        order.total = total

        db.session.add(order)
        db.session.commit()

        flash(f"Order {order.tracking_code} created.", "success")

        return redirect(url_for("admin.order_detail", order_id=order.id))

    return render_template(
        "admin/order_form.html",
        customers=customers,
        products=products,
        payment_statuses=PAYMENT_STATUSES
    )


@admin_bp.route("/orders/<int:order_id>", methods=["GET", "POST"])
@section_required("shop")
def order_detail(order_id):

    order = db.get_or_404(Order, order_id)

    if request.method == "POST":

        new_status = request.form.get("order_status")
        new_payment = request.form.get("payment_status")

        if order.order_status == "Cancelled" and new_status != "Cancelled":
            flash("A cancelled order cannot be reopened. Create a new order instead.", "warning")
            return redirect(url_for("admin.order_detail", order_id=order.id))

        if new_status == "Cancelled" and order.order_status != "Cancelled":
            for item in order.items:
                if item.product:
                    old_stock = item.product.stock
                    item.product.stock += item.quantity
                    notify_if_restocked(item.product, old_stock)

        status_changed = new_status in ORDER_STATUSES and new_status != order.order_status
        paid_now = new_payment == "Paid" and order.payment_status != "Paid"

        if new_status in ORDER_STATUSES:
            order.order_status = new_status

        if new_payment in PAYMENT_STATUSES:
            order.payment_status = new_payment

        messages = {
            "Ready": (f"Order {order.tracking_code} is ready", "Your order is ready for collection or delivery."),
            "Delivered": (f"Order {order.tracking_code} delivered", "Thank you for shopping with Fortune Needles!"),
            "Cancelled": (f"Order {order.tracking_code} was cancelled", "Contact us if you have any questions."),
        }
        if status_changed and order.order_status in messages:
            title, message = messages[order.order_status]
            alert_customer(order.customer, "order", title, message, url_for("customer.dashboard"))
        if paid_now:
            alert_customer(order.customer, "order", f"Payment received for {order.tracking_code}",
                           f"We've received KES {order.total:,.0f}. Thank you!", url_for("customer.dashboard"))

        order.delivery_date = form_date("delivery_date")

        db.session.commit()

        flash("Order updated.", "success")

        return redirect(url_for("admin.order_detail", order_id=order.id))

    return render_template(
        "admin/order_detail.html",
        order=order,
        statuses=ORDER_STATUSES,
        payment_statuses=PAYMENT_STATUSES
    )


@admin_bp.route("/orders/<int:order_id>/delete", methods=["POST"])
@section_required("shop")
def delete_order(order_id):

    order = db.get_or_404(Order, order_id)

    if order.order_status != "Cancelled":
        flash("Only cancelled orders can be deleted. Cancel it first.", "warning")
        return redirect(url_for("admin.order_detail", order_id=order.id))

    db.session.delete(order)
    db.session.commit()

    flash(f"Order {order.tracking_code} deleted.", "success")

    return redirect(url_for("admin.admin_orders"))
