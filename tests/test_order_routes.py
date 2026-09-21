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


def create_customer(balance=Decimal("1000.00")):
    customer = Customer(
        full_name="Route Test Customer",
        username="routeuser",
        email="route@example.com",
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


def test_buy_route_creates_pending_order(
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

        response = client.post(
            "/orders/buy",
            json={
                "customer_id": customer.id,
                "stock_id": stock.id,
                "quantity": 5,
            },
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data["message"] == "Buy order submitted."
        assert data["order"]["order_type"] == "Buy"
        assert data["order"]["quantity"] == 5
        assert data["order"]["status"] == "Pending"


def test_sell_route_creates_pending_order(
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

        response = client.post(
            "/orders/sell",
            json={
                "customer_id": customer.id,
                "stock_id": stock.id,
                "quantity": 4,
            },
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data["order"]["order_type"] == "Sell"
        assert data["order"]["quantity"] == 4
        assert data["order"]["status"] == "Pending"


def test_cancel_route_cancels_pending_order(
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

        buy_response = client.post(
            "/orders/buy",
            json={
                "customer_id": customer.id,
                "stock_id": stock.id,
                "quantity": 2,
            },
        )

        order_id = buy_response.get_json()["order"]["id"]

        cancel_response = client.post(
            f"/orders/{order_id}/cancel",
            json={
                "customer_id": customer.id,
            },
        )

        assert cancel_response.status_code == 200

        data = cancel_response.get_json()

        assert data["message"] == "Order cancelled."
        assert data["order"]["status"] == "Cancelled"


def test_customer_order_history_route(
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

        client.post(
            "/orders/buy",
            json={
                "customer_id": customer.id,
                "stock_id": stock.id,
                "quantity": 1,
            },
        )

        client.post(
            "/orders/buy",
            json={
                "customer_id": customer.id,
                "stock_id": stock.id,
                "quantity": 2,
            },
        )

        response = client.get(
            f"/orders/customer/{customer.id}"
        )

        assert response.status_code == 200

        data = response.get_json()

        assert len(data["orders"]) == 2


def test_buy_route_rejects_invalid_quantity(
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

        response = client.post(
            "/orders/buy",
            json={
                "customer_id": customer.id,
                "stock_id": stock.id,
                "quantity": 0,
            },
        )

        assert response.status_code == 400

        data = response.get_json()

        assert (
            data["error"]
            == "Order quantity must be greater than zero."
        )


def test_sell_route_rejects_insufficient_shares(
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

        response = client.post(
            "/orders/sell",
            json={
                "customer_id": customer.id,
                "stock_id": stock.id,
                "quantity": 5,
            },
        )

        assert response.status_code == 400

        data = response.get_json()

        assert (
            data["error"]
            == "Insufficient shares available to sell."
        )
