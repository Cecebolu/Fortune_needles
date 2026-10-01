from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

from extensions import db
from sqlalchemy import func

from models import Product, Gallery, ContactMessage, AboutPage, Service, Notification, Review

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def home():

    testimonials = Review.query.filter(
        Review.rating >= 4,
        Review.comment.isnot(None),
        Review.comment != ""
    ).order_by(Review.created_at.desc()).limit(3).all()

    return render_template("index.html", testimonials=testimonials)


@public_bp.route("/about")
def about():
    return render_template("about.html", about=AboutPage.get())


@public_bp.route("/services")
def services():
    return render_template("services.html", services=Service.active())


@public_bp.route("/gallery")
def gallery():

    images = Gallery.query.order_by(Gallery.created_at.desc()).all()

    return render_template("gallery.html", images=images)


@public_bp.route("/shop")
def shop():

    products = Product.query.filter_by(is_available=True).order_by(
        (Product.stock > 0).desc(),
        Product.created_at.desc()
    ).all()

    ratings = {
        product_id: (float(average), count)
        for product_id, average, count in db.session.query(
            Review.product_id, func.avg(Review.rating), func.count(Review.id)
        ).filter(Review.product_id.isnot(None)).group_by(Review.product_id)
    }

    return render_template("shop.html", products=products, ratings=ratings)


def enquiry_product(product_id):
    """The shop item a message is about, if it is a real, visible product."""

    product = db.session.get(Product, product_id) if product_id else None
    return product if product and product.is_available else None


@public_bp.route("/contact", methods=["GET", "POST"])
def contact():

    product = enquiry_product(request.values.get("product", type=int))

    if request.method == "POST":

        if current_user.is_authenticated:
            name = f"{current_user.first_name} {current_user.last_name}"
            email = current_user.email
            phone = current_user.phone
        else:
            name = (request.form.get("name") or "").strip()
            email = (request.form.get("email") or "").strip()
            phone = (request.form.get("phone") or "").strip() or None

        subject = (request.form.get("subject") or "").strip()
        message = (request.form.get("message") or "").strip()

        if not (name and email and subject and message):
            flash("Please fill in all the required fields.", "danger")
            return redirect(url_for("public.contact", product=product.id if product else None))

        contact_message = ContactMessage(
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message,
            product_id=product.id if product else None
        )
        db.session.add(contact_message)
        db.session.flush()

        Notification.add(
            "message",
            "New contact message",
            f"{name}: {subject}" + (f" ({product.name})" if product and product.name not in subject else ""),
            url_for("admin.admin_messages", open=contact_message.id)
        )

        db.session.commit()

        flash("Thank you! Your message has been sent.", "success")

        return redirect(url_for("public.contact"))

    subject = ""
    if product:
        subject = (f"Tell me when {product.name} is back in stock"
                   if request.args.get("about") == "restock" or not product.in_stock
                   else f"Question about {product.name}")

    return render_template("contact.html", product=product, subject=subject)
