from app.extensions import db
from app.models.order import Order


def cancel_order(order_id, customer_id=None):
    order = db.session.get(Order, order_id)

    if order is None:
        raise ValueError("Order not found.")

    if customer_id is not None and order.customer_id != customer_id:
        raise ValueError("Order does not belong to this customer.")

    if order.status != "Pending":
        raise ValueError(
            f"Only Pending orders can be cancelled. "
            f"Current status: {order.status}."
        )

    order.status = "Cancelled"

    db.session.commit()

    return order