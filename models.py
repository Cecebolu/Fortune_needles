from datetime import datetime

from flask_login import UserMixin

from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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