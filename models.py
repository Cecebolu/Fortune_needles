from datetime import datetime

from flask_login import UserMixin

from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# =====================================================
# USER MODEL
# =====================================================

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)

    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)

    password_hash= db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), default="customer")

    profile_picture = db.Column(
        db.String(255),
        default="default.png"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # ---------------- PASSWORD METHODS ----------------

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ---------------- RELATIONSHIPS ----------------

    appointments = db.relationship(
        "Appointment",
        backref="customer",
        lazy=True,
        cascade="all, delete-orphan"
    )

    measurements = db.relationship(
        "Measurement",
        backref="customer",
        uselist=False,
        cascade="all, delete-orphan"
    )

    custom_designs = db.relationship(
        "CustomDesign",
        backref="customer",
        lazy=True,
        cascade="all, delete-orphan"
    )

    orders = db.relationship(
        "Order",
        backref="customer",
        lazy=True,
        cascade="all, delete-orphan"
    )

    reviews = db.relationship(
        "Review",
        backref="customer",
        lazy=True,
        cascade="all, delete-orphan"
    )

    sent_messages = db.relationship(
        "ChatMessage",
        foreign_keys="ChatMessage.sender_id",
        backref="sender",
        lazy=True
    )

    received_messages = db.relationship(
        "ChatMessage",
        foreign_keys="ChatMessage.receiver_id",
        backref="receiver",
        lazy=True
    )

    def __repr__(self):
        return f"<User {self.username}>"


# =====================================================
# PRODUCT MODEL
# =====================================================

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(150), nullable=False)

    description = db.Column(db.Text)

    category = db.Column(db.String(100))

    price = db.Column(db.Float, nullable=False)

    stock = db.Column(db.Integer, default=0)

    image = db.Column(db.String(255))

    is_available = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    order_items = db.relationship(
        "OrderItem",
        backref="product",
        lazy=True
    )

    reviews = db.relationship(
        "Review",
        backref="product",
        lazy=True
    )

    LOW_STOCK = 3

    @property
    def in_stock(self):
        return (self.stock or 0) > 0

    @property
    def stock_status(self):
        """(label, colour) shown to the admin. `is_available` only means "show in shop"."""

        if not self.is_available:
            return ("Hidden", "secondary")
        if not self.in_stock:
            return ("Out of Stock", "danger")
        if self.stock <= self.LOW_STOCK:
            return ("Low Stock", "warning")
        return ("In Stock", "success")

    def __repr__(self):
        return f"<Product {self.name}>"


# =====================================================
# GALLERY MODEL
# =====================================================

class Gallery(db.Model):
    __tablename__ = "gallery"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(150))

    category = db.Column(db.String(100))

    description = db.Column(db.Text)

    image = db.Column(db.String(255))

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def __repr__(self):
        return f"<Gallery {self.title}>"


# =====================================================
# APPOINTMENTS
# =====================================================

class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    appointment_date = db.Column(
        db.Date,
        nullable=False
    )

    appointment_time = db.Column(
        db.Time,
        nullable=False
    )

    service = db.Column(
        db.String(100)
    )

    phone = db.Column(
        db.String(20)
    )

    location = db.Column(
        db.String(150)
    )

    notes = db.Column(db.Text)

    status = db.Column(
        db.String(50),
        default="Pending"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =====================================================
# MEASUREMENTS
# =====================================================

class Measurement(db.Model):
    __tablename__ = "measurements"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        unique=True
    )

    chest = db.Column(db.Float)

    waist = db.Column(db.Float)

    hips = db.Column(db.Float)

    shoulder = db.Column(db.Float)

    sleeve = db.Column(db.Float)

    neck = db.Column(db.Float)

    inseam = db.Column(db.Float)

    height = db.Column(db.Float)

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

# =====================================================
# CUSTOM DESIGN REQUESTS
# =====================================================

class CustomDesign(db.Model):
    __tablename__ = "custom_designs"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    clothing_type = db.Column(db.String(100))

    color = db.Column(db.String(100))

    fabric = db.Column(db.String(100))

    size = db.Column(db.String(20))

    description = db.Column(db.Text)

    front_image = db.Column(db.String(255))

    back_image = db.Column(db.String(255))

    fabric_image = db.Column(db.String(255))

    estimated_price = db.Column(db.Float)

    expected_completion = db.Column(db.Date)

    status = db.Column(
        db.String(50),
        default="Submitted"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def __repr__(self):
        return f"<CustomDesign {self.id}>"


# =====================================================
# ORDERS
# =====================================================

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    total = db.Column(
        db.Float,
        default=0
    )

    payment_status = db.Column(
        db.String(50),
        default="Pending"
    )

    order_status = db.Column(
        db.String(50),
        default="Received"
    )

    tracking_code = db.Column(
        db.String(50),
        unique=True
    )

    delivery_date = db.Column(db.Date)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    items = db.relationship(
        "OrderItem",
        backref="order",
        lazy=True,
        cascade="all, delete-orphan"
    )

    @classmethod
    def new_tracking_code(cls):
        import random
        import string

        while True:
            code = "FN-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

            if not cls.query.filter_by(tracking_code=code).first():
                return code

    def __repr__(self):
        return f"<Order {self.id}>"


# =====================================================
# ORDER ITEMS
# =====================================================

class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id")
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id")
    )

    quantity = db.Column(
        db.Integer,
        default=1
    )

    price = db.Column(db.Float)

    subtotal = db.Column(db.Float)

    def __repr__(self):
        return f"<OrderItem {self.id}>"


