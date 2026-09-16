import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import (
    CashAccount,
    Customer,
    MarketClock,
    MarketHours,
    MarketSchedule,
    Order,
    PortfolioHolding,
    PriceHistory,
    Stock,
    Transaction,
)
from app.services.market_clock_service import CLOCK_ID, utc_now


SEED_PASSWORD = "Password123!"

BUY = "Buy"
SELL = "Sell"
DEPOSIT = "Deposit"
WITHDRAWAL = "Withdrawal"

PENDING = "Pending"
EXECUTED = "Executed"
CANCELLED = "Cancelled"
REJECTED = "Rejected"

SIMULATED_NOW = datetime(2026, 9, 14, 10, 0)

MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)

HISTORY_DAYS = (
    date(2026, 9, 9),
    date(2026, 9, 10),
    date(2026, 9, 11),
)

# ADM-307
HOLIDAYS = {
    date(2026, 9, 7): True,
    date(2026, 9, 14): False,
    date(2026, 11, 26): True,
    date(2026, 12, 25): True,
}

# SAD Wireframe 8 values for the first four
# ticker, company, exchange, sector, current, volume, open, high, low, active
STOCKS = (
    ("ACME", "Acme Corporation", "NYSE", "Industrials",
     "42.15", 50000, "41.80", "42.50", "41.25", True),
    ("NVDA", "NVIDIA Corporation", "NASDAQ", "Technology",
     "175.10", 25000, "172.10", "176.25", "171.90", True),
    ("AMD", "Advanced Micro Devices", "NASDAQ", "Technology",
     "18.30", 35000, "18.10", "18.55", "17.95", True),
    ("SPCX", "Space Exploration Corp", "NASDAQ", "Aerospace",
     "72.40", 22000, "71.90", "73.10", "71.20", True),
    ("AAPL", "Apple Inc.", "NASDAQ", "Technology",
     "225.00", 40000, "223.10", "226.40", "222.75", True),
    ("MSFT", "Microsoft Corporation", "NASDAQ", "Technology",
     "510.00", 30000, "506.20", "512.80", "505.10", True),
    ("KOLA", "Kola Beverage Co.", "NYSE", "Consumer Staples",
     "61.40", 28000, "61.00", "61.95", "60.70", True),
    ("GRNE", "Green Energy Partners", "NYSE", "Energy",
     "9.85", 60000, "9.70", "10.05", "9.62", True),
    # SYS-101: inactive, should get no prices
    ("OLDC", "Old Colony Mills", "NYSE", "Industrials",
     "3.10", 10000, "3.10", "3.10", "3.10", False),
)

EXTRA_CUSTOMERS = (
    ("Avery Johnson", "ajohnson"),
    ("Blake Martinez", "bmartinez"),
    ("Casey Nguyen", "cnguyen"),
    ("Dana Patel", "dpatel"),
    ("Emerson Clark", "eclark"),
    ("Finley Brooks", "fbrooks"),
    ("Harper Reyes", "hreyes"),
    ("Jordan Kim", "jkim"),
    ("Morgan Diaz", "mdiaz"),
    ("Quinn Foster", "qfoster"),
    ("Riley Chen", "rchen"),
    ("Taylor Evans", "tevans"),
)

CENT = Decimal("0.01")


def _money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def _create_customer(full_name, username, is_admin=False):
    customer = Customer(
        full_name=full_name,
        username=username,
        email=f"{username}@example.com",
        password_hash=generate_password_hash(SEED_PASSWORD),
        is_admin=is_admin,
    )
    db.session.add(customer)
    db.session.flush()

    account = CashAccount(
        customer_id=customer.id,
        balance=Decimal("0.00"),
    )
    db.session.add(account)
    db.session.flush()

    return account


def _apply_cash(account, transaction_type, amount, when, **stock_fields):
    account.balance = account.balance + amount

    db.session.add(Transaction(
        customer_id=account.customer_id,
        cash_account_id=account.id,
        transaction_type=transaction_type,
        amount=amount,
        resulting_cash_balance=account.balance,
        transaction_date=when,
        **stock_fields
    ))


def _deposit(account, amount, when):
    _apply_cash(account, DEPOSIT, _money(amount), when)


def _withdraw(account, amount, when):
    _apply_cash(account, WITHDRAWAL, -_money(amount), when)


