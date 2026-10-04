from flask import Flask
from sqlalchemy import inspect, text

from config import Config
from extensions import db, login_manager, migrate

from routes.public import public_bp
from routes.auth import auth_bp
from routes.customer import customer_bp
from routes.admin import admin_bp
from routes.cart import cart_bp, cart_count

from flask_login import current_user

import re

from markupsafe import Markup, escape

from models import (User, SiteSettings, CustomDesign, CustomerAlert, OLD_DESIGN_STATUSES, AboutPage, FOUNDER_DEFAULTS,
                    OLD_WEBSITE_SECTIONS)


def create_app():

    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(cart_bp)

    @app.context_processor
    def inject_site_settings():
        unread_updates = 0
        if current_user.is_authenticated and current_user.role != "admin":
            unread_updates = CustomerAlert.query.filter_by(user_id=current_user.id, is_read=False).count()
        return {"site": SiteSettings.get(), "cart_count": cart_count(), "unread_updates": unread_updates}

    @app.template_filter("bold")
    def bold(text):
        """Escape text, then turn **words** into bold so admins can highlight a phrase."""
        return Markup(re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", str(escape(text))))

    return app


app = create_app()

def add_missing_columns():
    """create_all() only creates new tables, so add columns introduced after a table already existed."""

    new_columns = {
        "site_settings": {"order_whatsapp": "VARCHAR(30)"},
        "contact_messages": {"product_id": "INTEGER REFERENCES products(id) ON DELETE SET NULL"},
        "users": {"is_owner": "BOOLEAN DEFAULT FALSE", "permissions": "VARCHAR(100) DEFAULT ''"},
        "about_page": {
            "founder_heading": "VARCHAR(150)",
            "founder_name": "VARCHAR(150)",
            "founder_story": "TEXT",
            "founder_photo": "VARCHAR(255)",
        },
    }

    inspector = inspect(db.engine)

    for table, columns in new_columns.items():
        existing = {column["name"] for column in inspector.get_columns(table)}

        for name, sql_type in columns.items():
            if name not in existing:
                db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))
                print(f"Added column {table}.{name}")

    db.session.commit()


def rename_old_design_statuses():
    """Design requests used to have Reviewed / In Progress / Completed; map them onto the new stages."""

    for old, new in OLD_DESIGN_STATUSES.items():
        CustomDesign.query.filter_by(status=old).update({"status": new})

    db.session.commit()


def fill_founder_section():
    """The founder columns were added later, so give an existing About page the starting text once."""

    about = AboutPage.query.first()

    if about and about.founder_story is None:
        for field, value in FOUNDER_DEFAULTS.items():
            setattr(about, field, value)
        db.session.commit()


def make_first_admins_owners():
    """Admins made before staff permissions existed had full access; keep it by making them owners."""

    if not User.query.filter_by(role="admin", is_owner=True).first():
        User.query.filter_by(role="admin").update({"is_owner": True})
        db.session.commit()


def split_website_permission():
    """Staff who had the single "website" permission keep access to every website page."""

    for staff in User.query.filter(User.permissions.like("%website%")).all():
        sections = [s for s in staff.permissions.split(",") if s != "website"] + OLD_WEBSITE_SECTIONS
        staff.permissions = ",".join(dict.fromkeys(sections))

    db.session.commit()


with app.app_context():

    db.create_all()
    add_missing_columns()
    rename_old_design_statuses()
    fill_founder_section()
    make_first_admins_owners()
    split_website_permission()

    if not User.query.filter_by(username="admin").first():

        admin = User(
            first_name="System",
            last_name="Administrator",
            username="admin",
            email="admin@fortuneneedles.com",
            phone="0712345678",
            role="admin",
            is_owner=True
        )

        admin.set_password("Admin@123")

        db.session.add(admin)
        db.session.commit()

        print("Admin account created")


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=8080,
        debug=True
    )