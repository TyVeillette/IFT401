from app.services import market_tick_service


def test_closed_market_does_not_run_tick(monkeypatch):
    update_called = False
    orders_called = False

    def fake_update():
        nonlocal update_called
        update_called = True
        return []

    def fake_orders():
        nonlocal orders_called
        orders_called = True
        return []

    monkeypatch.setattr(
        market_tick_service,
        "is_market_open",
        lambda: False,
    )

    monkeypatch.setattr(
        market_tick_service,
        "update_all_active_stocks",
        fake_update,
    )

    monkeypatch.setattr(
        market_tick_service,
        "process_pending_orders",
        fake_orders,
    )

    result = market_tick_service.run_market_tick()

    assert result["market_open"] is False
    assert result["price_snapshots"] == []
    assert result["processed_orders"] == []

    assert update_called is False
    assert orders_called is False


def test_open_market_updates_prices_and_orders(monkeypatch):
    snapshots = ["snapshot-1", "snapshot-2"]
    orders = ["order-1"]

    monkeypatch.setattr(
        market_tick_service,
        "is_market_open",
        lambda: True,
    )

    monkeypatch.setattr(
        market_tick_service,
        "update_all_active_stocks",
        lambda: snapshots,
    )

    monkeypatch.setattr(
        market_tick_service,
        "process_pending_orders",
        lambda: orders,
    )

    result = market_tick_service.run_market_tick()

    assert result["market_open"] is True
    assert result["price_snapshots"] == snapshots
    assert result["processed_orders"] == orders


def test_prices_update_before_orders_execute(monkeypatch):
    events = []

    monkeypatch.setattr(
        market_tick_service,
        "is_market_open",
        lambda: True,
    )

    def fake_update():
        events.append("prices")
        return []

    def fake_orders():
        events.append("orders")
        return []

    monkeypatch.setattr(
        market_tick_service,
        "update_all_active_stocks",
        fake_update,
    )

    monkeypatch.setattr(
        market_tick_service,
        "process_pending_orders",
        fake_orders,
    )

    market_tick_service.run_market_tick()

    assert events == [
        "prices",
        "orders",
    ]