from datetime import datetime, timezone

from app.extensions import db


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # CUS-102
    full_name = db.Column(
        db.String(100),
        nullable=False
    )

    # CUS-103, CUS-105
    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True
    )

    # CUS-104
    email = db.Column(
        db.String(120),
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    is_admin = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    def __repr__(self):
        return f"<Customer {self.username}>"
