import os
from datetime import datetime
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest

from app import create_app
from app.extensions import db
from app.models.cash_account import CashAccount
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.services.cash_account_service import (
    deposit,
    normalize_amount,
    withdraw,
)


SIMULATED_TIME = datetime(
    2026,
    9,
    22,
    10,
    0,
    0,
)


@pytest.fixture
def app():
    app = create_app()

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def create_customer(balance=Decimal("1000.00")):
    customer = Customer(
        full_name="Cash Test Customer",
        username="cashuser",
        email="cash@example.com",
        password_hash="test-password-hash",
        is_admin=False,
    )

    db.session.add(customer)
    db.session.flush()

    cash_account = CashAccount(
        customer_id=customer.id,
        balance=balance,
    )

    db.session.add(cash_account)
    db.session.commit()

    return customer, cash_account


def test_deposit_increases_balance(app, monkeypatch):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.cash_account_service.get_simulated_datetime",
            lambda: SIMULATED_TIME,
        )

        customer, cash_account = create_customer()

        transaction = deposit(
            customer.id,
            "250.00",
        )

        assert cash_account.balance == Decimal("1250.00")
        assert transaction.transaction_type == "Deposit"
        assert transaction.amount == Decimal("250.00")
        assert (
            transaction.resulting_cash_balance
            == Decimal("1250.00")
        )
        assert transaction.transaction_date == SIMULATED_TIME


def test_withdrawal_decreases_balance(app, monkeypatch):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.cash_account_service.get_simulated_datetime",
            lambda: SIMULATED_TIME,
        )

        customer, cash_account = create_customer()

        transaction = withdraw(
            customer.id,
            "300.00",
        )

        assert cash_account.balance == Decimal("700.00")
        assert transaction.transaction_type == "Withdrawal"
        assert transaction.amount == Decimal("-300.00")
        assert (
            transaction.resulting_cash_balance
            == Decimal("700.00")
        )


def test_withdrawal_rejects_insufficient_balance(app):
    with app.app_context():
        customer, cash_account = create_customer(
            Decimal("100.00")
        )

        with pytest.raises(
            ValueError,
            match="Insufficient cash balance",
        ):
            withdraw(
                customer.id,
                "150.00",
            )

        assert cash_account.balance == Decimal("100.00")

        transaction = Transaction.query.filter_by(
            customer_id=customer.id,
            transaction_type="Withdrawal",
        ).first()

        assert transaction is None


def test_zero_amount_rejected(app):
    with app.app_context():
        customer, _ = create_customer()

        with pytest.raises(
            ValueError,
            match="Amount must be greater than zero",
        ):
            deposit(
                customer.id,
                "0",
            )


def test_negative_amount_rejected(app):
    with app.app_context():
        customer, _ = create_customer()

        with pytest.raises(
            ValueError,
            match="Amount must be greater than zero",
        ):
            withdraw(
                customer.id,
                "-50.00",
            )


def test_invalid_amount_rejected():
    with pytest.raises(
        ValueError,
        match="Amount must be a valid number",
    ):
        normalize_amount("not-money")