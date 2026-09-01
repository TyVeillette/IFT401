from datetime import datetime
from time import sleep

from run import app
from app.services.market_clock_service import (
    set_simulated_datetime,
    get_simulated_datetime,
    set_speed_multiplier
)


with app.app_context():
    set_simulated_datetime(
        datetime(2026, 9, 1, 12, 0, 0)
    )

    set_speed_multiplier(10)

    first_time = get_simulated_datetime()

    print("Starting simulated time:")
    print(first_time)

    print("\nWaiting 5 real seconds...")
    sleep(5)

    second_time = get_simulated_datetime()

    print("\nEnding simulated time:")
    print(second_time)

    simulated_elapsed = second_time - first_time

    print("\nSimulated seconds elapsed:")
    print(simulated_elapsed.total_seconds())