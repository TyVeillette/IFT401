import os
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest

from app import create_app
from app.extensions import db
from app.models.stock import Stock
from app.services.market_board_service import get_market_board


@pytest.fixture
def app():
    app = create_app()

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def create_stock(
    ticker,
    company_name,
    current_price,
    volume,
    is_active=True,
):
    stock = Stock(
        company_name=company_name,
        ticker=ticker,
        initial_price=current_price,
        current_price=current_price,
        open_price=current_price,
        high_price=current_price,
        low_price=current_price,
        volume=volume,
        is_active=is_active,
    )

    db.session.add(stock)
    db.session.commit()

    return stock


def test_market_board_returns_active_stocks(
    app,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_board_service.is_market_open",
            lambda: True,
        )

        create_stock(
            "AAA",
            "Active Company",
            Decimal("100.00"),
            1000,
            True,
        )

        create_stock(
            "ZZZ",
            "Inactive Company",
            Decimal("50.00"),
            500,
            False,
        )

        board = get_market_board()

        assert board["market_open"] is True
        assert len(board["stocks"]) == 1
        assert board["stocks"][0]["ticker"] == "AAA"


def test_market_board_calculates_market_cap(
    app,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_board_service.is_market_open",
            lambda: True,
        )

        create_stock(
            "CAP",
            "Market Cap Company",
            Decimal("25.50"),
            2000,
        )

        board = get_market_board()

        stock = board["stocks"][0]

        assert stock["current_price"] == Decimal("25.50")
        assert stock["volume"] == 2000
        assert stock["market_cap"] == Decimal("51000.00")


def test_market_board_sorts_by_ticker(
    app,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_board_service.is_market_open",
            lambda: True,
        )

        create_stock(
            "ZZZ",
            "Z Company",
            Decimal("10.00"),
            100,
        )

        create_stock(
            "AAA",
            "A Company",
            Decimal("20.00"),
            100,
        )

        board = get_market_board()

        tickers = [
            stock["ticker"]
            for stock in board["stocks"]
        ]

        assert tickers == ["AAA", "ZZZ"]


def test_market_board_reports_closed_market(
    app,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_board_service.is_market_open",
            lambda: False,
        )

        create_stock(
            "CLOSED",
            "Closed Market Company",
            Decimal("75.00"),
            1000,
        )

        board = get_market_board()

        assert board["market_open"] is False
        assert len(board["stocks"]) == 1