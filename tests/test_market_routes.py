import os
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest

from app import create_app
from app.extensions import db
from app.models.stock import Stock


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


def create_stock(
    ticker="ROUTE",
    company_name="Route Company",
    price=Decimal("125.00"),
    volume=1000,
):
    stock = Stock(
        company_name=company_name,
        ticker=ticker,
        initial_price=price,
        current_price=price,
        open_price=Decimal("120.00"),
        high_price=Decimal("130.00"),
        low_price=Decimal("115.00"),
        volume=volume,
        is_active=True,
    )

    db.session.add(stock)
    db.session.commit()

    return stock


def test_market_board_route(
    app,
    client,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_board_service.is_market_open",
            lambda: True,
        )

        create_stock()

        response = client.get("/market")

        assert response.status_code == 200

        data = response.get_json()

        assert data["market_open"] is True
        assert len(data["stocks"]) == 1

        stock = data["stocks"][0]

        assert stock["ticker"] == "ROUTE"
        assert stock["company_name"] == "Route Company"
        assert stock["current_price"] == "125.00"
        assert stock["volume"] == 1000
        assert stock["market_cap"] == "125000.00"
        assert stock["open_price"] == "120.00"
        assert stock["high_price"] == "130.00"
        assert stock["low_price"] == "115.00"


def test_market_board_route_reports_closed_market(
    app,
    client,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_board_service.is_market_open",
            lambda: False,
        )

        create_stock()

        response = client.get("/market")

        assert response.status_code == 200
        assert response.get_json()["market_open"] is False


def test_market_board_route_excludes_inactive_stock(
    app,
    client,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_board_service.is_market_open",
            lambda: True,
        )

        active = create_stock(
            ticker="ACTIVE",
        )

        inactive = Stock(
            company_name="Inactive Company",
            ticker="INACTIVE",
            initial_price=Decimal("50.00"),
            current_price=Decimal("50.00"),
            open_price=Decimal("50.00"),
            high_price=Decimal("50.00"),
            low_price=Decimal("50.00"),
            volume=500,
            is_active=False,
        )

        db.session.add(inactive)
        db.session.commit()

        response = client.get("/market")

        assert response.status_code == 200

        stocks = response.get_json()["stocks"]

        assert len(stocks) == 1
        assert stocks[0]["stock_id"] == active.id
        assert stocks[0]["ticker"] == "ACTIVE"