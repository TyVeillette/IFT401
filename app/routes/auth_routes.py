from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models.customer import Customer

auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
)


def serialize_customer(customer):
    return {
        "id": customer.id,
        "full_name": customer.full_name,
        "username": customer.username,
        "email": customer.email,
        "is_admin": customer.is_admin,
    }


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or request.form

    try:
        username = str(
            data["username"]
        ).strip()

        password = str(
            data["password"]
        )

        if not username or not password:
            raise ValueError(
                "Username and password are required."
            )

    except (KeyError, TypeError, ValueError) as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400

    customer = Customer.query.filter_by(
        username=username
    ).first()

    if customer is None:
        return jsonify(
            {
                "error": "Invalid username or password.",
            }
        ), 401

    if not check_password_hash(
        customer.password_hash,
        password,
    ):
        return jsonify(
            {
                "error": "Invalid username or password.",
            }
        ), 401

    session.clear()
    session["customer_id"] = customer.id

    return jsonify(
        {
            "message": "Login successful.",
            "customer": serialize_customer(
                customer
            ),
        }
    ), 200


@auth_bp.post("/logout")
def logout():
    session.clear()

    return jsonify(
        {
            "message": "Logout successful.",
        }
    ), 200


@auth_bp.get("/session")
def session_status():
    customer_id = session.get(
        "customer_id"
    )

    if customer_id is None:
        return jsonify(
            {
                "authenticated": False,
                "customer": None,
            }
        ), 200

    customer = db.session.get(
        Customer,
        customer_id,
    )

    if customer is None:
        session.clear()

        return jsonify(
            {
                "authenticated": False,
                "customer": None,
            }
        ), 200

    return jsonify(
        {
            "authenticated": True,
            "customer": serialize_customer(
                customer
            ),
        }
    ), 200