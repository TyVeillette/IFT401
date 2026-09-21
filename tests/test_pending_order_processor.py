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
    cancel_order,
    create_buy_order,
    create_sell_order,
    process_pending_orders,
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
        username="processor",
        email="processor@example.com",
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


def create_holding(customer_id, stock_id, quantity):
    holding = PortfolioHolding(
        customer_id=customer_id,
        stock_id=stock_id,
        share_quantity=quantity,
    )

    db.session.add(holding)
    db.session.commit()

    return holding


def configure_market(monkeypatch, market_open=True):
    monkeypatch.setattr(
        "app.services.order_service.get_simulated_datetime",
        lambda: SIMULATED_TIME,
    )

    monkeypatch.setattr(
        "app.services.order_service.is_market_open",
        lambda: market_open,
    )


def test_processor_executes_pending_buy_and_sell(
    app,
    monkeypatch,
):
    with app.app_context():
        configure_market(monkeypatch)

        customer, cash_account = create_customer()
        stock = create_stock()

        holding = create_holding(
            customer.id,
            stock.id,
            10,
        )

        buy_order = create_buy_order(
            customer.id,
            stock.id,
            2,
        )

        sell_order = create_sell_order(
            customer.id,
            stock.id,
            3,
        )

        processed = process_pending_orders()

        assert len(processed) == 2

        assert buy_order.status == "Executed"
        assert sell_order.status == "Executed"

        assert cash_account.balance == Decimal("1100.00")
        assert holding.share_quantity == 9

        transactions = Transaction.query.order_by(
            Transaction.id
        ).all()

        assert len(transactions) == 2
        assert transactions[0].transaction_type == "Buy"
        assert transactions[1].transaction_type == "Sell"


def test_processor_ignores_cancelled_order(
    app,
    monkeypatch,
):
    with app.app_context():
        configure_market(monkeypatch)

        customer, cash_account = create_customer()
        stock = create_stock()

        order = create_buy_order(
            customer.id,
            stock.id,
            5,
        )

        cancel_order(
            order.id,
            customer.id,
        )

        processed = process_pending_orders()

        assert processed == []
        assert order.status == "Cancelled"
        assert cash_account.balance == Decimal("1000.00")

        transaction = Transaction.query.filter_by(
            order_id=order.id
        ).first()

        assert transaction is None


def test_processor_does_nothing_when_market_closed(
    app,
    monkeypatch,
):
    with app.app_context():
        configure_market(
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

        processed = process_pending_orders()

        assert processed == []
        assert order.status == "Pending"
        assert cash_account.balance == Decimal("1000.00")


def test_processor_ignores_non_pending_orders(
    app,
    monkeypatch,
):
    with app.app_context():
        configure_market(monkeypatch)

        customer, _ = create_customer()
        stock = create_stock()

        order = Order(
            customer_id=customer.id,
            stock_id=stock.id,
            order_type="Buy",
            quantity=1,
            status="Rejected",
            submitted_at=SIMULATED_TIME,
            rejection_reason="Test rejection.",
        )

        db.session.add(order)
        db.session.commit()

        processed = process_pending_orders()

        assert processed == []
        assert order.status == "Rejected"

        transaction = Transaction.query.filter_by(
            order_id=order.id
        ).first()

        assert transaction is None