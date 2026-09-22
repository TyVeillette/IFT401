from flask import Blueprint, jsonify

from app.models.transaction import Transaction
from app.services.auth_service import (
    get_current_customer,
    login_required,
)
from app.services.portfolio_service import get_portfolio


portfolio_bp = Blueprint(
    "portfolio",
    __name__,
    url_prefix="/portfolio",
)


def serialize_transaction(transaction):
    return {
        "id": transaction.id,
        "order_id": transaction.order_id,
        "stock_id": transaction.stock_id,
        "transaction_type": transaction.transaction_type,
        "amount": str(transaction.amount),
        "resulting_cash_balance": str(
            transaction.resulting_cash_balance
        ),
        "share_quantity": transaction.share_quantity,
        "price_per_share": (
            str(transaction.price_per_share)
            if transaction.price_per_share is not None
            else None
        ),
        "transaction_date": (
            transaction.transaction_date.isoformat()
            if transaction.transaction_date
            else None
        ),
    }


@portfolio_bp.get("")
@login_required
def portfolio_summary():
    customer = get_current_customer()

    try:
        portfolio = get_portfolio(
            customer.id
        )

        return jsonify(
            {
                "customer_id": customer.id,
                "cash_balance": str(
                    portfolio["cash_balance"]
                ),
                "total_market_value": str(
                    portfolio["total_market_value"]
                ),
                "total_account_value": str(
                    portfolio["total_account_value"]
                ),
                "holdings": [
                    {
                        "stock_id": item["stock_id"],
                        "ticker": item["ticker"],
                        "company_name": item[
                            "company_name"
                        ],
                        "share_quantity": item[
                            "share_quantity"
                        ],
                        "current_price": str(
                            item["current_price"]
                        ),
                        "market_value": str(
                            item["market_value"]
                        ),
                    }
                    for item in portfolio["holdings"]
                ],
            }
        ), 200

    except ValueError as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 404


@portfolio_bp.get("/transactions")
@login_required
def transaction_history():
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