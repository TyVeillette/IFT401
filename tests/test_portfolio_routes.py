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
from app.models.portfolio_holding import PortfolioHolding
from app.models.stock import Stock
from app.services.cash_account_service import deposit


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
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def create_customer(
    username="portfolio",
    email="portfolio@example.com",
    balance=Decimal("1000.00"),
):
    customer = Customer(
        full_name="Portfolio Route Customer",
        username=username,
        email=email,
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

    return customer


def create_stock():
    stock = Stock(
        company_name="Portfolio Company",
        ticker="PORT",
        initial_price=Decimal("100.00"),
        current_price=Decimal("100.00"),
        open_price=Decimal("100.00"),
        high_price=Decimal("100.00"),
        low_price=Decimal("100.00"),
        volume=1000,
        is_active=True,
    )

    db.session.add(stock)
    db.session.commit()

    return stock


def login_customer(client, customer):
    with client.session_transaction() as session:
        session["customer_id"] = customer.id


def test_portfolio_requires_authentication(client):
    response = client.get(
        "/portfolio"
    )

    assert response.status_code == 401

    assert (
        response.get_json()["error"]
        == "Authentication required."
    )


def test_portfolio_summary(app, client):
    with app.app_context():
        customer = create_customer()
        stock = create_stock()

        holding = PortfolioHolding(
            customer_id=customer.id,
            stock_id=stock.id,
            share_quantity=5,
        )

        db.session.add(holding)
        db.session.commit()

        login_customer(
            client,
            customer,
        )

        response = client.get(
            "/portfolio"
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["cash_balance"] == "1000.00"
        assert data["total_market_value"] == "500.00"
        assert data["total_account_value"] == "1500.00"

        assert len(data["holdings"]) == 1

        assert (
            data["holdings"][0]["ticker"]
            == "PORT"
        )

        assert (
            data["holdings"][0]["share_quantity"]
            == 5
        )


def test_transaction_history_requires_authentication(
    client,
):
    response = client.get(
        "/portfolio/transactions"
    )

    assert response.status_code == 401


def test_transaction_history_only_returns_customer(
    app,
    client,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.cash_account_service.get_simulated_datetime",
            lambda: SIMULATED_TIME,
        )

        customer = create_customer()

        deposit(
            customer.id,
            Decimal("100.00"),
        )

        other_customer = create_customer(
            username="otherportfolio",
            email="otherportfolio@example.com",
        )

        deposit(
            other_customer.id,
            Decimal("500.00"),
        )

        login_customer(
            client,
            customer,
        )

        response = client.get(
            "/portfolio/transactions"
        )

        assert response.status_code == 200

        transactions = response.get_json()[
            "transactions"
        ]

        assert len(transactions) == 1

        assert (
            transactions[0]["transaction_type"]
            == "Deposit"
        )

        assert transactions[0]["amount"] == "100.00"