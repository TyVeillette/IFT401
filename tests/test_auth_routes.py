import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
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


def create_customer(
    username="loginuser",
    password="TestPassword123!",
    is_admin=False,
):
    customer = Customer(
        full_name="Login Test Customer",
        username=username,
        email=f"{username}@example.com",
        password_hash=generate_password_hash(password),
        is_admin=is_admin,
    )

    db.session.add(customer)
    db.session.commit()

    return customer


def test_login_success(app, client):
    with app.app_context():
        customer = create_customer()

        response = client.post(
            "/auth/login",
            json={
                "username": "loginuser",
                "password": "TestPassword123!",
            },
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["message"] == "Login successful."
        assert data["customer"]["id"] == customer.id
        assert data["customer"]["username"] == "loginuser"
        assert data["customer"]["is_admin"] is False

        with client.session_transaction() as session:
            assert session["customer_id"] == customer.id


def test_login_rejects_wrong_password(app, client):
    with app.app_context():
        create_customer()

        response = client.post(
            "/auth/login",
            json={
                "username": "loginuser",
                "password": "wrong-password",
            },
        )

        assert response.status_code == 401
        assert (
            response.get_json()["error"]
            == "Invalid username or password."
        )


def test_login_rejects_unknown_user(app, client):
    with app.app_context():
        response = client.post(
            "/auth/login",
            json={
                "username": "doesnotexist",
                "password": "anything",
            },
        )

        assert response.status_code == 401


def test_session_reports_authenticated_user(app, client):
    with app.app_context():
        customer = create_customer(
            username="sessionuser"
        )

        client.post(
            "/auth/login",
            json={
                "username": "sessionuser",
                "password": "TestPassword123!",
            },
        )

        response = client.get(
            "/auth/session"
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["authenticated"] is True
        assert data["customer"]["id"] == customer.id


def test_session_reports_unauthenticated(client):
    response = client.get(
        "/auth/session"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["authenticated"] is False
    assert data["customer"] is None


def test_logout_clears_session(app, client):
    with app.app_context():
        create_customer()

        client.post(
            "/auth/login",
            json={
                "username": "loginuser",
                "password": "TestPassword123!",
            },
        )

        response = client.post(
            "/auth/logout"
        )

        assert response.status_code == 200

        session_response = client.get(
            "/auth/session"
        )

        assert (
            session_response.get_json()["authenticated"]
            is False
        )


def test_admin_login_reports_admin_status(app, client):
    with app.app_context():
        create_customer(
            username="adminlogin",
            is_admin=True,
        )

        response = client.post(
            "/auth/login",
            json={
                "username": "adminlogin",
                "password": "TestPassword123!",
            },
        )

        assert response.status_code == 200
        assert (
            response.get_json()["customer"]["is_admin"]
            is True
        )