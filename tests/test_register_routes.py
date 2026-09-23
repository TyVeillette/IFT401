import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest

from app import create_app
from app.extensions import db
from app.models.cash_account import CashAccount
from app.models.customer import Customer


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


NEW_ACCOUNT = {
    "full_name": "Route Customer",
    "username": "routeuser",
    "email": "routeuser@example.com",
    "password": "Password123!",
}


def test_register_creates_account_and_signs_in(app, client):
    with app.app_context():
        response = client.post(
            "/auth/register",
            json=NEW_ACCOUNT,
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data["message"] == "Account created. Cash account created."
        assert data["customer"]["username"] == "routeuser"
        assert data["customer"]["is_admin"] is False
        assert "password_hash" not in data["customer"]

        customer = Customer.query.filter_by(
            username="routeuser"
        ).one()

        assert CashAccount.query.filter_by(
            customer_id=customer.id
        ).count() == 1

        with client.session_transaction() as session:
            assert session["customer_id"] == customer.id

        session_response = client.get("/auth/session")

        assert session_response.get_json()["authenticated"] is True


def test_register_accepts_form_data(app, client):
    with app.app_context():
        response = client.post(
            "/auth/register",
            data=NEW_ACCOUNT,
        )

        assert response.status_code == 201


def test_new_account_can_log_in(app, client):
    with app.app_context():
        client.post(
            "/auth/register",
            json=NEW_ACCOUNT,
        )
        client.post("/auth/logout")

        response = client.post(
            "/auth/login",
            json={
                "username": "routeuser",
                "password": "Password123!",
            },
        )

        assert response.status_code == 200


def test_register_ignores_is_admin(app, client):
    with app.app_context():
        response = client.post(
            "/auth/register",
            json={
                **NEW_ACCOUNT,
                "is_admin": True,
            },
        )

        assert response.status_code == 201
        assert response.get_json()["customer"]["is_admin"] is False


def test_register_rejects_taken_username(app, client):
    with app.app_context():
        client.post(
            "/auth/register",
            json=NEW_ACCOUNT,
        )

        response = client.post(
            "/auth/register",
            json={
                **NEW_ACCOUNT,
                "email": "someone-else@example.com",
            },
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == (
            "Username unavailable. Choose another username."
        )


def test_register_rejects_missing_fields(app, client):
    with app.app_context():
        response = client.post(
            "/auth/register",
            json={},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "Full name is required."
        assert Customer.query.count() == 0

        with client.session_transaction() as session:
            assert "customer_id" not in session
