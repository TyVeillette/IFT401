from decimal import Decimal

from app.extensions import db
from app.models.cash_account import CashAccount
from app.models.customer import Customer
from app.models.order import Order
from app.models.portfolio_holding import PortfolioHolding
from app.models.stock import Stock
from app.models.transaction import Transaction
from app.services.market_clock_service import get_simulated_datetime
from app.services.market_schedule_service import is_market_open


def cancel_order(order_id, customer_id=None):
    order = db.session.get(Order, order_id)

    if order is None:
        raise ValueError("Order not found.")

    if customer_id is not None and order.customer_id != customer_id:
        raise ValueError("Order does not belong to this customer.")

    if order.status != "Pending":
        raise ValueError(
            f"Only Pending orders can be cancelled. "
            f"Current status: {order.status}."
        )

    order.status = "Cancelled"

    db.session.commit()

    return order


def create_buy_order(customer_id, stock_id, quantity):
    if quantity <= 0:
        raise ValueError("Order quantity must be greater than zero.")

    customer = db.session.get(Customer, customer_id)

    if customer is None:
        raise ValueError("Customer not found.")

    stock = db.session.get(Stock, stock_id)

    if stock is None:
        raise ValueError("Stock not found.")

    if not stock.is_active:
        raise ValueError("Cannot place an order for an inactive stock.")

    order = Order(
        customer_id=customer_id,
        stock_id=stock_id,
        order_type="Buy",
        quantity=quantity,
        status="Pending",
        submitted_at=get_simulated_datetime(),
    )

    db.session.add(order)
    db.session.commit()

    return order


def execute_buy_order(order_id):
    order = db.session.get(Order, order_id)

    if order is None:
        raise ValueError("Order not found.")

    if order.order_type != "Buy":
        raise ValueError("Order is not a Buy order.")

    if order.status != "Pending":
        raise ValueError(
            f"Only Pending orders can execute. "
            f"Current status: {order.status}."
        )

    if not is_market_open():
        return order

    stock = db.session.get(Stock, order.stock_id)

    if stock is None or not stock.is_active:
        order.status = "Rejected"
        order.rejection_reason = "Stock is unavailable."
        db.session.commit()
        return order

    cash_account = CashAccount.query.filter_by(
        customer_id=order.customer_id
    ).first()

    if cash_account is None:
        order.status = "Rejected"
        order.rejection_reason = "Cash account not found."
        db.session.commit()
        return order

    execution_price = Decimal(stock.current_price)
    execution_cost = execution_price * order.quantity

    if cash_account.balance < execution_cost:
        order.status = "Rejected"
        order.rejection_reason = "Insufficient cash balance."
        db.session.commit()
        return order

    holding = PortfolioHolding.query.filter_by(
        customer_id=order.customer_id,
        stock_id=order.stock_id,
    ).first()

    if holding is None:
        holding = PortfolioHolding(
            customer_id=order.customer_id,
            stock_id=order.stock_id,
            share_quantity=0,
        )
        db.session.add(holding)

    cash_account.balance -= execution_cost
    holding.share_quantity += order.quantity

    simulated_datetime = get_simulated_datetime()

    order.status = "Executed"
    order.execution_price = execution_price
    order.executed_at = simulated_datetime
    order.rejection_reason = None

    transaction = Transaction(
        customer_id=order.customer_id,
        cash_account_id=cash_account.id,
        order_id=order.id,
        stock_id=order.stock_id,
        transaction_type="Buy",
        amount=-execution_cost,
        resulting_cash_balance=cash_account.balance,
        share_quantity=order.quantity,
        price_per_share=execution_price,
        transaction_date=simulated_datetime,
    )

    db.session.add(transaction)
    db.session.commit()

    return order