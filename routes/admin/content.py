from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import AboutPage, Service, Gallery, SiteSettings, ContactMessage
from routes.admin import admin_bp, admin_required, save_image, delete_image, form_float

SERVICE_ICONS = [
    "bi-scissors", "bi-rulers", "bi-gem", "bi-palette", "bi-person-standing-dress",
    "bi-briefcase", "bi-stars", "bi-heart", "bi-bag", "bi-brush",
]

SOCIAL_FIELDS = ["facebook", "instagram", "whatsapp", "tiktok"]


def clean(name):
    return (request.form.get(name) or "").strip()


# ==========================================
# HOME PAGE
# ==========================================

@admin_bp.route("/home", methods=["GET", "POST"])
@admin_required
def admin_home():

    settings = SiteSettings.get()

    if request.method == "POST":

        settings.hero_tagline = clean("hero_tagline")
        settings.hero_title = clean("hero_title").replace("\r\n", "\n")
        settings.hero_text = clean("hero_text").replace("\r\n", "\n")
        settings.hero_button_text = clean("hero_button_text") or "Explore Collection"

        db.session.commit()

        flash("Home page updated.", "success")

        return redirect(url_for("admin.admin_home"))

    return render_template("admin/manage_home.html", settings=settings)


# ==========================================
# ABOUT PAGE
# ==========================================

@admin_bp.route("/about", methods=["GET", "POST"])
@admin_required
def admin_about():

    about = AboutPage.get()

    if request.method == "POST":

        about.title = request.form.get("title")
        about.subtitle = request.form.get("subtitle")
        about.description = (request.form.get("description") or "").replace("\r\n", "\n")

        db.session.commit()

        flash("About page updated.", "success")

        return redirect(url_for("admin.admin_about"))

    return render_template("admin/about.html", about=about)


# ==========================================
# SERVICES
# ==========================================

def fill_service_from_form(service):

    service.name = clean("name")
    service.description = clean("description")
    service.icon = request.form.get("icon") if request.form.get("icon") in SERVICE_ICONS else "bi-scissors"
    service.starting_price = form_float("starting_price")
    service.is_active = request.form.get("is_active") == "on"


@admin_bp.route("/services", methods=["GET", "POST"])
@admin_required
def admin_services():

    Service.active()  # creates the starter services the first time

    if request.method == "POST":

        service = Service(position=Service.query.count())
        fill_service_from_form(service)

        if not service.name:
            flash("Service name is required.", "danger")
            return redirect(url_for("admin.admin_services"))

        db.session.add(service)
        db.session.commit()

        flash(f"Service \"{service.name}\" added.", "success")

        return redirect(url_for("admin.admin_services"))

    return render_template(
        "admin/services.html",
        services=Service.query.order_by(Service.position, Service.id).all(),
        icons=SERVICE_ICONS,
        editing=db.session.get(Service, request.args.get("edit", type=int) or 0)
    )


@admin_bp.route("/services/add")
@admin_required
def add_service():
    return redirect(url_for("admin.admin_services") + "#add-service")


@admin_bp.route("/services/<int:service_id>/edit", methods=["POST"])
@admin_required
def edit_service(service_id):

    service = db.get_or_404(Service, service_id)
    fill_service_from_form(service)

    if not service.name:
        db.session.rollback()
        flash("Service name is required.", "danger")
        return redirect(url_for("admin.admin_services", edit=service_id))

    db.session.commit()

    flash(f"Service \"{service.name}\" updated.", "success")

    return redirect(url_for("admin.admin_services"))


@admin_bp.route("/services/<int:service_id>/move/<direction>", methods=["POST"])
@admin_required
def move_service(service_id, direction):

    services = Service.query.order_by(Service.position, Service.id).all()
    index = next((i for i, s in enumerate(services) if s.id == service_id), None)
    other = (index - 1) if direction == "up" else (index + 1)

    if index is not None and 0 <= other < len(services):
        services[index], services[other] = services[other], services[index]
        for position, service in enumerate(services):
            service.position = position
        db.session.commit()

    return redirect(url_for("admin.admin_services"))


