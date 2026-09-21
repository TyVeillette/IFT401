from app.extensions import db
from app.models.market_hours import MarketHours
from app.models.market_schedule import MarketSchedule
from app.services.market_clock_service import get_simulated_datetime


MARKET_HOURS_ID = 1


def get_market_hours():
    return db.session.get(MarketHours, MARKET_HOURS_ID)


def set_market_hours(opening_time, closing_time):
    if opening_time >= closing_time:
        raise ValueError(
            "Market opening time must occur before closing time."
        )

    market_hours = get_market_hours()

    if market_hours is None:
        market_hours = MarketHours(
            id=MARKET_HOURS_ID,
            opening_time=opening_time,
            closing_time=closing_time,
        )
        db.session.add(market_hours)
    else:
        market_hours.opening_time = opening_time
        market_hours.closing_time = closing_time

    db.session.commit()

    return market_hours


def get_market_schedule(simulated_date):
    return MarketSchedule.query.filter_by(
        simulated_date=simulated_date
    ).first()


def set_market_holiday(simulated_date, is_holiday):
    schedule = get_market_schedule(simulated_date)

    if schedule is None:
        schedule = MarketSchedule(
            simulated_date=simulated_date,
            is_holiday=is_holiday,
        )
        db.session.add(schedule)
    else:
        schedule.is_holiday = is_holiday

    db.session.commit()

    return schedule


def is_market_open():
    simulated_datetime = get_simulated_datetime()

    market_hours = get_market_hours()

    if market_hours is None:
        raise RuntimeError(
            "Market hours have not been configured."
        )

    schedule = get_market_schedule(
        simulated_datetime.date()
    )

    if schedule is not None and schedule.is_holiday:
        return False

    current_time = simulated_datetime.time()

    return (
        market_hours.opening_time
        <= current_time
        < market_hours.closing_time
    )