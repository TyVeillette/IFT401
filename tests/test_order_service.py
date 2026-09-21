import os
from datetime import datetime
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest

from app import create_app
from app.extensions import db
from app.models.customer import Customer
from app.models.order import Order
from app.models.stock import Stock
from app.services.order_service import cancel_order


@pytest.fixture
def app():
    app = create_app()

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def create_customer():
    customer = Customer(
        full_name="Test Customer",
        username="testcustomer",
        email="test@example.com",
        password_hash="test-password-hash",
        is_admin=False,
    )

    db.session.add(customer)
    db.session.commit()

    return customer


def create_stock():
    stock = Stock(
        company_name="Test Company",
        ticker="TEST",
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


def create_order(customer, stock, status="Pending"):
    order = Order(
        customer_id=customer.id,
        stock_id=stock.id,
        order_type="Buy",
        quantity=10,
        status=status,
        submitted_at=datetime(2026, 9, 20, 10, 0, 0),
    )

    db.session.add(order)
    db.session.commit()

    return order


def test_cancel_pending_order(app):
    with app.app_context():
        customer = create_customer()
        stock = create_stock()
        order = create_order(customer, stock)

        cancelled_order = cancel_order(
            order.id,
            customer_id=customer.id,
        )

        assert cancelled_order.status == "Cancelled"


def test_cannot_cancel_executed_order(app):
    with app.app_context():
        customer = create_customer()
        stock = create_stock()
        order = create_order(
            customer,
            stock,
            status="Executed",
        )

        with pytest.raises(
            ValueError,
            match="Only Pending orders can be cancelled",
        ):
            cancel_order(
                order.id,
                customer_id=customer.id,
            )


def test_cannot_cancel_already_cancelled_order(app):
    with app.app_context():
        customer = create_customer()
        stock = create_stock()
        order = create_order(
            customer,
            stock,
            status="Cancelled",
        )

        with pytest.raises(
            ValueError,
            match="Only Pending orders can be cancelled",
        ):
            cancel_order(
                order.id,
                customer_id=customer.id,
            )


def test_customer_cannot_cancel_another_customers_order(app):
    with app.app_context():
        customer = create_customer()
        stock = create_stock()
        order = create_order(customer, stock)

        other_customer = Customer(
            full_name="Other Customer",
            username="othercustomer",
            email="other@example.com",
            password_hash="test-password-hash",
            is_admin=False,
        )

        db.session.add(other_customer)
        db.session.commit()

        with pytest.raises(
            ValueError,
            match="Order does not belong to this customer",
        ):
            cancel_order(
                order.id,
                customer_id=other_customer.id,
            )


def test_cancel_missing_order(app):
    with app.app_context():
        with pytest.raises(
            ValueError,
            match="Order not found",
        ):
            cancel_order(99999)