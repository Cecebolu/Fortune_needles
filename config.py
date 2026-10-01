import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Optional: email for password reset links (e.g. Gmail with an app password)
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = os.environ.get("MAIL_PORT", "587")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_FROM = os.environ.get("MAIL_FROM")
