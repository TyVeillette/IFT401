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
    CashAccount
)


@app.route("/buy-stock/<string:ticker>", methods=["GET", "POST"])
@login_required
def buy_stock(ticker):

    stock = Stock.query.filter_by(
        ticker=ticker
    ).first_or_404()

    cash_account = CashAccount.query.filter_by(
        customer_id=current_user.id
    ).first()

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
                "buy_stock.html",
                stock=stock,
                cash_account=cash_account
            )

        estimated_cost = quantity * stock.current_price

        # Create pending buy order
        order = Order(
            customer_id=current_user.id,
            stock_id=stock.id,
            order_type="BUY",
            quantity=quantity,
            status="Pending"
        )

        db.session.add(order)
        db.session.commit()

        flash(
            "Order submitted. Pending Execution.",
            "success"
        )

        return redirect(
            url_for(
                "buy_stock",
                ticker=ticker
            )
        )

    return render_template(
        "buy_stock.html",
        stock=stock,
        cash_account=cash_account
    )