def _holding(holdings, account, stock):
    key = (account.customer_id, stock.id)

    if key not in holdings:
        holding = PortfolioHolding(
            customer_id=account.customer_id,
            stock_id=stock.id,
            share_quantity=0,
        )
        db.session.add(holding)
        holdings[key] = holding

    return holdings[key]


def _execute(holdings, account, order_type, stock, quantity, price, when):
    price = _money(price)

    order = Order(
        customer_id=account.customer_id,
        stock_id=stock.id,
        order_type=order_type,
        quantity=quantity,
        status=EXECUTED,
        submitted_at=when - timedelta(minutes=1),
        executed_at=when,
        execution_price=price,
    )
    db.session.add(order)
    db.session.flush()

    holding = _holding(holdings, account, stock)
    total = price * quantity

    if order_type == BUY:
        holding.share_quantity += quantity
        amount, transaction_type = -total, BUY
    else:
        holding.share_quantity -= quantity
        amount, transaction_type = total, SELL

    _apply_cash(
        account,
        transaction_type,
        amount,
        when,
        order_id=order.id,
        stock_id=stock.id,
        share_quantity=quantity,
        price_per_share=price,
    )


def _open_order(account, order_type, stock, quantity, when, status,
                rejection_reason=None):
    db.session.add(Order(
        customer_id=account.customer_id,
        stock_id=stock.id,
        order_type=order_type,
        quantity=quantity,
        status=status,
        submitted_at=when,
        rejection_reason=rejection_reason,
    ))


def _history_times():
    times = []

    for day in HISTORY_DAYS:
        for hour in range(9, 16):
            times.append(datetime.combine(day, time(hour, 30)))
        times.append(datetime.combine(day, MARKET_CLOSE))

    return times


def _price_walk(rng, end_price, points):
    prices = [_money(end_price)]

    for _ in range(points - 1):
        move = Decimal(rng.randint(-150, 150)) / Decimal("10000")
        prices.append(max(_money(prices[-1] / (1 + move)), CENT))

    return list(reversed(prices))


def _seed_market(rng):
    # Paused so everyone sees the same simulated time.
    db.session.add(MarketClock(
        id=CLOCK_ID,
        simulated_anchor=SIMULATED_NOW,
        real_anchor=utc_now(),
        is_running=False,
        speed_multiplier=Decimal("1.00"),
    ))

    db.session.add(MarketHours(
        opening_time=MARKET_OPEN,
        closing_time=MARKET_CLOSE,
    ))

    for simulated_date, is_holiday in HOLIDAYS.items():
        db.session.add(MarketSchedule(
            simulated_date=simulated_date,
            is_holiday=is_holiday,
        ))

    times = _history_times()
    stocks = {}
    history = {}

    for (ticker, company, exchange, sector, current, volume,
         open_, high, low, active) in STOCKS:
        walk = _price_walk(rng, current, len(times))

        stock = Stock(
            ticker=ticker,
            company_name=company,
            exchange=exchange,
            sector=sector,
            initial_price=walk[0],
            current_price=_money(current),
            open_price=_money(open_),
            high_price=_money(high),
            low_price=_money(low),
            volume=volume,
            is_active=active,
        )
        db.session.add(stock)
        db.session.flush()

        for when, price in zip(times, walk):
            db.session.add(PriceHistory(
                stock_id=stock.id,
                simulated_datetime=when,
                price=price,
                volume=volume,
            ))

        stocks[ticker] = stock
        history[ticker] = list(zip(times, walk))

    return stocks, history


# Matches SAD Wireframe 4 (history) and Wireframe 7 (pending orders)
def _seed_demo(holdings, stocks):
    demo = _create_customer("Demo Customer", "demo")
    acme, nvda = stocks["ACME"], stocks["NVDA"]

    _deposit(demo, "2500.00", datetime(2026, 9, 12, 10, 0))
    _execute(holdings, demo, BUY, acme, 10, "42.15",
             datetime(2026, 9, 12, 10, 15))
    _execute(holdings, demo, SELL, acme, 5, "43.80",
             datetime(2026, 9, 13, 11, 0))
    _withdraw(demo, "300.00", datetime(2026, 9, 13, 14, 0))

    _open_order(demo, BUY, nvda, 2,
                datetime(2026, 9, 13, 15, 0), CANCELLED)
    _open_order(demo, BUY, acme, 10,
                datetime(2026, 9, 13, 16, 30), PENDING)
    _open_order(demo, SELL, acme, 5,
                datetime(2026, 9, 13, 16, 31), PENDING)


