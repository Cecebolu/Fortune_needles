from flask import Flask
from config import Config
from extensions import db, login_manager, migrate

from routes.public import public_bp
from routes.auth import auth_bp
from routes.customer import customer_bp
from routes.admin import admin_bp

from models import User


def create_app():

    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please login to continue."

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp)

    return app


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


app = create_app()

with app.app_context():

    db.create_all()

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

        print("✓ Admin account created")


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=8080,
        debug=True
    )