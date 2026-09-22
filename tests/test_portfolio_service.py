import os
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
from app.services.portfolio_service import get_portfolio


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
        full_name="Portfolio Test Customer",
        username="portfoliouser",
        email="portfolio@example.com",
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


def create_stock(
    ticker,
    company_name,
    price,
):
    stock = Stock(
        company_name=company_name,
        ticker=ticker,
        initial_price=price,
        current_price=price,
        open_price=price,
        high_price=price,
        low_price=price,
        volume=1000,
        is_active=True,
    )

    db.session.add(stock)
    db.session.commit()

    return stock


def test_portfolio_calculates_values(app):
    with app.app_context():
        customer = create_customer(
            Decimal("1000.00")
        )

        stock_one = create_stock(
            "ONE",
            "Company One",
            Decimal("100.00"),
        )

        stock_two = create_stock(
            "TWO",
            "Company Two",
            Decimal("50.00"),
        )

        db.session.add_all(
            [
                PortfolioHolding(
                    customer_id=customer.id,
                    stock_id=stock_one.id,
                    share_quantity=5,
                ),
                PortfolioHolding(
                    customer_id=customer.id,
                    stock_id=stock_two.id,
                    share_quantity=4,
                ),
            ]
        )

        db.session.commit()

        portfolio = get_portfolio(
            customer.id
        )

        assert (
            portfolio["cash_balance"]
            == Decimal("1000.00")
        )

        assert (
            portfolio["total_market_value"]
            == Decimal("700.00")
        )

        assert (
            portfolio["total_account_value"]
            == Decimal("1700.00")
        )

        assert len(portfolio["holdings"]) == 2


def test_empty_portfolio_returns_cash_value(app):
    with app.app_context():
        customer = create_customer(
            Decimal("750.00")
        )

        portfolio = get_portfolio(
            customer.id
        )

        assert portfolio["holdings"] == []

        assert (
            portfolio["total_market_value"]
            == Decimal("0.00")
        )

        assert (
            portfolio["total_account_value"]
            == Decimal("750.00")
        )


def test_missing_cash_account_rejected(app):
    with app.app_context():
        customer = Customer(
            full_name="No Cash Customer",
            username="nocash",
            email="nocash@example.com",
            password_hash="test-password-hash",
            is_admin=False,
        )

        db.session.add(customer)
        db.session.commit()

        with pytest.raises(
            ValueError,
            match="Cash account not found",
        ):
            get_portfolio(
                customer.id
            )