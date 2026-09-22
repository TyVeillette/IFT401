from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.extensions import db
from app.models.cash_account import CashAccount
from app.models.transaction import Transaction
from app.services.market_clock_service import get_simulated_datetime


MONEY_INCREMENT = Decimal("0.01")


def normalize_amount(amount):
    try:
        normalized = Decimal(str(amount)).quantize(
            MONEY_INCREMENT,
            rounding=ROUND_HALF_UP,
        )
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Amount must be a valid number.")

    if normalized <= 0:
        raise ValueError("Amount must be greater than zero.")

    return normalized


def get_cash_account(customer_id):
    return CashAccount.query.filter_by(
        customer_id=customer_id
    ).first()


def deposit(customer_id, amount):
    amount = normalize_amount(amount)

    cash_account = get_cash_account(customer_id)

    if cash_account is None:
        raise ValueError("Cash account not found.")

    cash_account.balance += amount

    transaction = Transaction(
        customer_id=customer_id,
        cash_account_id=cash_account.id,
        order_id=None,
        stock_id=None,
        transaction_type="Deposit",
        amount=amount,
        resulting_cash_balance=cash_account.balance,
        share_quantity=None,
        price_per_share=None,
        transaction_date=get_simulated_datetime(),
    )

    db.session.add(transaction)
    db.session.commit()

    return transaction


def withdraw(customer_id, amount):
    amount = normalize_amount(amount)

    cash_account = get_cash_account(customer_id)

    if cash_account is None:
        raise ValueError("Cash account not found.")

    if cash_account.balance < amount:
        raise ValueError("Insufficient cash balance.")

    cash_account.balance -= amount

    transaction = Transaction(
        customer_id=customer_id,
        cash_account_id=cash_account.id,
        order_id=None,
        stock_id=None,
        transaction_type="Withdrawal",
        amount=-amount,
        resulting_cash_balance=cash_account.balance,
        share_quantity=None,
        price_per_share=None,
        transaction_date=get_simulated_datetime(),
    )

    db.session.add(transaction)
    db.session.commit()

    return transaction