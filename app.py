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

from models import User, SiteSettings, CustomDesign, CustomerAlert, OLD_DESIGN_STATUSES


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

    return app


app = create_app()

def add_missing_columns():
    """create_all() only creates new tables, so add columns introduced after a table already existed."""

    new_columns = {
        "site_settings": {"order_whatsapp": "VARCHAR(30)"},
        "contact_messages": {"product_id": "INTEGER REFERENCES products(id) ON DELETE SET NULL"},
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


with app.app_context():

    db.create_all()
    add_missing_columns()
    rename_old_design_statuses()

    if not User.query.filter_by(username="admin").first():

        admin = User(
            first_name="System",
            last_name="Administrator",
            username="admin",
            email="admin@fortuneneedles.com",
            phone="0712345678",
            role="admin"
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