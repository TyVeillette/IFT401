from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models.market_clock import MarketClock


CLOCK_ID = 1


def utc_now():
    return datetime.now(timezone.utc)


def get_clock():
    return db.session.get(MarketClock, CLOCK_ID)


def create_clock(simulated_datetime):
    clock = MarketClock(
        id=CLOCK_ID,
        simulated_anchor=simulated_datetime,
        real_anchor=utc_now(),
        is_running=True,
        speed_multiplier=1.00
    )

    db.session.add(clock)
    db.session.commit()

    return clock


def get_simulated_datetime():
    clock = get_clock()

    if clock is None:
        raise RuntimeError("Market clock has not been configured.")

    if not clock.is_running:
        return clock.simulated_anchor

    elapsed_real_time = utc_now().replace(tzinfo=None) - clock.real_anchor

    multiplier = float(clock.speed_multiplier)

    elapsed_simulated_time = timedelta(
        seconds=elapsed_real_time.total_seconds() * multiplier
    )

    return clock.simulated_anchor + elapsed_simulated_time


def set_simulated_datetime(simulated_datetime):
    clock = get_clock()

    if clock is None:
        return create_clock(simulated_datetime)

    clock.simulated_anchor = simulated_datetime
    clock.real_anchor = utc_now().replace(tzinfo=None)

    db.session.commit()

    return clock


def pause_clock():
    clock = get_clock()

    if clock is None:
        raise RuntimeError("Market clock has not been configured.")

    current_simulated_time = get_simulated_datetime()

    clock.simulated_anchor = current_simulated_time
    clock.real_anchor = utc_now().replace(tzinfo=None)
    clock.is_running = False

    db.session.commit()

    return clock


def resume_clock():
    clock = get_clock()

    if clock is None:
        raise RuntimeError("Market clock has not been configured.")

    clock.real_anchor = utc_now().replace(tzinfo=None)
    clock.is_running = True

    db.session.commit()

    return clock


def set_speed_multiplier(multiplier):
    if multiplier <= 0:
        raise ValueError("Clock speed multiplier must be greater than zero.")

    clock = get_clock()

    if clock is None:
        raise RuntimeError("Market clock has not been configured.")

    current_simulated_time = get_simulated_datetime()

    clock.simulated_anchor = current_simulated_time
    clock.real_anchor = utc_now().replace(tzinfo=None)
    clock.speed_multiplier = multiplier

    db.session.commit()

    return clock