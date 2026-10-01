from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

# Login settings
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "info"