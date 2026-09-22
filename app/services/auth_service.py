from functools import wraps

from flask import jsonify, session

from app.extensions import db
from app.models.customer import Customer


def get_current_customer():
    customer_id = session.get("customer_id")

    if customer_id is None:
        return None

    return db.session.get(Customer, customer_id)


def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        customer = get_current_customer()

        if customer is None:
            return jsonify(
                {
                    "error": "Authentication required.",
                }
            ), 401

        return view_function(*args, **kwargs)

    return wrapped_view


def admin_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        customer = get_current_customer()

        if customer is None:
            return jsonify(
                {
                    "error": "Authentication required.",
                }
            ), 401

        if not customer.is_admin:
            return jsonify(
                {
                    "error": "Administrator access required.",
                }
            ), 403

        return view_function(*args, **kwargs)

    return wrapped_view