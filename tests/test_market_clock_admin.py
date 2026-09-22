import os
from datetime import datetime
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest

from app import create_app
from app.extensions import db
from app.services.market_clock_service import (
    advance_clock,
    create_clock,
    get_simulated_datetime,
    pause_clock,
    resume_clock,
    set_simulated_datetime,
    set_speed_multiplier,
)


START_TIME = datetime(
    2026,
    9,
    22,
    9,
    30,
)


@pytest.fixture
def app():
    app = create_app()

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_create_clock(app, monkeypatch):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_clock_service.utc_now",
            lambda: datetime(2026, 9, 22, 14, 0),
        )

        clock = create_clock(START_TIME)

        assert clock.simulated_anchor == START_TIME
        assert clock.is_running is True
        assert clock.speed_multiplier == Decimal("1.00")


def test_set_simulated_datetime(app, monkeypatch):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_clock_service.utc_now",
            lambda: datetime(2026, 9, 22, 14, 0),
        )

        create_clock(START_TIME)

        new_time = datetime(
            2026,
            9,
            23,
            10,
            15,
        )

        clock = set_simulated_datetime(new_time)

        assert clock.simulated_anchor == new_time


def test_pause_and_resume_clock(app, monkeypatch):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_clock_service.utc_now",
            lambda: datetime(2026, 9, 22, 14, 0),
        )

        create_clock(START_TIME)

        clock = pause_clock()

        assert clock.is_running is False

        paused_time = get_simulated_datetime()

        assert paused_time == START_TIME

        clock = resume_clock()

        assert clock.is_running is True


def test_set_speed_multiplier(app, monkeypatch):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_clock_service.utc_now",
            lambda: datetime(2026, 9, 22, 14, 0),
        )

        create_clock(START_TIME)

        clock = set_speed_multiplier(2.5)

        assert clock.speed_multiplier == Decimal("2.50")


def test_invalid_speed_multiplier_rejected(
    app,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_clock_service.utc_now",
            lambda: datetime(2026, 9, 22, 14, 0),
        )

        create_clock(START_TIME)

        with pytest.raises(
            ValueError,
            match="greater than zero",
        ):
            set_speed_multiplier(0)


def test_advance_clock(app, monkeypatch):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_clock_service.utc_now",
            lambda: datetime(2026, 9, 22, 14, 0),
        )

        create_clock(START_TIME)

        clock = advance_clock(45)

        assert clock.simulated_anchor == datetime(
            2026,
            9,
            22,
            10,
            15,
        )


def test_invalid_advance_rejected(
    app,
    monkeypatch,
):
    with app.app_context():
        monkeypatch.setattr(
            "app.services.market_clock_service.utc_now",
            lambda: datetime(2026, 9, 22, 14, 0),
        )

        create_clock(START_TIME)

        with pytest.raises(
            ValueError,
            match="greater than zero",
        ):
            advance_clock(0)