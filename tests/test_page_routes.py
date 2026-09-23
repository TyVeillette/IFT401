import os
from datetime import datetime, time
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models.cash_account import CashAccount
from app.models.customer import Customer
from app.models.market_hours import MarketHours
from app.models.order import Order
from app.models.portfolio_holding import PortfolioHolding
from app.models.stock import Stock
from app.services.market_clock_service import (
    pause_clock,
    set_simulated_datetime,
)
from app.services.market_schedule_service import get_market_schedule


SIMULATED_TIME = datetime(
    2026,
    9,
    14,
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

        set_simulated_datetime(SIMULATED_TIME)
        pause_clock()

        db.session.add(
            MarketHours(
                id=1,
                opening_time=time(9, 30),
                closing_time=time(16, 0),
            )
        )
        db.session.commit()

        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def create_customer(
    username="pages",
    is_admin=False,
    balance=Decimal("1000.00"),
):
    customer = Customer(
        full_name="Page Route Customer",
        username=username,
        email=f"{username}@example.com",
        password_hash=generate_password_hash("Password123!"),
        is_admin=is_admin,
    )

    db.session.add(customer)
    db.session.flush()

    db.session.add(
        CashAccount(
            customer_id=customer.id,
            balance=balance,
        )
    )
    db.session.commit()

    return customer


def create_stock(ticker="PAGE"):
    stock = Stock(
        company_name="Page Company",
        ticker=ticker,
        initial_price=Decimal("50.00"),
        current_price=Decimal("50.00"),
        open_price=Decimal("48.00"),
        high_price=Decimal("52.00"),
        low_price=Decimal("47.00"),
        volume=1000,
        is_active=True,
    )

    db.session.add(stock)
    db.session.commit()

    return stock


def login_customer(client, customer):
    with client.session_transaction() as session:
        session["customer_id"] = customer.id


def test_page_redirects_to_login_when_signed_out(client):
    response = client.get("/market-board")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_page_signs_in(app, client):
    with app.app_context():
        create_customer()

        response = client.post(
            "/login",
            data={
                "username": "pages",
                "password": "Password123!",
            },
        )

        assert response.status_code == 302
        assert response.headers["Location"].endswith(
            "/market-board"
        )


def test_login_page_rejects_bad_password(app, client):
    with app.app_context():
        create_customer()

        response = client.post(
            "/login",
            data={
                "username": "pages",
                "password": "wrong",
            },
        )

        assert response.status_code == 401
        assert b"Invalid username or password." in response.data


def test_login_ignores_external_next_url(app, client):
    with app.app_context():
        create_customer()

        response = client.post(
            "/login?next=//evil.example.com",
            data={
                "username": "pages",
                "password": "Password123!",
            },
        )

        assert response.headers["Location"].endswith(
            "/market-board"
        )


def test_market_board_page(app, client):
    with app.app_context():
        customer = create_customer()
        create_stock()
        login_customer(client, customer)

        response = client.get("/market-board")

        assert response.status_code == 200
        assert b"PAGE" in response.data
        assert b"$50.00" in response.data
        assert b"Open" in response.data


def test_portfolio_page(app, client):
    with app.app_context():
        customer = create_customer()
        stock = create_stock()

        db.session.add(
            PortfolioHolding(
                customer_id=customer.id,
                stock_id=stock.id,
                share_quantity=4,
            )
        )
        db.session.commit()

        login_customer(client, customer)

        response = client.get("/my-portfolio")

        assert response.status_code == 200
        assert b"$1,200.00" in response.data
        assert b"$200.00" in response.data


def test_buy_page_creates_pending_order(app, client):
    with app.app_context():
        customer = create_customer()
        stock = create_stock()
        login_customer(client, customer)

        response = client.post(
            "/buy/PAGE",
            data={"quantity": "3"},
        )

        assert response.status_code == 302

        order = Order.query.one()

        assert order.customer_id == customer.id
        assert order.stock_id == stock.id
        assert order.order_type == "Buy"
        assert order.quantity == 3
        assert order.status == "Pending"


def test_buy_page_rejects_zero_quantity(app, client):
    with app.app_context():
        customer = create_customer()
        create_stock()
        login_customer(client, customer)

        response = client.post(
            "/buy/PAGE",
            data={"quantity": "0"},
        )

        assert response.status_code == 200
        assert b"greater than zero" in response.data
        assert Order.query.count() == 0


def test_sell_page_rejects_more_than_owned(app, client):
    with app.app_context():
        customer = create_customer()
        stock = create_stock()

        db.session.add(
            PortfolioHolding(
                customer_id=customer.id,
                stock_id=stock.id,
                share_quantity=2,
            )
        )
        db.session.commit()

        login_customer(client, customer)

        response = client.post(
            "/sell/PAGE",
            data={"quantity": "5"},
        )

        assert response.status_code == 200
        assert b"Insufficient shares" in response.data
        assert Order.query.count() == 0


def test_cancel_pending_order_page(app, client):
    with app.app_context():
        customer = create_customer()
        stock = create_stock()

        order = Order(
            customer_id=customer.id,
            stock_id=stock.id,
            order_type="Buy",
            quantity=1,
            status="Pending",
            submitted_at=SIMULATED_TIME,
        )
        db.session.add(order)
        db.session.commit()

        login_customer(client, customer)

        listing = client.get("/pending-orders")

        assert b"PAGE" in listing.data

        response = client.post(
            f"/pending-orders/{order.id}/cancel"
        )

        assert response.status_code == 302
        assert db.session.get(Order, order.id).status == "Cancelled"


def test_cash_page_deposit(app, client):
    with app.app_context():
        customer = create_customer()
        login_customer(client, customer)

        response = client.post(
            "/cash-account",
            data={
                "action": "deposit",
                "amount": "250.00",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"$1,250.00" in response.data

        history = client.get("/transaction-history")

        assert b"Deposit" in history.data


def test_admin_page_requires_admin(app, client):
    with app.app_context():
        customer = create_customer()
        login_customer(client, customer)

        response = client.get("/admin/create-stock")

        assert response.status_code == 302
        assert response.headers["Location"].endswith(
            "/market-board"
        )


def test_admin_create_stock_page(app, client):
    with app.app_context():
        admin = create_customer(
            username="admin",
            is_admin=True,
        )
        login_customer(client, admin)

        response = client.post(
            "/admin/create-stock",
            data={
                "ticker": "newc",
                "company_name": "New Company",
                "initial_price": "12.34",
                "volume": "500",
            },
        )

        assert response.status_code == 302

        stock = Stock.query.filter_by(ticker="NEWC").one()

        assert stock.current_price == Decimal("12.34")


def test_admin_market_hours_rejects_open_after_close(app, client):
    with app.app_context():
        admin = create_customer(
            username="admin",
            is_admin=True,
        )
        login_customer(client, admin)

        response = client.post(
            "/admin/market-hours",
            data={
                "opening_time": "17:00",
                "closing_time": "09:00",
            },
        )

        assert response.status_code == 200
        assert b"must occur before closing" in response.data


def test_admin_market_schedule_sets_holiday(app, client):
    with app.app_context():
        admin = create_customer(
            username="admin",
            is_admin=True,
        )
        login_customer(client, admin)

        response = client.post(
            "/admin/market-schedule",
            data={
                "simulated_date": "2026-10-12",
                "is_holiday": "on",
            },
        )

        assert response.status_code == 302

        schedule = get_market_schedule(
            datetime(2026, 10, 12).date()
        )

        assert schedule.is_holiday is True
