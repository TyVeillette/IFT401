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


def test_market_tick_command_when_closed(
    app,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.commands.market_commands.run_market_tick",
        lambda: {
            "market_open": False,
            "price_snapshots": [],
            "processed_orders": [],
        },
    )

    runner = app.test_cli_runner()

    result = runner.invoke(
        args=["market-tick"]
    )

    assert result.exit_code == 0

    assert (
        "Market closed. No tick executed."
        in result.output
    )


def test_market_tick_command_when_open(
    app,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.commands.market_commands.run_market_tick",
        lambda: {
            "market_open": True,
            "price_snapshots": [
                "snapshot-1",
                "snapshot-2",
            ],
            "processed_orders": [
                "order-1",
            ],
        },
    )

    runner = app.test_cli_runner()

    result = runner.invoke(
        args=["market-tick"]
    )

    assert result.exit_code == 0

    assert (
        "2 stock prices updated"
        in result.output
    )

    assert (
        "1 orders processed"
        in result.output
    )