@admin_bp.route("/services/<int:service_id>/delete", methods=["POST"])
@admin_required
def delete_service(service_id):

    service = db.get_or_404(Service, service_id)

    db.session.delete(service)
    db.session.commit()

    flash(f"Service \"{service.name}\" deleted.", "success")

    return redirect(url_for("admin.admin_services"))


# ==========================================
# GALLERY
# ==========================================

@admin_bp.route("/gallery", methods=["GET", "POST"])
@admin_required
def add_gallery():

    if request.method == "POST":

        files = [f for f in request.files.getlist("images") if f and f.filename]

        if not files:
            flash("Choose at least one image to upload.", "danger")
            return redirect(url_for("admin.add_gallery"))

        saved = 0

        for file in files:

            filename = save_image(file, "gallery")

            if filename:
                db.session.add(Gallery(
                    title=clean("title") or None,
                    category=clean("category") or None,
                    description=clean("description") or None,
                    image=filename
                ))
                saved += 1

        db.session.commit()

        skipped = len(files) - saved

        if saved:
            flash(f"{saved} image{'s' if saved != 1 else ''} uploaded.", "success")
        if skipped:
            flash(f"{skipped} file{'s' if skipped != 1 else ''} skipped: only png, jpg, jpeg, gif or webp allowed.", "warning")

        return redirect(url_for("admin.add_gallery"))

    return render_template(
        "admin/gallery.html",
        images=Gallery.query.order_by(Gallery.created_at.desc()).all()
    )


@admin_bp.route("/gallery/<int:image_id>/delete", methods=["POST"])
@admin_required
def delete_gallery(image_id):

    item = db.get_or_404(Gallery, image_id)

    delete_image(item.image, "gallery")
    db.session.delete(item)
    db.session.commit()

    flash("Image deleted.", "success")

    return redirect(url_for("admin.add_gallery"))


# ==========================================
# CONTACT INFO
# ==========================================

@admin_bp.route("/contact", methods=["GET", "POST"])
@admin_required
def admin_contact():

    settings = SiteSettings.get()

    if request.method == "POST":

        settings.phone = clean("phone")
        settings.email = clean("email")
        settings.location = clean("location")
        settings.order_whatsapp = clean("order_whatsapp") or None

        for field in SOCIAL_FIELDS:
            setattr(settings, field, clean(field) or None)

        db.session.commit()

        flash("Contact information updated.", "success")

        return redirect(url_for("admin.admin_contact"))

    return render_template("admin/contact.html", settings=settings)


# ==========================================
# MESSAGES (from the public contact form)
# ==========================================

@admin_bp.route("/messages")
@admin_required
def admin_messages():

    show = request.args.get("show", "all")

    query = ContactMessage.query

    if show == "unread":
        query = query.filter_by(is_read=False)

    messages = query.order_by(ContactMessage.created_at.desc()).all()

    selected = db.session.get(ContactMessage, request.args.get("open", type=int) or 0)

    if selected and not selected.is_read:
        selected.is_read = True
        db.session.commit()

    return render_template(
        "admin/messages.html",
        messages=messages,
        selected=selected,
        show=show
    )


@admin_bp.route("/messages/<int:message_id>/unread", methods=["POST"])
@admin_required
def mark_message_unread(message_id):

    message = db.get_or_404(ContactMessage, message_id)
    message.is_read = False
    db.session.commit()

    return redirect(url_for("admin.admin_messages"))


@admin_bp.route("/messages/<int:message_id>/delete", methods=["POST"])
@admin_required
def delete_message(message_id):

    message = db.get_or_404(ContactMessage, message_id)

    db.session.delete(message)
    db.session.commit()

    flash("Message deleted.", "success")

    return redirect(url_for("admin.admin_messages"))
