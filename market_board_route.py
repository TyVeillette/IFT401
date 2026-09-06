from flask import (
    render_template,
    redirect,
    url_for
)

from flask_login import (
    login_required
)

from app import app
from models import Stock


@app.route("/market-board")
@login_required
def market_board():

    stocks = Stock.query.order_by(
        Stock.ticker
    ).all()

    return render_template(
        "market_board.html",
        stocks=stocks,
        market_status="Open"
    )