# =====================================================
# REVIEWS
# =====================================================

class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id")
    )

    rating = db.Column(db.Integer)

    comment = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def __repr__(self):
        return f"<Review {self.id}>"


# =====================================================
# CONTACT MESSAGES
# =====================================================

class ContactMessage(db.Model):
    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(150),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        nullable=False
    )

    phone = db.Column(db.String(20))

    subject = db.Column(db.String(200))

    message = db.Column(
        db.Text,
        nullable=False
    )

    is_read = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def __repr__(self):
        return f"<ContactMessage {self.name}>"


# =====================================================
# CHAT MESSAGES
# =====================================================

class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    receiver_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    is_read = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def __repr__(self):
        return f"<ChatMessage {self.id}>"

# =====================================================
# ABOUT PAGE CONTENT
# =====================================================

class AboutPage(db.Model):
    __tablename__ = "about_page"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(
        db.String(150),
        default="About Fortune Needles"
    )

    subtitle = db.Column(
        db.String(255),
        default="Crafting elegance through custom tailoring."
    )

    description = db.Column(
        db.Text,
        default=(
            "Fortune Needles is a tailoring house in Nakuru, Kenya. "
            "We make custom suits, dresses, kitenge and bridal wear, "
            "and offer alterations that give every garment a perfect fit."
        )
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    @classmethod
    def get(cls):
        about = cls.query.first()

        if about is None:
            about = cls()
            db.session.add(about)
            db.session.commit()

        return about

    def __repr__(self):
        return f"<AboutPage {self.title}>"


# =====================================================
# SERVICES
# =====================================================

class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(150), nullable=False)

    description = db.Column(db.Text)

    icon = db.Column(
        db.String(50),
        default="bi-scissors"
    )

    starting_price = db.Column(db.Float)

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    position = db.Column(
        db.Integer,
        default=0
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    DEFAULTS = [
        ("Custom Tailoring", "Suits, dresses and kitenge made to your exact measurements.", "bi-scissors"),
        ("Alterations", "Resizing, hemming and repairs that give your clothes a perfect fit.", "bi-rulers"),
        ("Bridal Fitting", "Gowns and bridal party outfits fitted for your big day.", "bi-gem"),
        ("Design Consultation", "Work with us to choose fabrics, colours and a style that suits you.", "bi-palette"),
    ]

    @classmethod
    def active(cls):
        services = cls.query.filter_by(is_active=True).order_by(cls.position, cls.id).all()

        if not services and cls.query.count() == 0:
            for position, (name, description, icon) in enumerate(cls.DEFAULTS):
                db.session.add(cls(name=name, description=description, icon=icon, position=position))
            db.session.commit()
            services = cls.query.order_by(cls.position, cls.id).all()

        return services

    def __repr__(self):
        return f"<Service {self.name}>"


# =====================================================
# SITE SETTINGS (contact details, social links, home page)
# =====================================================

class SiteSettings(db.Model):
    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True)

    phone = db.Column(db.String(50), default="+254 0114 725 119")
    email = db.Column(db.String(150), default="info@fortuneneedles.com")
    location = db.Column(db.String(200), default="Nakuru, Kenya")

    facebook = db.Column(db.String(255))
    instagram = db.Column(db.String(255))
    whatsapp = db.Column(db.String(255))
    tiktok = db.Column(db.String(255))

    # Number that receives shop orders on WhatsApp (falls back to `phone`)
    order_whatsapp = db.Column(db.String(30))

    hero_tagline = db.Column(db.String(150), default="Luxury Tailoring & Fashion")
    hero_title = db.Column(db.String(255), default="Tailored With Precision.\nCrafted For Confidence.")
    hero_text = db.Column(
        db.Text,
        default="From elegant gowns to executive suits, Fortune Needles brings your fashion ideas to life."
    )
    hero_button_text = db.Column(db.String(50), default="Explore Collection")

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    @classmethod
    def get(cls):
        settings = cls.query.first()

        if settings is None:
            settings = cls()
            db.session.add(settings)
            db.session.commit()

        return settings

    def __repr__(self):
        return "<SiteSettings>"


# =====================================================
# ADMIN NOTIFICATIONS
# =====================================================

class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)

    kind = db.Column(db.String(30), nullable=False)

    title = db.Column(db.String(150), nullable=False)

    message = db.Column(db.String(255))

    link = db.Column(db.String(255))

    is_read = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    ICONS = {
        "order": "bi-bag-check",
        "appointment": "bi-calendar-check",
        "design": "bi-scissors",
        "message": "bi-envelope",
        "customer": "bi-person-plus",
        "review": "bi-star-fill",
        "password": "bi-key-fill",
    }

    @property
    def icon(self):
        return self.ICONS.get(self.kind, "bi-bell")

    @classmethod
    def add(cls, kind, title, message=None, link=None):
        """Queue a notification for the admin. The caller commits the session."""
        notification = cls(kind=kind, title=title, message=message, link=link)
        db.session.add(notification)
        return notification

    def __repr__(self):
        return f"<Notification {self.kind}: {self.title}>"



# =====================================================
# DASHBOARD ALERTS A CUSTOMER HAS CLOSED
# =====================================================

class DismissedAlert(db.Model):
    __tablename__ = "dismissed_alerts"
    __table_args__ = (db.UniqueConstraint("user_id", "key"),)

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Describes the alert *and* its state, e.g. "appointment-4-Confirmed",
    # so a closed alert comes back only when something actually changes
    key = db.Column(db.String(120), nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
