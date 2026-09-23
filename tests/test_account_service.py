import os
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest
from werkzeug.security import check_password_hash

from app import create_app
from app.extensions import db
from app.models.cash_account import CashAccount
from app.models.customer import Customer
from app.services.account_service import create_account


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def register(**overrides):
    values = {
        "full_name": "New Customer",
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "Password123!",
    }
    values.update(overrides)

    return create_account(**values)


def test_create_account_creates_customer_and_cash_account(app):
    customer = register()

    assert customer.id is not None
    assert customer.full_name == "New Customer"
    assert customer.username == "newuser"
    assert customer.email == "newuser@example.com"
    assert customer.is_admin is False

    cash_account = CashAccount.query.filter_by(
        customer_id=customer.id
    ).one()

    assert cash_account.balance == Decimal("0.00")


def test_create_account_hashes_password(app):
    customer = register()

    assert customer.password_hash != "Password123!"
    assert check_password_hash(
        customer.password_hash,
        "Password123!",
    )


def test_create_account_trims_input_and_lowercases_email(app):
    customer = register(
        full_name="  Spaced Name  ",
        username="  spaced  ",
        email="  Mixed.Case@Example.COM ",
    )

    assert customer.full_name == "Spaced Name"
    assert customer.username == "spaced"
    assert customer.email == "mixed.case@example.com"


def test_create_account_rejects_taken_username(app):
    register()

    with pytest.raises(ValueError, match="Username unavailable"):
        register(email="other@example.com")

    assert Customer.query.count() == 1


def test_create_account_rejects_taken_username_any_case(app):
    register()

    with pytest.raises(ValueError, match="Username unavailable"):
        register(
            username="NewUser",
            email="other@example.com",
        )


def test_create_account_rejects_taken_email(app):
    register()

    with pytest.raises(ValueError, match="email already exists"):
        register(
            username="otheruser",
            email="NEWUSER@example.com",
        )


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("full_name", "", "Full name is required."),
        ("full_name", "x" * 101, "cannot exceed 100"),
        ("username", "", "Username is required."),
        ("username", "x" * 51, "cannot exceed 50"),
        ("username", "has space", "can only contain"),
        ("email", "", "Email is required."),
        ("email", "not-an-email", "valid email"),
        ("password", "short", "at least 8"),
        ("password", None, "at least 8"),
    ],
)
def test_create_account_validates_fields(app, field, value, message):
    with pytest.raises(ValueError, match=message):
        register(**{field: value})

    assert Customer.query.count() == 0
    assert CashAccount.query.count() == 0
