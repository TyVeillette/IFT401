from app.services.market_schedule_service import is_market_open
from app.services.order_service import process_pending_orders
from app.services.price_generator_service import update_all_active_stocks


def run_market_tick():
    if not is_market_open():
        return {
            "market_open": False,
            "price_snapshots": [],
            "processed_orders": [],
        }

    price_snapshots = update_all_active_stocks()

    processed_orders = process_pending_orders()

    return {
        "market_open": True,
        "price_snapshots": price_snapshots,
        "processed_orders": processed_orders,
    }