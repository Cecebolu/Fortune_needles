from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import Product, StockAlert
from notify import notify_if_restocked
from routes.admin import admin_bp, section_required, save_image, delete_image


def fill_product_from_form(product):

    product.name = request.form.get("name")
    product.description = request.form.get("description")
    product.category = request.form.get("category")
    product.price = float(request.form.get("price") or 0)
    product.stock = max(int(request.form.get("stock") or 0), 0)
    product.is_available = request.form.get("is_available") == "on"


def replace_product_image(product):
    """Save a newly uploaded image, if any. Returns False if the file type is not allowed."""

    image = request.files.get("image")

    if not image or not image.filename:
        return True

    filename = save_image(image, "products")

    if not filename:
        return False

    delete_image(product.image, "products")
    product.image = filename

    return True


@admin_bp.route("/products")
@section_required("shop")
def admin_products():

    products = Product.query.order_by(Product.created_at.desc()).all()

    return render_template("admin/products.html", products=products)


@admin_bp.route("/products/add", methods=["GET", "POST"])
@section_required("shop")
def add_product():

    if request.method == "POST":

        product = Product()
        fill_product_from_form(product)

        if not replace_product_image(product):
            flash("Image must be png, jpg, jpeg, gif or webp.", "warning")
            return redirect(url_for("admin.add_product"))

        db.session.add(product)
        db.session.commit()

        flash("Product added successfully.", "success")

        return redirect(url_for("admin.admin_products"))

    return render_template("admin/add_product.html")


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@section_required("shop")
def edit_product(product_id):

    product = db.get_or_404(Product, product_id)

    if request.method == "POST":

        old_stock = product.stock
        fill_product_from_form(product)

        if not replace_product_image(product):
            flash("Image must be png, jpg, jpeg, gif or webp.", "warning")
            return redirect(url_for("admin.edit_product", product_id=product.id))

        told = notify_if_restocked(product, old_stock)
        db.session.commit()

        flash("Product updated successfully." + (f" {told} waiting customer(s) told it's back." if told else ""), "success")

        return redirect(url_for("admin.admin_products"))

    waiting = StockAlert.query.filter_by(product_id=product.id).order_by(
        StockAlert.notified_at.isnot(None), StockAlert.created_at.desc()
    ).all()

    return render_template("admin/edit_product.html", product=product, waiting=waiting)


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@section_required("shop")
def delete_product(product_id):

    product = db.get_or_404(Product, product_id)

    if product.order_items:
        product.is_available = False
        flash("Product has orders, so it was hidden from the shop instead of deleted.", "warning")
    else:
        delete_image(product.image, "products")
        db.session.delete(product)
        flash("Product deleted.", "success")

    db.session.commit()

    return redirect(url_for("admin.admin_products"))


@admin_bp.route("/products/<int:product_id>/visibility", methods=["POST"])
@section_required("shop")
def toggle_product_visibility(product_id):

    product = db.get_or_404(Product, product_id)
    product.is_available = not product.is_available
    db.session.commit()

    flash(f"{product.name} is now {'shown in' if product.is_available else 'hidden from'} the shop.", "success")

    return redirect(url_for("admin.admin_products"))


@admin_bp.route("/products/<int:product_id>/stock", methods=["POST"])
@section_required("shop")
def update_stock(product_id):

    product = db.get_or_404(Product, product_id)
    old_stock = product.stock
    product.stock = max(request.form.get("stock", product.stock, type=int), 0)
    told = notify_if_restocked(product, old_stock)
    db.session.commit()

    flash(f"{product.name} stock set to {product.stock}." + (f" {told} waiting customer(s) told it's back." if told else ""), "success")

    return redirect(url_for("admin.admin_products"))
