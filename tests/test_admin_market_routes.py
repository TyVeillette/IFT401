import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest

from app import create_app
from app.extensions import db


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


def test_get_unconfigured_market_hours(client):
    response = client.get(
        "/admin/market/hours"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["opening_time"] is None
    assert data["closing_time"] is None


def test_set_market_hours(client):
    response = client.post(
        "/admin/market/hours",
        json={
            "opening_time": "09:30",
            "closing_time": "16:00",
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["opening_time"] == "09:30"
    assert data["closing_time"] == "16:00"


def test_reject_invalid_market_hours(client):
    response = client.post(
        "/admin/market/hours",
        json={
            "opening_time": "16:00",
            "closing_time": "09:30",
        },
    )

    assert response.status_code == 400

    data = response.get_json()

    assert (
        data["error"]
        == "Market opening time must occur before closing time."
    )


def test_reject_invalid_time_format(client):
    response = client.post(
        "/admin/market/hours",
        json={
            "opening_time": "9:30 AM",
            "closing_time": "4:00 PM",
        },
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["error"] == "Time must use HH:MM format."


def test_set_market_holiday(client):
    response = client.post(
        "/admin/market/holiday",
        json={
            "simulated_date": "2026-12-25",
            "is_holiday": True,
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["simulated_date"] == "2026-12-25"
    assert data["is_holiday"] is True


def test_disable_market_holiday(client):
    client.post(
        "/admin/market/holiday",
        json={
            "simulated_date": "2026-12-25",
            "is_holiday": True,
        },
    )

    response = client.post(
        "/admin/market/holiday",
        json={
            "simulated_date": "2026-12-25",
            "is_holiday": False,
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["is_holiday"] is False


def test_get_market_schedule(client):
    client.post(
        "/admin/market/holiday",
        json={
            "simulated_date": "2026-12-25",
            "is_holiday": True,
        },
    )

    response = client.get(
        "/admin/market/schedule/2026-12-25"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["simulated_date"] == "2026-12-25"
    assert data["is_holiday"] is True


def test_reject_invalid_date(client):
    response = client.post(
        "/admin/market/holiday",
        json={
            "simulated_date": "12/25/2026",
            "is_holiday": True,
        },
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["error"] == "Date must use YYYY-MM-DD format."


def test_reject_non_boolean_holiday_value(client):
    response = client.post(
        "/admin/market/holiday",
        json={
            "simulated_date": "2026-12-25",
            "is_holiday": "yes",
        },
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["error"] == "is_holiday must be true or false."