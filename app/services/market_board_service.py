from decimal import Decimal

from app.models.stock import Stock
from app.services.market_schedule_service import is_market_open


def get_market_board():
    stocks = (
        Stock.query
        .filter_by(is_active=True)
        .order_by(Stock.ticker.asc())
        .all()
    )

    market_open = is_market_open()

    results = []

    for stock in stocks:
        current_price = Decimal(
            str(stock.current_price)
        )

        market_cap = (
            current_price
            * stock.volume
        )

        results.append(
            {
                "stock_id": stock.id,
                "ticker": stock.ticker,
                "company_name": stock.company_name,
                "current_price": current_price,
                "volume": stock.volume,
                "market_cap": market_cap,
                "open_price": Decimal(
                    str(stock.open_price)
                ),
                "high_price": Decimal(
                    str(stock.high_price)
                ),
                "low_price": Decimal(
                    str(stock.low_price)
                ),
            }
        )

    return {
        "market_open": market_open,
        "stocks": results,
    }