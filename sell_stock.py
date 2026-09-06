from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_required,
    current_user
)

from app import app, db
from models import (
    Stock,
    Order,
    PortfolioHolding
)


@app.route("/sell-stock/<string:ticker>", methods=["GET", "POST"])
@login_required
def sell_stock(ticker):

    stock = Stock.query.filter_by(
        ticker=ticker
    ).first_or_404()

    holding = PortfolioHolding.query.filter_by(
        customer_id=current_user.id,
        stock_id=stock.id
    ).first()

    available_shares = 0

    if holding:
        available_shares = holding.quantity

    if request.method == "POST":

        quantity = request.form.get(
            "quantity",
            type=int
        )

        # Validate quantity
        if quantity is None or quantity <= 0:

            flash(
                "Quantity must be greater than zero.",
                "danger"
            )

            return render_template(
                "sell_stock.html",
                stock=stock,
                available_shares=available_shares
            )

        # Verify ownership
        if quantity > available_shares:

            flash(
                "Cannot sell more shares than currently owned.",
                "danger"
            )

            return render_template(
                "sell_stock.html",
                stock=stock,
                available_shares=available_shares
            )

        estimated_proceeds = quantity * stock.current_price

        # Create pending sell order
        order = Order(
            customer_id=current_user.id,
            stock_id=stock.id,
            order_type="SELL",
            quantity=quantity,
            status="Pending"
        )

        db.session.add(order)
        db.session.commit()

        flash(
            f"Sell order submitted. Estimated proceeds: ${estimated_proceeds:.2f}. Pending Execution.",
            "success"
        )

        return redirect(
            url_for(
                "sell_stock",
                ticker=ticker
            )
        )

    return render_template(
        "sell_stock.html",
        stock=stock,
        available_shares=
