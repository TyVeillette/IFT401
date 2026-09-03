from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from app import app, db
from models import Customer, CashAccount


@app.route("/create-account", methods=["GET", "POST"])
def create_account():

    if request.method == "POST":

        full_name = request.form.get("full_name")
        username = request.form.get("username")
        email = request.form.get("email")

        # Optional admin checkbox
        is_admin = request.form.get("is_admin") == "on"

        # Required field validation
        if not full_name or not username or not email:

            flash(
                "All fields are required.",
                "danger"
            )

            return render_template(
                "create_account.html"
            )

        # Username availability check
        existing_user = Customer.query.filter_by(
            username=username
        ).first()

        if existing_user:

            flash(
                "Username unavailable. Choose another username.",
                "warning"
            )

            return render_template(
                "create_account.html",
                full_name=full_name,
                email=email
            )

        # Create account
        customer = Customer(
            full_name=full_name,
            username=username,
            email=email,
            is_admin=is_admin
        )

        db.session.add(customer)
        db.session.commit()

        # Create associated cash account
        cash_account = CashAccount(
            customer_id=customer.id,
            balance=0.00
        )

        db.session.add(cash_account)
        db.session.commit()

        flash(
            "Account created successfully. Cash account created.",
            "success"
        )

        return redirect(
            url_for("create_account")
        )

    return render_template(
        "create_account.html"
    )
