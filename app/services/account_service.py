import re
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.cash_account import CashAccount
from app.models.customer import Customer


FULL_NAME_MAX_LENGTH = 100
USERNAME_MAX_LENGTH = 50
EMAIL_MAX_LENGTH = 120
PASSWORD_MIN_LENGTH = 8

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_full_name(full_name):
    full_name = str(full_name or "").strip()

    if not full_name:
        raise ValueError("Full name is required.")

    if len(full_name) > FULL_NAME_MAX_LENGTH:
        raise ValueError(
            f"Full name cannot exceed {FULL_NAME_MAX_LENGTH} characters."
        )

    return full_name


def normalize_username(username):
    username = str(username or "").strip()

    if not username:
        raise ValueError("Username is required.")

    if len(username) > USERNAME_MAX_LENGTH:
        raise ValueError(
            f"Username cannot exceed {USERNAME_MAX_LENGTH} characters."
        )

    if not USERNAME_PATTERN.match(username):
        raise ValueError(
            "Username can only contain letters, numbers, "
            "periods, hyphens and underscores."
        )

    return username


def normalize_email(email):
    email = str(email or "").strip().lower()

    if not email:
        raise ValueError("Email is required.")

    if len(email) > EMAIL_MAX_LENGTH:
        raise ValueError(
            f"Email cannot exceed {EMAIL_MAX_LENGTH} characters."
        )

    if not EMAIL_PATTERN.match(email):
        raise ValueError("Email must be a valid email address.")

    return email


def validate_password(password):
    password = str(password or "")

    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
        )

    return password


def username_taken(username):
    return (
        Customer.query
        .filter(func.lower(Customer.username) == username.lower())
        .first()
        is not None
    )


def email_taken(email):
    return (
        Customer.query
        .filter(func.lower(Customer.email) == email)
        .first()
        is not None
    )


def create_account(full_name, username, email, password):
    full_name = normalize_full_name(full_name)
    username = normalize_username(username)
    email = normalize_email(email)
    password = validate_password(password)

    # CUS-105: usernames are unique. Compare case-insensitively so
    # "Demo" can't be registered next to "demo".
    if username_taken(username):
        raise ValueError(
            "Username unavailable. Choose another username."
        )

    if email_taken(email):
        raise ValueError(
            "An account with that email already exists."
        )

    # New accounts are always customers. Administrators are
    # set up directly in the database, never through sign-up.
    customer = Customer(
        full_name=full_name,
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        is_admin=False,
    )

    db.session.add(customer)

    try:
        db.session.flush()

        # CUS-106: every customer gets one cash account
        cash_account = CashAccount(
            customer_id=customer.id,
            balance=Decimal("0.00"),
        )

        db.session.add(cash_account)
        db.session.commit()

    except IntegrityError:
        # Another request registered the same username first.
        db.session.rollback()

        raise ValueError(
            "Username unavailable. Choose another username."
        )

    return customer
