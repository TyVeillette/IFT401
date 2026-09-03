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
from models import CashAccount, Transaction


@app.route("/deposit-cash", methods=["GET", "POST"])
@login_required
def deposit_cash():

    cash_account = CashAccount.query.filter_by(
        customer_id=current_user.id
    ).first()

    if request.method == "POST":

        amount = request.form.get(
            "amount",
            type=float
        )

        # Validation
        if amount is None or amount <= 0:

            flash(
                "Amount must be greater than zero.",
                "danger"
            )

            return render_template(
                "deposit_cash.html",
                cash_account=cash_account
            )

        # Update balance
        cash_account.balance += amount

        # Record transaction
        transaction = Transaction(
            customer_id=current_user.id,
            transaction_type="Deposit",
            amount=amount,
            resulting_balance=cash_account.balance
        )

        db.session.add(transaction)
        db.session.commit()

        flash(
            f"Deposit confirmed. Updated cash account balance: ${cash_account.balance:,.2f}",
            "success"
        )

        return redirect(
            url_for("deposit_cash")
        )

    return render_template(
        "deposit_cash.html",
        cash_account=cash_account
    )
