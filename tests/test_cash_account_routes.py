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
    username="cashroute",
    email="cashroute@example.com",
    balance=Decimal("1000.00"),
):
    customer = Customer(
        full_name="Cash Route Customer",
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


def login_customer(client, customer):
    with client.session_transaction() as session:
        session["customer_id"] = customer.id


def test_cash_balance_requires_authentication(client):
    response = client.get("/cash")

    assert response.status_code == 401
    assert (
        response.get_json()["error"]
        == "Authentication required."
    )


def test_cash_balance_returns_logged_in_customer(
    app,
    client,
):
    with app.app_context():
        customer = create_customer()

        login_customer(
            client,
            customer,
        )

        response = client.get("/cash")

        assert response.status_code == 200

        data = response.get_json()

        assert data["customer_id"] == customer.id
        assert data["balance"] == "1000.00"


def test_deposit_route(
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

        login_customer(
            client,
            customer,
        )

        response = client.post(
            "/cash/deposit",
            json={
                "amount": "250.00",
            },
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data["message"] == "Deposit completed."
        assert (
            data["transaction"]["transaction_type"]
            == "Deposit"
        )
        assert data["transaction"]["amount"] == "250.00"
        assert (
            data["transaction"]["resulting_cash_balance"]
            == "1250.00"
        )


def test_withdraw_route(
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

        login_customer(
            client,
            customer,
        )

        response = client.post(
            "/cash/withdraw",
            json={
                "amount": "300.00",
            },
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data["message"] == "Withdrawal completed."
        assert (
            data["transaction"]["transaction_type"]
            == "Withdrawal"
        )
        assert data["transaction"]["amount"] == "-300.00"
        assert (
            data["transaction"]["resulting_cash_balance"]
            == "700.00"
        )


def test_withdraw_route_rejects_insufficient_balance(
    app,
    client,
):
    with app.app_context():
        customer = create_customer(
            balance=Decimal("100.00")
        )

        login_customer(
            client,
            customer,
        )

        response = client.post(
            "/cash/withdraw",
            json={
                "amount": "500.00",
            },
        )

        assert response.status_code == 400

        assert (
            response.get_json()["error"]
            == "Insufficient cash balance."
        )


def test_deposit_route_rejects_invalid_amount(
    app,
    client,
):
    with app.app_context():
        customer = create_customer()

        login_customer(
            client,
            customer,
        )

        response = client.post(
            "/cash/deposit",
            json={
                "amount": "invalid",
            },
        )

        assert response.status_code == 400

        assert (
            response.get_json()["error"]
            == "Amount must be a valid number."
        )


def test_transactions_only_return_logged_in_customer(
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

        login_customer(
            client,
            customer,
        )

        client.post(
            "/cash/deposit",
            json={
                "amount": "100.00",
            },
        )

        other_customer = create_customer(
            username="othercash",
            email="othercash@example.com",
        )

        login_customer(
            client,
            other_customer,
        )

        client.post(
            "/cash/deposit",
            json={
                "amount": "500.00",
            },
        )

        response = client.get(
            "/cash/transactions"
        )

        assert response.status_code == 200

        transactions = response.get_json()[
            "transactions"
        ]

        assert len(transactions) == 1
        assert transactions[0]["amount"] == "500.00"


def test_transactions_require_authentication(client):
    response = client.get(
        "/cash/transactions"
    )

    assert response.status_code == 401