from datetime import datetime

from flask import Blueprint, jsonify, request

from app.services.auth_service import admin_required
from app.services.market_schedule_service import (
    get_market_hours,
    get_market_schedule,
    set_market_holiday,
    set_market_hours,
)

from app.services.admin_stock_service import (
    create_stock,
    get_all_stocks,
    set_stock_active,
)
from app.services.market_clock_service import (
    advance_clock,
    get_clock,
    get_simulated_datetime,
    pause_clock,
    resume_clock,
    set_simulated_datetime,
    set_speed_multiplier,
)

admin_market_bp = Blueprint(
    "admin_market",
    __name__,
    url_prefix="/admin/market",
)


def parse_time(value):
    try:
        return datetime.strptime(
            value,
            "%H:%M",
        ).time()
    except (TypeError, ValueError):
        raise ValueError(
            "Time must use HH:MM format."
        )


def parse_date(value):
    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d",
        ).date()
    except (TypeError, ValueError):
        raise ValueError(
            "Date must use YYYY-MM-DD format."
        )


@admin_market_bp.get("/hours")
@admin_required
def market_hours():
    hours = get_market_hours()

    if hours is None:
        return jsonify(
            {
                "opening_time": None,
                "closing_time": None,
            }
        ), 200

    return jsonify(
        {
            "opening_time": hours.opening_time.strftime(
                "%H:%M"
            ),
            "closing_time": hours.closing_time.strftime(
                "%H:%M"
            ),
        }
    ), 200


@admin_market_bp.post("/hours")
@admin_required
def update_market_hours():
    data = request.get_json(silent=True) or request.form

    try:
        opening_time = parse_time(
            data["opening_time"]
        )

        closing_time = parse_time(
            data["closing_time"]
        )

        hours = set_market_hours(
            opening_time,
            closing_time,
        )

        return jsonify(
            {
                "message": "Market hours updated.",
                "opening_time": (
                    hours.opening_time.strftime("%H:%M")
                ),
                "closing_time": (
                    hours.closing_time.strftime("%H:%M")
                ),
            }
        ), 200

    except (KeyError, TypeError, ValueError) as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400


@admin_market_bp.get("/schedule/<string:date_value>")
@admin_required
def market_schedule(date_value):
    try:
        simulated_date = parse_date(date_value)

        schedule = get_market_schedule(
            simulated_date
        )

        return jsonify(
            {
                "simulated_date": simulated_date.isoformat(),
                "is_holiday": (
                    schedule.is_holiday
                    if schedule is not None
                    else False
                ),
            }
        ), 200

    except ValueError as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400


@admin_market_bp.post("/holiday")
@admin_required
def update_market_holiday():
    data = request.get_json(silent=True) or request.form

    try:
        simulated_date = parse_date(
            data["simulated_date"]
        )

        is_holiday = data["is_holiday"]

        if not isinstance(is_holiday, bool):
            raise ValueError(
                "is_holiday must be true or false."
            )

        schedule = set_market_holiday(
            simulated_date,
            is_holiday,
        )

        return jsonify(
            {
                "message": "Market schedule updated.",
                "simulated_date": (
                    schedule.simulated_date.isoformat()
                ),
                "is_holiday": schedule.is_holiday,
            }
        ), 200

    except (KeyError, TypeError, ValueError) as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400
# ---------------------------------------------------------------------------
# Stock administration
# ---------------------------------------------------------------------------

def parse_datetime(value):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(
            "Datetime must use ISO format."
        )


def serialize_stock(stock):
    return {
        "id": stock.id,
        "company_name": stock.company_name,
        "ticker": stock.ticker,
        "exchange": stock.exchange,
        "sector": stock.sector,
        "initial_price": str(stock.initial_price),
        "current_price": str(stock.current_price),
        "open_price": str(stock.open_price),
        "high_price": str(stock.high_price),
        "low_price": str(stock.low_price),
        "volume": stock.volume,
        "is_active": stock.is_active,
    }


