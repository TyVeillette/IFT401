from flask import Blueprint, jsonify

from app.services.market_board_service import get_market_board


market_bp = Blueprint(
    "market",
    __name__,
    url_prefix="/market",
)


@market_bp.get("")
def market_board():
    board = get_market_board()

    return jsonify(
        {
            "market_open": board["market_open"],
            "stocks": [
                {
                    "stock_id": stock["stock_id"],
                    "ticker": stock["ticker"],
                    "company_name": stock["company_name"],
                    "current_price": str(
                        stock["current_price"]
                    ),
                    "volume": stock["volume"],
                    "market_cap": str(
                        stock["market_cap"]
                    ),
                    "open_price": str(
                        stock["open_price"]
                    ),
                    "high_price": str(
                        stock["high_price"]
                    ),
                    "low_price": str(
                        stock["low_price"]
                    ),
                }
                for stock in board["stocks"]
            ],
        }
    ), 200