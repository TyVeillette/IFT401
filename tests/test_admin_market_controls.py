import os
from datetime import datetime
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest

from app import create_app
from app.extensions import db
from app.models.customer import Customer
from app.models.stock import Stock


REAL_TIME = datetime(
    2026,
    9,
    22,
    14,
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
    username,
    email,
    is_admin=False,
):
    customer = Customer(
        full_name="Admin Test Customer",
        username=username,
        email=email,
        password_hash="test-password-hash",
        is_admin=is_admin,
    )

    db.session.add(customer)
    db.session.commit()

    return customer


def login_customer(client, customer):
    with client.session_transaction() as session:
        session["customer_id"] = customer.id


def configure_clock(client):
    return client.post(
        "/admin/market/clock",
        json={
            "simulated_datetime":
                "2026-09-22T09:30:00",
        },
    )


def test_admin_routes_require_authentication(client):
    response = client.get(
        "/admin/market/stocks"
    )

    assert response.status_code == 401

    assert (
        response.get_json()["error"]
        == "Authentication required."
    )


def test_admin_routes_reject_non_admin(
    app,
    client,
):
    with app.app_context():
        customer = create_customer(
            username="regularuser",
            email="regular@example.com",
            is_admin=False,
        )

        login_customer(
            client,
            customer,
        )

        response = client.get(
            "/admin/market/stocks"
        )

        assert response.status_code == 403

        assert (
            response.get_json()["error"]
            == "Administrator access required."
        )


def test_admin_can_create_stock(
    app,
    client,
):
    with app.app_context():
        admin = create_customer(
            username="admincreate",
            email="admincreate@example.com",
            is_admin=True,
        )

        login_customer(
            client,
            admin,
        )

        response = client.post(
            "/admin/market/stocks",
            json={
                "company_name": "Admin Company",
                "ticker": "adm",
                "initial_price": "125.50",
                "volume": 500000,
                "exchange": "NASDAQ",
                "sector": "Technology",
            },
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data["message"] == "Stock created."
        assert data["stock"]["ticker"] == "ADM"
        assert (
            data["stock"]["company_name"]
            == "Admin Company"
        )
        assert (
            data["stock"]["initial_price"]
            == "125.50"
        )
        assert data["stock"]["volume"] == 500000
        assert data["stock"]["is_active"] is True


def test_admin_can_list_stocks(
    app,
    client,
):
    with app.app_context():
        admin = create_customer(
            username="adminlist",
            email="adminlist@example.com",
            is_admin=True,
        )

        stock = Stock(
            company_name="List Company",
            ticker="LIST",
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

        login_customer(
            client,
            admin,
        )

        response = client.get(
            "/admin/market/stocks"
        )

        assert response.status_code == 200

        stocks = response.get_json()["stocks"]

        assert len(stocks) == 1
        assert stocks[0]["ticker"] == "LIST"


def test_admin_can_deactivate_stock(
    app,
    client,
):
    with app.app_context():
        admin = create_customer(
            username="adminactive",
            email="adminactive@example.com",
            is_admin=True,
        )

        stock = Stock(
            company_name="Active Company",
            ticker="ACTIVE",
            initial_price=Decimal("50.00"),
            current_price=Decimal("50.00"),
            open_price=Decimal("50.00"),
            high_price=Decimal("50.00"),
            low_price=Decimal("50.00"),
            volume=1000,
            is_active=True,
        )

        db.session.add(stock)
        db.session.commit()

        stock_id = stock.id

        login_customer(
            client,
            admin,
        )

        response = client.post(
            f"/admin/market/stocks/{stock_id}/active",
            json={
                "is_active": False,
            },
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["stock"]["is_active"] is False


def test_clock_reports_unconfigured(
    app,
    client,
):
    with app.app_context():
        admin = create_customer(
            username="adminclock1",
            email="adminclock1@example.com",
            is_admin=True,
        )

        login_customer(
            client,
            admin,
        )

        response = client.get(
            "/admin/market/clock"
        )

        assert response.status_code == 200
        assert response.get_json()["configured"] is False


def test_admin_can_configure_clock(
    app,
    client,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_clock_service.utc_now",
            lambda: REAL_TIME,
        )

        admin = create_customer(
            username="adminclock2",
            email="adminclock2@example.com",
            is_admin=True,
        )

        login_customer(
            client,
            admin,
        )

        response = configure_clock(client)

        assert response.status_code == 200

        data = response.get_json()

        assert (
            data["message"]
            == "Simulated datetime updated."
        )

        assert (
            data["clock"]["simulated_anchor"]
            == "2026-09-22T09:30:00"
        )

        assert data["clock"]["is_running"] is True


def test_admin_can_pause_and_resume_clock(
    app,
    client,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_clock_service.utc_now",
            lambda: REAL_TIME,
        )

        admin = create_customer(
            username="adminclock3",
            email="adminclock3@example.com",
            is_admin=True,
        )

        login_customer(
            client,
            admin,
        )

        configure_clock(client)

        pause_response = client.post(
            "/admin/market/clock/pause"
        )

        assert pause_response.status_code == 200

        assert (
            pause_response.get_json()[
                "clock"
            ]["is_running"]
            is False
        )

        resume_response = client.post(
            "/admin/market/clock/resume"
        )

        assert resume_response.status_code == 200

        assert (
            resume_response.get_json()[
                "clock"
            ]["is_running"]
            is True
        )


def test_admin_can_change_clock_speed(
    app,
    client,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_clock_service.utc_now",
            lambda: REAL_TIME,
        )

        admin = create_customer(
            username="adminclock4",
            email="adminclock4@example.com",
            is_admin=True,
        )

        login_customer(
            client,
            admin,
        )

        configure_clock(client)

        response = client.post(
            "/admin/market/clock/speed",
            json={
                "speed_multiplier": 2.5,
            },
        )

        assert response.status_code == 200

        assert (
            response.get_json()[
                "clock"
            ]["speed_multiplier"]
            == "2.50"
        )


def test_admin_can_advance_clock(
    app,
    client,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_clock_service.utc_now",
            lambda: REAL_TIME,
        )

        admin = create_customer(
            username="adminclock5",
            email="adminclock5@example.com",
            is_admin=True,
        )

        login_customer(
            client,
            admin,
        )

        configure_clock(client)

        response = client.post(
            "/admin/market/clock/advance",
            json={
                "minutes": 45,
            },
        )

        assert response.status_code == 200

        assert (
            response.get_json()[
                "clock"
            ]["simulated_anchor"]
            == "2026-09-22T10:15:00"
        )