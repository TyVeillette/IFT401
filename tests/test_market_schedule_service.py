import os
from datetime import date, datetime, time

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest

from app import create_app
from app.extensions import db
from app.services.market_schedule_service import (
    get_market_hours,
    get_market_schedule,
    is_market_open,
    set_market_holiday,
    set_market_hours,
)


@pytest.fixture
def app():
    app = create_app()

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_set_market_hours(app):
    with app.app_context():
        market_hours = set_market_hours(
            time(9, 30),
            time(16, 0),
        )

        assert market_hours.opening_time == time(9, 30)
        assert market_hours.closing_time == time(16, 0)

        saved_hours = get_market_hours()

        assert saved_hours.id == market_hours.id


def test_update_market_hours(app):
    with app.app_context():
        set_market_hours(
            time(9, 30),
            time(16, 0),
        )

        updated_hours = set_market_hours(
            time(8, 0),
            time(15, 0),
        )

        assert updated_hours.opening_time == time(8, 0)
        assert updated_hours.closing_time == time(15, 0)


def test_invalid_market_hours_rejected(app):
    with app.app_context():
        with pytest.raises(
            ValueError,
            match="Market opening time must occur before closing time",
        ):
            set_market_hours(
                time(16, 0),
                time(9, 30),
            )


def test_market_open_during_configured_hours(app, monkeypatch):
    with app.app_context():
        set_market_hours(
            time(9, 30),
            time(16, 0),
        )

        simulated_datetime = datetime(
            2026,
            9,
            21,
            10,
            0,
            0,
        )

        monkeypatch.setattr(
            "app.services.market_schedule_service.get_simulated_datetime",
            lambda: simulated_datetime,
        )

        assert is_market_open() is True


def test_market_closed_before_opening(app, monkeypatch):
    with app.app_context():
        set_market_hours(
            time(9, 30),
            time(16, 0),
        )

        simulated_datetime = datetime(
            2026,
            9,
            21,
            8,
            0,
            0,
        )

        monkeypatch.setattr(
            "app.services.market_schedule_service.get_simulated_datetime",
            lambda: simulated_datetime,
        )

        assert is_market_open() is False


def test_market_closed_at_closing_time(app, monkeypatch):
    with app.app_context():
        set_market_hours(
            time(9, 30),
            time(16, 0),
        )

        simulated_datetime = datetime(
            2026,
            9,
            21,
            16,
            0,
            0,
        )

        monkeypatch.setattr(
            "app.services.market_schedule_service.get_simulated_datetime",
            lambda: simulated_datetime,
        )

        assert is_market_open() is False


def test_market_closed_on_holiday(app, monkeypatch):
    with app.app_context():
        set_market_hours(
            time(9, 30),
            time(16, 0),
        )

        holiday_date = date(
            2026,
            9,
            21,
        )

        set_market_holiday(
            holiday_date,
            True,
        )

        simulated_datetime = datetime(
            2026,
            9,
            21,
            10,
            0,
            0,
        )

        monkeypatch.setattr(
            "app.services.market_schedule_service.get_simulated_datetime",
            lambda: simulated_datetime,
        )

        assert is_market_open() is False


def test_market_holiday_can_be_disabled(app):
    with app.app_context():
        simulated_date = date(
            2026,
            9,
            21,
        )

        set_market_holiday(
            simulated_date,
            True,
        )

        updated_schedule = set_market_holiday(
            simulated_date,
            False,
        )

        assert updated_schedule.is_holiday is False

        saved_schedule = get_market_schedule(
            simulated_date
        )

        assert saved_schedule.is_holiday is False


def test_missing_market_hours_raises_error(app, monkeypatch):
    with app.app_context():
        simulated_datetime = datetime(
            2026,
            9,
            21,
            10,
            0,
            0,
        )

        monkeypatch.setattr(
            "app.services.market_schedule_service.get_simulated_datetime",
            lambda: simulated_datetime,
        )

        with pytest.raises(
            RuntimeError,
            match="Market hours have not been configured",
        ):
            is_market_open()