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
from models import Order


@app.route("/cancel-order")
@login_required
def cancel_order_page():

    pending_orders = Order.query.filter_by(
        customer_id=current_user.id,
        status="Pending"
    ).all()

    return render_template(
        "cancel_order.html",
        pending_orders=pending_orders
    )
