from urllib.parse import quote

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user

from extensions import db
from models import Product, Order, OrderItem, Notification, SiteSettings
from utils import whatsapp_digits

cart_bp = Blueprint("cart", __name__, url_prefix="/cart")


# ==========================================
# HELPERS
# ==========================================

def get_cart():
    """The cart lives in the session as {"product_id": quantity}."""
    return session.get("cart", {})


def save_cart(cart):
    session["cart"] = {pid: qty for pid, qty in cart.items() if qty > 0}
    session.modified = True


def cart_lines():
    """Products in the cart with their quantity and subtotal. Drops products that no longer exist."""

    cart = get_cart()
    products = Product.query.filter(Product.id.in_([int(pid) for pid in cart])).all() if cart else []

    lines = [
        {"product": p, "quantity": cart[str(p.id)], "subtotal": p.price * cart[str(p.id)]}
        for p in products
    ]

    if len(lines) != len(cart):
        save_cart({str(line["product"].id): line["quantity"] for line in lines})

    return sorted(lines, key=lambda line: line["product"].name)


def cart_count():
    return sum(get_cart().values())


def whatsapp_number(settings):
    return whatsapp_digits(settings.order_whatsapp or settings.phone)


def whatsapp_message(order):

    lines = [
        "Hello Fortune Needles! I would like to place an order.",
        "",
        f"Order: {order.tracking_code}",
    ]
    lines += [
        f"- {item.quantity} x {item.product.name} = KES {item.subtotal:,.0f}"
        for item in order.items
    ]
    lines += [
        f"Total: KES {order.total:,.0f}",
        "",
        f"Name: {order.customer.first_name} {order.customer.last_name}",
        f"Phone: {order.customer.phone}",
    ]

    return "\n".join(lines)


# ==========================================
# CART (customers only: log in first)
# ==========================================

@cart_bp.before_request
def require_customer_login():

    if not current_user.is_authenticated:
        flash("Please log in to use your cart.", "info")
        return redirect(url_for("auth.login", next=url_for("public.shop")))

    if current_user.role == "admin":
        flash("Admins record orders from the admin panel.", "info")
        return redirect(url_for("admin.add_order"))


@cart_bp.route("/")
def view_cart():

    lines = cart_lines()

    return render_template(
        "cart.html",
        lines=lines,
        total=sum(line["subtotal"] for line in lines)
    )


@cart_bp.route("/add/<int:product_id>", methods=["POST"])
def add(product_id):

    product = db.get_or_404(Product, product_id)
    quantity = max(request.form.get("quantity", 1, type=int) or 1, 1)

    cart = get_cart()
    in_cart = cart.get(str(product.id), 0)

    if not product.is_available:
        flash(f"{product.name} is no longer available.", "warning")
    elif not product.in_stock:
        flash(f"{product.name} is out of stock.", "warning")
    elif in_cart + quantity > product.stock:
        cart[str(product.id)] = product.stock
        save_cart(cart)
        flash(f"Only {product.stock} {product.name} in stock. Your cart has the maximum.", "warning")
    else:
        cart[str(product.id)] = in_cart + quantity
        save_cart(cart)
        flash(f"{product.name} added to your cart.", "success")

    return redirect(url_for("public.shop"))


@cart_bp.route("/update", methods=["POST"])
def update():

    cart = {}

    for line in cart_lines():
        product = line["product"]
        quantity = request.form.get(f"quantity_{product.id}", line["quantity"], type=int) or 0
        cart[str(product.id)] = max(0, min(quantity, product.stock))

    save_cart(cart)
    flash("Cart updated.", "success")

    return redirect(url_for("cart.view_cart"))


@cart_bp.route("/remove/<int:product_id>", methods=["POST"])
def remove(product_id):

    cart = get_cart()
    cart.pop(str(product_id), None)
    save_cart(cart)

    return redirect(url_for("cart.view_cart"))


# ==========================================
# CHECKOUT ON WHATSAPP
# ==========================================

@cart_bp.route("/checkout", methods=["POST"])
def checkout():

    lines = cart_lines()

    if not lines:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("public.shop"))

    for line in lines:
        product = line["product"]
        if not product.is_available or product.stock < line["quantity"]:
            message = (f"Sorry, {product.name} is out of stock." if product.is_available and not product.in_stock
                       else f"Sorry, {product.name} is no longer available." if not product.is_available
                       else f"Sorry, only {product.stock} {product.name} left.")
            flash(message + " Please update your cart.", "warning")
            return redirect(url_for("cart.view_cart"))

    order = Order(user_id=current_user.id, tracking_code=Order.new_tracking_code())

    for line in lines:
        product = line["product"]
        product.stock -= line["quantity"]
        order.items.append(OrderItem(
            product_id=product.id,
            quantity=line["quantity"],
            price=product.price,
            subtotal=line["subtotal"]
        ))

    order.total = sum(line["subtotal"] for line in lines)

    db.session.add(order)
    db.session.flush()

    item_count = sum(line["quantity"] for line in lines)
    Notification.add(
        "order",
        "New order placed",
        f"{current_user.first_name} {current_user.last_name}: {item_count} item{'s' if item_count != 1 else ''} "
        f"(KES {order.total:,.0f}), sent on WhatsApp",
        url_for("admin.order_detail", order_id=order.id)
    )

    db.session.commit()

    save_cart({})

    return redirect(url_for("cart.order_sent", order_id=order.id))


@cart_bp.route("/sent/<int:order_id>")
@login_required
def order_sent(order_id):

    order = db.get_or_404(Order, order_id)

    if order.user_id != current_user.id:
        return redirect(url_for("customer.dashboard"))

    number = whatsapp_number(SiteSettings.get())
    whatsapp_url = f"https://wa.me/{number}?text={quote(whatsapp_message(order))}" if number else None

    return render_template("order_sent.html", order=order, whatsapp_url=whatsapp_url)
