from decimal import Decimal

from app.extensions import db
from app.models.cash_account import CashAccount
from app.models.portfolio_holding import PortfolioHolding
from app.models.stock import Stock


def get_portfolio(customer_id):
    cash_account = CashAccount.query.filter_by(
        customer_id=customer_id
    ).first()

    if cash_account is None:
        raise ValueError("Cash account not found.")

    holdings = PortfolioHolding.query.filter_by(
        customer_id=customer_id
    ).all()

    portfolio_items = []
    total_market_value = Decimal("0.00")

    for holding in holdings:
        stock = db.session.get(
            Stock,
            holding.stock_id,
        )

        if stock is None:
            continue

        current_price = Decimal(
            str(stock.current_price)
        )

        market_value = (
            current_price
            * holding.share_quantity
        )

        total_market_value += market_value

        portfolio_items.append(
            {
                "stock_id": stock.id,
                "ticker": stock.ticker,
                "company_name": stock.company_name,
                "share_quantity": holding.share_quantity,
                "current_price": current_price,
                "market_value": market_value,
            }
        )

    total_account_value = (
        cash_account.balance
        + total_market_value
    )

    return {
        "cash_balance": cash_account.balance,
        "total_market_value": total_market_value,
        "total_account_value": total_account_value,
        "holdings": portfolio_items,
    }