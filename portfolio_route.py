from flask import render_template

from flask_login import (
    login_required,
    current_user
)

from app import app
from models import (
    PortfolioHolding,
    CashAccount
)


@app.route("/portfolio")
@login_required
def view_portfolio():

    holdings = PortfolioHolding.query.filter_by(
        customer_id=current_user.id
    ).all()

    cash_account = CashAccount.query.filter_by(
        customer_id=current_user.id
    ).first()

    portfolio_data = []
    total_portfolio_value = 0

    for holding in holdings:

        market_value = (
            holding.quantity *
            holding.stock.current_price
        )

        total_portfolio_value += market_value

        portfolio_data.append({
            "ticker": holding.stock.ticker,
            "shares": holding.quantity,
            "market_price": holding.stock.current_price,
            "market_value": market_value
        })

    return render_template(
        "portfolio.html",
        holdings=portfolio_data,
        total_portfolio_value=total_portfolio_value,
        cash_balance=cash_account.balance
    )
