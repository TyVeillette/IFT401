from flask import Blueprint, jsonify, request

from app.models.transaction import Transaction
from app.services.auth_service import (
    get_current_customer,
    login_required,
)
from app.services.cash_account_service import (
    deposit,
    get_cash_account,
    withdraw,
)


cash_account_bp = Blueprint(
    "cash_account",
    __name__,
    url_prefix="/cash",
)


def serialize_transaction(transaction):
    return {
        "id": transaction.id,
        "transaction_type": transaction.transaction_type,
        "amount": str(transaction.amount),
        "resulting_cash_balance": str(
            transaction.resulting_cash_balance
        ),
        "transaction_date": (
            transaction.transaction_date.isoformat()
            if transaction.transaction_date
            else None
        ),
    }


@cash_account_bp.get("")
@login_required
def cash_balance():
    customer = get_current_customer()

    cash_account = get_cash_account(customer.id)

    if cash_account is None:
        return jsonify(
            {
                "error": "Cash account not found.",
            }
        ), 404

    return jsonify(
        {
            "customer_id": customer.id,
            "balance": str(cash_account.balance),
        }
    ), 200


@cash_account_bp.post("/deposit")
@login_required
def deposit_cash():
    customer = get_current_customer()
    data = request.get_json(silent=True) or request.form

    try:
        transaction = deposit(
            customer.id,
            data["amount"],
        )

        return jsonify(
            {
                "message": "Deposit completed.",
                "transaction": serialize_transaction(
                    transaction
                ),
            }
        ), 201

    except (KeyError, TypeError, ValueError) as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400


@cash_account_bp.post("/withdraw")
@login_required
def withdraw_cash():
    customer = get_current_customer()
    data = request.get_json(silent=True) or request.form

    try:
        transaction = withdraw(
            customer.id,
            data["amount"],
        )

        return jsonify(
            {
                "message": "Withdrawal completed.",
                "transaction": serialize_transaction(
                    transaction
                ),
            }
        ), 201

    except (KeyError, TypeError, ValueError) as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400


@cash_account_bp.get("/transactions")
@login_required
def cash_transactions():
    customer = get_current_customer()

    transactions = (
        Transaction.query
        .filter_by(customer_id=customer.id)
        .order_by(
            Transaction.transaction_date.desc(),
            Transaction.id.desc(),
        )
        .all()
    )

    return jsonify(
        {
            "transactions": [
                serialize_transaction(transaction)
                for transaction in transactions
            ]
        }
    ), 200