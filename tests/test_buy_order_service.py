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
from app.models.order import Order
from app.models.portfolio_holding import PortfolioHolding
from app.models.stock import Stock
from app.models.transaction import Transaction
from app.services.order_service import (
    create_buy_order,
    execute_buy_order,
)


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

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def create_customer(balance=Decimal("1000.00")):
    customer = Customer(
        full_name="Test Customer",
        username="buyer",
        email="buyer@example.com",
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

    return customer, cash_account


def create_stock(price=Decimal("100.00")):
    stock = Stock(
        company_name="Test Company",
        ticker="TEST",
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


def configure_execution(monkeypatch, market_open=True):
    monkeypatch.setattr(
        "app.services.order_service.get_simulated_datetime",
        lambda: SIMULATED_TIME,
    )

    monkeypatch.setattr(
        "app.services.order_service.is_market_open",
        lambda: market_open,
    )


def test_create_buy_order_is_pending(app, monkeypatch):
    with app.app_context():
        configure_execution(monkeypatch)

        customer, _ = create_customer()
        stock = create_stock()

        order = create_buy_order(
            customer.id,
            stock.id,
            5,
        )

        assert order.order_type == "Buy"
        assert order.quantity == 5
        assert order.status == "Pending"
        assert order.execution_price is None
        assert order.executed_at is None


def test_buy_quantity_must_be_positive(app):
    with app.app_context():
        customer, _ = create_customer()
        stock = create_stock()

        with pytest.raises(
            ValueError,
            match="Order quantity must be greater than zero",
        ):
            create_buy_order(
                customer.id,
                stock.id,
                0,
            )


def test_closed_market_leaves_order_pending(app, monkeypatch):
    with app.app_context():
        configure_execution(
            monkeypatch,
            market_open=False,
        )

        customer, cash_account = create_customer()
        stock = create_stock()

        order = create_buy_order(
            customer.id,
            stock.id,
            5,
        )

        execute_buy_order(order.id)

        assert order.status == "Pending"
        assert cash_account.balance == Decimal("1000.00")

        holding = PortfolioHolding.query.filter_by(
            customer_id=customer.id,
            stock_id=stock.id,
        ).first()

        assert holding is None


def test_successful_buy_executes(app, monkeypatch):
    with app.app_context():
        configure_execution(monkeypatch)

        customer, cash_account = create_customer()
        stock = create_stock()

        order = create_buy_order(
            customer.id,
            stock.id,
            5,
        )

        execute_buy_order(order.id)

        holding = PortfolioHolding.query.filter_by(
            customer_id=customer.id,
            stock_id=stock.id,
        ).first()

        transaction = Transaction.query.filter_by(
            order_id=order.id
        ).first()

        assert order.status == "Executed"
        assert order.execution_price == Decimal("100.00")
        assert order.executed_at == SIMULATED_TIME

        assert cash_account.balance == Decimal("500.00")

        assert holding is not None
        assert holding.share_quantity == 5

        assert transaction is not None
        assert transaction.transaction_type == "Buy"
        assert transaction.amount == Decimal("-500.00")
        assert transaction.resulting_cash_balance == Decimal("500.00")
        assert transaction.share_quantity == 5
        assert transaction.price_per_share == Decimal("100.00")


def test_buy_uses_execution_time_price(app, monkeypatch):
    with app.app_context():
        configure_execution(monkeypatch)

        customer, cash_account = create_customer()
        stock = create_stock(
            Decimal("100.00")
        )

        order = create_buy_order(
            customer.id,
            stock.id,
            5,
        )

        stock.current_price = Decimal("120.00")
        db.session.commit()

        execute_buy_order(order.id)

        assert order.execution_price == Decimal("120.00")
        assert cash_account.balance == Decimal("400.00")


def test_insufficient_cash_rejects_order(app, monkeypatch):
    with app.app_context():
        configure_execution(monkeypatch)

        customer, cash_account = create_customer(
            Decimal("100.00")
        )

        stock = create_stock(
            Decimal("50.00")
        )

        order = create_buy_order(
            customer.id,
            stock.id,
            5,
        )

        execute_buy_order(order.id)

        assert order.status == "Rejected"
        assert order.rejection_reason == "Insufficient cash balance."
        assert cash_account.balance == Decimal("100.00")

        holding = PortfolioHolding.query.filter_by(
            customer_id=customer.id,
            stock_id=stock.id,
        ).first()

        transaction = Transaction.query.filter_by(
            order_id=order.id
        ).first()

        assert holding is None
        assert transaction is None


def test_cancelled_buy_cannot_execute(app, monkeypatch):
    with app.app_context():
        configure_execution(monkeypatch)

        customer, _ = create_customer()
        stock = create_stock()

        order = create_buy_order(
            customer.id,
            stock.id,
            5,
        )

        order.status = "Cancelled"
        db.session.commit()

        with pytest.raises(
            ValueError,
            match="Only Pending orders can execute",
        ):
            execute_buy_order(order.id)