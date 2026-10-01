class Config:
    SECRET_KEY = "fortune_needles_secret_key"

    SQLALCHEMY_DATABASE_URI = (
        "postgresql://postgres:happycrm%402026@localhost:5432/fortune_needles"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = "static/uploads"

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    