def _seed_extra_customer(rng, full_name, username, stocks, history, holdings):
    account = _create_customer(full_name, username)
    tradable = [s for s in stocks.values() if s.is_active]
    by_id = {s.id: s for s in stocks.values()}
    times = _history_times()

    _deposit(account, rng.randrange(50, 501) * 100, times[0])

    picks = rng.sample(tradable, k=rng.randint(1, 3))
    buy_points = sorted(rng.sample(range(1, 16), k=len(picks)))

    for stock, point in zip(picks, buy_points):
        when, price = history[stock.ticker][point]
        quantity = rng.randint(5, 60)

        while quantity > 0 and price * quantity > account.balance:
            quantity //= 2

        if quantity > 0:
            _execute(holdings, account, BUY, stock, quantity, price, when)

    held = [
        h for (customer_id, _), h in holdings.items()
        if customer_id == account.customer_id and h.share_quantity > 1
    ]

    if held and rng.random() < 0.5:
        holding = rng.choice(held)
        stock = by_id[holding.stock_id]
        when, price = history[stock.ticker][rng.randint(16, 22)]
        _execute(holdings, account, SELL, stock,
                 holding.share_quantity // 2, price, when)

    if rng.random() < 0.3:
        amount = (account.balance / 10).quantize(Decimal("10"))
        if amount > 0:
            _withdraw(account, amount, times[-1] + timedelta(minutes=5))

    if rng.random() < 0.4:
        _open_order(account, BUY, rng.choice(tradable),
                    rng.randint(1, 20), times[-1] + timedelta(minutes=30),
                    PENDING)

    return account


def seed_data():
    rng = random.Random(401)
    holdings = {}

    stocks, history = _seed_market(rng)

    _create_customer("Site Administrator", "admin", is_admin=True)
    _seed_demo(holdings, stocks)
    # CUS-311: no transactions
    _create_customer("New Customer", "newcustomer")

    extras = [
        _seed_extra_customer(rng, full_name, username, stocks, history,
                             holdings)
        for full_name, username in EXTRA_CUSTOMERS
    ]

    # CUS-406
    _open_order(extras[0], BUY, stocks["MSFT"], 500,
                datetime(2026, 9, 10, 16, 30), REJECTED,
                rejection_reason="Insufficient cash at execution.")

    db.session.commit()


def clear_data():
    models = (
        Transaction,
        Order,
        PortfolioHolding,
        CashAccount,
        Customer,
        PriceHistory,
        Stock,
        MarketSchedule,
        MarketHours,
        MarketClock,
    )

    if db.engine.dialect.name == "postgresql":
        # Restart ids so a reset gives the same ids every time.
        tables = ", ".join(model.__tablename__ for model in models)
        db.session.execute(
            db.text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE")
        )
    else:
        for model in models:
            db.session.query(model).delete()

    db.session.commit()


def _has_data():
    return (
        db.session.query(Stock.id).first() is not None
        or db.session.query(Customer.id).first() is not None
        or db.session.get(MarketClock, CLOCK_ID) is not None
    )


@click.command("seed")
@click.option(
    "--reset",
    is_flag=True,
    help="Delete all existing rows first, then seed."
)
@click.option(
    "--yes",
    is_flag=True,
    help="Skip the confirmation prompt when using --reset."
)
@with_appcontext
def seed_command(reset, yes):
    """Load fake development data."""
    target = db.engine.url.render_as_string(hide_password=True)

    if reset:
        if not yes:
            click.confirm(
                f"This deletes ALL rows in {target}. Continue?",
                abort=True
            )
        clear_data()
    elif _has_data():
        raise click.ClickException(
            "Database already has data. "
            "Run `flask seed --reset` to wipe it and seed again."
        )

    seed_data()

    click.echo(f"Seeded {target}")
    click.echo(
        f"  {Customer.query.count()} customers, "
        f"{Stock.query.count()} stocks, "
        f"{Order.query.count()} orders, "
        f"{Transaction.query.count()} transactions, "
        f"{PriceHistory.query.count()} price points"
    )
    click.echo(f"  Logins: admin / demo / newcustomer, password {SEED_PASSWORD}")
