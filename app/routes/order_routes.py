from flask import Blueprint, jsonify, request

from app.models.order import Order
from app.services.auth_service import (
    get_current_customer,
    login_required,
)
from app.services.order_service import (
    cancel_order,
    create_buy_order,
    create_sell_order,
)


order_bp = Blueprint(
    "orders",
    __name__,
    url_prefix="/orders",
)


def get_request_data():
    data = request.get_json(silent=True)

    if data is not None:
        return data

    return request.form


def serialize_order(order):
    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "stock_id": order.stock_id,
        "order_type": order.order_type,
        "quantity": order.quantity,
        "status": order.status,
        "submitted_at": (
            order.submitted_at.isoformat()
            if order.submitted_at
            else None
        ),
        "executed_at": (
            order.executed_at.isoformat()
            if order.executed_at
            else None
        ),
        "execution_price": (
            str(order.execution_price)
            if order.execution_price is not None
            else None
        ),
        "rejection_reason": order.rejection_reason,
    }


@order_bp.post("/buy")
@login_required
def buy_order():
    data = get_request_data()
    customer = get_current_customer()

    try:
        stock_id = int(data["stock_id"])
        quantity = int(data["quantity"])

        order = create_buy_order(
            customer_id=customer.id,
            stock_id=stock_id,
            quantity=quantity,
        )

        return jsonify(
            {
                "message": "Buy order submitted.",
                "order": serialize_order(order),
            }
        ), 201

    except (KeyError, TypeError, ValueError) as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400


@order_bp.post("/sell")
@login_required
def sell_order():
    data = get_request_data()
    customer = get_current_customer()

    try:
        stock_id = int(data["stock_id"])
        quantity = int(data["quantity"])

        order = create_sell_order(
            customer_id=customer.id,
            stock_id=stock_id,
            quantity=quantity,
        )

        return jsonify(
            {
                "message": "Sell order submitted.",
                "order": serialize_order(order),
            }
        ), 201

    except (KeyError, TypeError, ValueError) as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400


@order_bp.post("/<int:order_id>/cancel")
@login_required
def cancel_customer_order(order_id):
    customer = get_current_customer()

    try:
        order = cancel_order(
            order_id=order_id,
            customer_id=customer.id,
        )

        return jsonify(
            {
                "message": "Order cancelled.",
                "order": serialize_order(order),
            }
        ), 200

    except ValueError as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400


@order_bp.get("/history")
@login_required
def customer_orders():
    customer = get_current_customer()

    orders = (
        Order.query
        .filter_by(customer_id=customer.id)
        .order_by(
            Order.submitted_at.desc(),
            Order.id.desc(),
        )
        .all()
    )

    return jsonify(
        {
            "orders": [
                serialize_order(order)
                for order in orders
            ]
        }
    ), 200