def serialize_clock(clock):
    return {
        "simulated_datetime": (
            get_simulated_datetime().isoformat()
        ),
        "simulated_anchor": (
            clock.simulated_anchor.isoformat()
        ),
        "real_anchor": (
            clock.real_anchor.isoformat()
        ),
        "is_running": clock.is_running,
        "speed_multiplier": str(
            clock.speed_multiplier
        ),
    }


@admin_market_bp.get("/stocks")
@admin_required
def admin_stocks():
    stocks = get_all_stocks()

    return jsonify(
        {
            "stocks": [
                serialize_stock(stock)
                for stock in stocks
            ]
        }
    ), 200


@admin_market_bp.post("/stocks")
@admin_required
def admin_create_stock():
    data = request.get_json(silent=True) or request.form

    try:
        stock = create_stock(
            company_name=data["company_name"],
            ticker=data["ticker"],
            initial_price=data["initial_price"],
            volume=data["volume"],
            exchange=data.get("exchange"),
            sector=data.get("sector"),
        )

        return jsonify(
            {
                "message": "Stock created.",
                "stock": serialize_stock(stock),
            }
        ), 201

    except (KeyError, TypeError, ValueError) as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400


@admin_market_bp.post(
    "/stocks/<int:stock_id>/active"
)
@admin_required
def admin_set_stock_active(stock_id):
    data = request.get_json(silent=True) or request.form

    try:
        stock = set_stock_active(
            stock_id,
            data["is_active"],
        )

        return jsonify(
            {
                "message": "Stock status updated.",
                "stock": serialize_stock(stock),
            }
        ), 200

    except (KeyError, TypeError, ValueError) as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400


# ---------------------------------------------------------------------------
# Simulated market clock administration
# ---------------------------------------------------------------------------

@admin_market_bp.get("/clock")
@admin_required
def market_clock():
    clock = get_clock()

    if clock is None:
        return jsonify(
            {
                "configured": False,
            }
        ), 200

    result = serialize_clock(clock)
    result["configured"] = True

    return jsonify(result), 200


@admin_market_bp.post("/clock")
@admin_required
def update_market_clock():
    data = request.get_json(silent=True) or request.form

    try:
        simulated_datetime = parse_datetime(
            data["simulated_datetime"]
        )

        clock = set_simulated_datetime(
            simulated_datetime
        )

        return jsonify(
            {
                "message": "Simulated datetime updated.",
                "clock": serialize_clock(clock),
            }
        ), 200

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400


@admin_market_bp.post("/clock/pause")
@admin_required
def pause_market_clock():
    try:
        clock = pause_clock()

        return jsonify(
            {
                "message": "Market clock paused.",
                "clock": serialize_clock(clock),
            }
        ), 200

    except RuntimeError as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400


@admin_market_bp.post("/clock/resume")
@admin_required
def resume_market_clock():
    try:
        clock = resume_clock()

        return jsonify(
            {
                "message": "Market clock resumed.",
                "clock": serialize_clock(clock),
            }
        ), 200

    except RuntimeError as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400


@admin_market_bp.post("/clock/speed")
@admin_required
def update_clock_speed():
    data = request.get_json(silent=True) or request.form

    try:
        multiplier = float(
            data["speed_multiplier"]
        )

        clock = set_speed_multiplier(
            multiplier
        )

        return jsonify(
            {
                "message": "Clock speed updated.",
                "clock": serialize_clock(clock),
            }
        ), 200

    except (
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400


@admin_market_bp.post("/clock/advance")
@admin_required
def advance_market_clock():
    data = request.get_json(silent=True) or request.form

    try:
        minutes = float(
            data["minutes"]
        )

        clock = advance_clock(
            minutes
        )

        return jsonify(
            {
                "message": "Market clock advanced.",
                "clock": serialize_clock(clock),
            }
        ), 200

    except (
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400
