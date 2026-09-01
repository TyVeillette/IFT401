from app.extensions import db
from app.models.price_history import PriceHistory
from app.services.market_clock_service import get_simulated_datetime


def record_price(stock_id, price, volume=0):
    snapshot = PriceHistory(
        stock_id=stock_id,
        simulated_datetime=get_simulated_datetime(),
        price=price,
        volume=volume
    )

    db.session.add(snapshot)
    db.session.commit()

    return snapshot


def get_stock_history(stock_id, start_time=None, end_time=None):
    query = PriceHistory.query.filter_by(
        stock_id=stock_id
    )

    if start_time is not None:
        query = query.filter(
            PriceHistory.simulated_datetime >= start_time
        )

    if end_time is not None:
        query = query.filter(
            PriceHistory.simulated_datetime <= end_time
        )

    return query.order_by(
        PriceHistory.simulated_datetime.asc()
    ).all()