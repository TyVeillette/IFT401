from datetime import datetime

from flask import Blueprint, jsonify, request

from app.services.market_schedule_service import (
    get_market_hours,
    get_market_schedule,
    set_market_holiday,
    set_market_hours,
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