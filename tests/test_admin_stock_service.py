import os
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest

from app import create_app
from app.extensions import db
from app.services.admin_stock_service import (
    create_stock,
    set_stock_active,
)


@pytest.fixture
def app():
    app = create_app()

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_create_stock(app):
    with app.app_context():
        stock = create_stock(
            company_name="Test Company",
            ticker="test",
            initial_price="125.50",
            volume=1000000,
            exchange="NASDAQ",
            sector="Technology",
        )

        assert stock.id is not None
        assert stock.company_name == "Test Company"
        assert stock.ticker == "TEST"
        assert stock.exchange == "NASDAQ"
        assert stock.sector == "Technology"

        assert stock.initial_price == Decimal("125.50")
        assert stock.current_price == Decimal("125.50")
        assert stock.open_price == Decimal("125.50")
        assert stock.high_price == Decimal("125.50")
        assert stock.low_price == Decimal("125.50")

        assert stock.volume == 1000000
        assert stock.is_active is True


def test_duplicate_ticker_rejected(app):
    with app.app_context():
        create_stock(
            company_name="First Company",
            ticker="DUP",
            initial_price="100.00",
            volume=1000,
        )

        with pytest.raises(
            ValueError,
            match="already exists",
        ):
            create_stock(
                company_name="Second Company",
                ticker="dup",
                initial_price="200.00",
                volume=2000,
            )


def test_invalid_price_rejected(app):
    with app.app_context():
        with pytest.raises(
            ValueError,
            match="Price must be a valid number",
        ):
            create_stock(
                company_name="Bad Price Company",
                ticker="BAD",
                initial_price="invalid",
                volume=1000,
            )


def test_zero_price_rejected(app):
    with app.app_context():
        with pytest.raises(
            ValueError,
            match="Price must be greater than zero",
        ):
            create_stock(
                company_name="Zero Price Company",
                ticker="ZERO",
                initial_price="0",
                volume=1000,
            )


def test_negative_volume_rejected(app):
    with app.app_context():
        with pytest.raises(
            ValueError,
            match="Volume cannot be negative",
        ):
            create_stock(
                company_name="Negative Volume Company",
                ticker="NEG",
                initial_price="100.00",
                volume=-1,
            )


def test_set_stock_active(app):
    with app.app_context():
        stock = create_stock(
            company_name="Status Company",
            ticker="STAT",
            initial_price="50.00",
            volume=1000,
        )

        updated = set_stock_active(
            stock.id,
            False,
        )

        assert updated.is_active is False

        updated = set_stock_active(
            stock.id,
            True,
        )

        assert updated.is_active is True