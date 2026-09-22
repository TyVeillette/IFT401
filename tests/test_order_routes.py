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


SIMULATED_TIME = datetime(
    2026,
    9,
    21,
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
    username="routeuser",
    email="route@example.com",
    balance=Decimal("1000.00"),
):
    customer = Customer(
        full_name="Route Test Customer",
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


def create_stock():
    stock = Stock(
        company_name="Route Test Company",
        ticker="ROUT",
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


def test_buy_route_requires_authentication(client):
    response = client.post(
        "/orders/buy",
        json={
            "stock_id": 1,
            "quantity": 5,
        },
    )

    assert response.status_code == 401
    assert (
        response.get_json()["error"]
        == "Authentication required."
    )


def test_buy_route_uses_logged_in_customer(
    app,
    client,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.order_service.get_simulated_datetime",
            lambda: SIMULATED_TIME,
        )

        customer = create_customer()
        stock = create_stock()

        login_customer(client, customer)

        response = client.post(
            "/orders/buy",
            json={
                "stock_id": stock.id,
                "quantity": 5,
            },
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data["order"]["customer_id"] == customer.id
        assert data["order"]["order_type"] == "Buy"
        assert data["order"]["status"] == "Pending"


def test_customer_id_cannot_be_spoofed(
    app,
    client,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.order_service.get_simulated_datetime",
            lambda: SIMULATED_TIME,
        )

        customer = create_customer()

        other_customer = create_customer(
            username="other",
            email="other@example.com",
        )

        stock = create_stock()

        login_customer(client, customer)

        response = client.post(
            "/orders/buy",
            json={
                "customer_id": other_customer.id,
                "stock_id": stock.id,
                "quantity": 2,
            },
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data["order"]["customer_id"] == customer.id
        assert data["order"]["customer_id"] != other_customer.id


def test_sell_route_uses_logged_in_customer(
    app,
    client,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.order_service.get_simulated_datetime",
            lambda: SIMULATED_TIME,
        )

        customer = create_customer()
        stock = create_stock()

        holding = PortfolioHolding(
            customer_id=customer.id,
            stock_id=stock.id,
            share_quantity=10,
        )

        db.session.add(holding)
        db.session.commit()

        login_customer(client, customer)

        response = client.post(
            "/orders/sell",
            json={
                "stock_id": stock.id,
                "quantity": 4,
            },
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data["order"]["customer_id"] == customer.id
        assert data["order"]["order_type"] == "Sell"


def test_customer_can_cancel_own_order(
    app,
    client,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.order_service.get_simulated_datetime",
            lambda: SIMULATED_TIME,
        )

        customer = create_customer()
        stock = create_stock()

        login_customer(client, customer)

        response = client.post(
            "/orders/buy",
            json={
                "stock_id": stock.id,
                "quantity": 2,
            },
        )

        order_id = response.get_json()["order"]["id"]

        response = client.post(
            f"/orders/{order_id}/cancel"
        )

        assert response.status_code == 200
        assert (
            response.get_json()["order"]["status"]
            == "Cancelled"
        )


def test_customer_cannot_cancel_another_customers_order(
    app,
    client,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.order_service.get_simulated_datetime",
            lambda: SIMULATED_TIME,
        )

        owner = create_customer()
        stock = create_stock()

        login_customer(client, owner)

        response = client.post(
            "/orders/buy",
            json={
                "stock_id": stock.id,
                "quantity": 2,
            },
        )

        order_id = response.get_json()["order"]["id"]

        other_customer = create_customer(
            username="other",
            email="other@example.com",
        )

        login_customer(client, other_customer)

        response = client.post(
            f"/orders/{order_id}/cancel"
        )

        assert response.status_code == 400
        assert (
            response.get_json()["error"]
            == "Order does not belong to this customer."
        )


def test_history_only_returns_logged_in_customers_orders(
    app,
    client,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.order_service.get_simulated_datetime",
            lambda: SIMULATED_TIME,
        )

        customer = create_customer()
        stock = create_stock()

        login_customer(client, customer)

        client.post(
            "/orders/buy",
            json={
                "stock_id": stock.id,
                "quantity": 1,
            },
        )

        other_customer = create_customer(
            username="other",
            email="other@example.com",
        )

        login_customer(client, other_customer)

        client.post(
            "/orders/buy",
            json={
                "stock_id": stock.id,
                "quantity": 3,
            },
        )

        response = client.get(
            "/orders/history"
        )

        assert response.status_code == 200

        orders = response.get_json()["orders"]

        assert len(orders) == 1
        assert (
            orders[0]["customer_id"]
            == other_customer.id
        )


def test_history_requires_authentication(client):
    response = client.get(
        "/orders/history"
    )

    assert response.status_code == 401