from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.extensions import db
from app.models.stock import Stock


MONEY_INCREMENT = Decimal("0.01")


def normalize_price(value):
    try:
        price = Decimal(str(value)).quantize(
            MONEY_INCREMENT,
            rounding=ROUND_HALF_UP,
        )
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Price must be a valid number.")

    if price <= 0:
        raise ValueError("Price must be greater than zero.")

    return price


def normalize_volume(value):
    try:
        volume = int(value)
    except (TypeError, ValueError):
        raise ValueError("Volume must be a valid integer.")

    if volume < 0:
        raise ValueError("Volume cannot be negative.")

    return volume


def create_stock(
    company_name,
    ticker,
    initial_price,
    volume,
    exchange=None,
    sector=None,
):
    company_name = str(company_name).strip()
    ticker = str(ticker).strip().upper()

    if not company_name:
        raise ValueError("Company name is required.")

    if not ticker:
        raise ValueError("Ticker is required.")

    if len(ticker) > 10:
        raise ValueError(
            "Ticker cannot exceed 10 characters."
        )

    existing = Stock.query.filter_by(
        ticker=ticker
    ).first()

    if existing is not None:
        raise ValueError(
            "A stock with that ticker already exists."
        )

    price = normalize_price(initial_price)
    volume = normalize_volume(volume)

    stock = Stock(
        company_name=company_name,
        ticker=ticker,
        exchange=(
            str(exchange).strip()
            if exchange
            else None
        ),
        sector=(
            str(sector).strip()
            if sector
            else None
        ),
        initial_price=price,
        current_price=price,
        open_price=price,
        high_price=price,
        low_price=price,
        volume=volume,
        is_active=True,
    )

    db.session.add(stock)
    db.session.commit()

    return stock


def get_all_stocks():
    return (
        Stock.query
        .order_by(Stock.ticker.asc())
        .all()
    )


def set_stock_active(stock_id, is_active):
    if not isinstance(is_active, bool):
        raise ValueError(
            "is_active must be true or false."
        )

    stock = db.session.get(
        Stock,
        stock_id,
    )

    if stock is None:
        raise ValueError("Stock not found.")

    stock.is_active = is_active

    db.session.commit()

    return stock