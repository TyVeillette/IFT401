import random
from decimal import Decimal, ROUND_HALF_UP

from app.models.price_history import PriceHistory
from app.models.stock import Stock
from app.services.market_clock_service import get_simulated_datetime
from app.services.price_history_service import record_price


MINIMUM_PRICE = Decimal("0.01")
DEFAULT_MAX_MOVE_BPS = 50


def round_price(price):
    return max(
        Decimal(price).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        ),
        MINIMUM_PRICE
    )


def generate_new_price(
    current_price,
    max_move_bps=DEFAULT_MAX_MOVE_BPS
):
    if max_move_bps <= 0:
        raise ValueError(
            "Maximum price movement must be greater than zero."
        )

    movement_bps = random.randint(
        -max_move_bps,
        max_move_bps
    )

    movement_rate = (
        Decimal(movement_bps)
        / Decimal("10000")
    )

    new_price = (
        Decimal(current_price)
        * (Decimal("1") + movement_rate)
    )

    return round_price(new_price)


def is_new_simulated_day(stock_id, simulated_datetime):
    latest_snapshot = (
        PriceHistory.query
        .filter_by(stock_id=stock_id)
        .order_by(
            PriceHistory.simulated_datetime.desc()
        )
        .first()
    )

    if latest_snapshot is None:
        return True

    return (
        latest_snapshot.simulated_datetime.date()
        != simulated_datetime.date()
    )


def update_stock_price(stock):
    if not stock.is_active:
        raise ValueError(
            "Cannot generate a price for an inactive stock."
        )

    simulated_datetime = get_simulated_datetime()

    new_price = generate_new_price(
        stock.current_price
    )

    if is_new_simulated_day(
        stock.id,
        simulated_datetime
    ):
        stock.open_price = new_price
        stock.high_price = new_price
        stock.low_price = new_price
    else:
        if new_price > stock.high_price:
            stock.high_price = new_price

        if new_price < stock.low_price:
            stock.low_price = new_price

    stock.current_price = new_price

    snapshot = record_price(
        stock_id=stock.id,
        price=new_price,
        volume=stock.volume
    )

    return snapshot


def update_all_active_stocks():
    active_stocks = Stock.query.filter_by(
        is_active=True
    ).all()

    snapshots = []

    for stock in active_stocks:
        snapshot = update_stock_price(stock)
        snapshots.append(snapshot)

    return snapshots