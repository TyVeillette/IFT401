from functools import wraps

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.extensions import db
from app.models.order import Order
from app.models.portfolio_holding import PortfolioHolding
from app.models.stock import Stock
from app.models.transaction import Transaction
from app.routes.admin_market_routes import parse_date, parse_time
from app.services.admin_stock_service import create_stock
from app.services.auth_service import (
    authenticate,
    get_current_customer,
)
from app.services.cash_account_service import (
    deposit,
    get_cash_account,
    withdraw,
)
from app.services.market_board_service import get_market_board
from app.services.market_clock_service import get_simulated_datetime
from app.services.market_schedule_service import (
    get_market_hours,
    get_market_schedule,
    set_market_holiday,
    set_market_hours,
)
from app.services.order_service import (
    cancel_order,
    create_buy_order,
    create_sell_order,
)
from app.services.portfolio_service import get_portfolio


# HTML pages for the browser. The JSON API in the other route
# files stays unchanged; both call the same services.
page_bp = Blueprint(
    "pages",
    __name__,
)


# The auth_service decorators return JSON 401/403 responses,
# so pages use their own versions that redirect to the login page.
def page_login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if get_current_customer() is None:
            flash("Please sign in to continue.", "warning")

            return redirect(
                url_for("pages.login", next=request.path)
            )

        return view_function(*args, **kwargs)

    return wrapped_view


def page_admin_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        customer = get_current_customer()

        if customer is None:
            flash("Please sign in to continue.", "warning")

            return redirect(
                url_for("pages.login", next=request.path)
            )

        if not customer.is_admin:
            flash("Administrator access required.", "danger")

            return redirect(url_for("pages.market_board"))

        return view_function(*args, **kwargs)

    return wrapped_view


@page_bp.app_context_processor
def inject_page_globals():
    try:
        simulated_datetime = get_simulated_datetime()
    except RuntimeError:
        simulated_datetime = None

    return {
        "current_customer": get_current_customer(),
        "simulated_datetime": simulated_datetime,
    }


def get_active_stock(ticker):
    stock = Stock.query.filter_by(
        ticker=ticker.upper(),
        is_active=True,
    ).first()

    if stock is None:
        flash(f"Stock {ticker.upper()} not found.", "danger")

    return stock


# ---------------------------------------------------------------------------
# Sign in
# ---------------------------------------------------------------------------

@page_bp.get("/")
def home():
    return redirect(url_for("pages.market_board"))


@page_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        customer = authenticate(username, password)

        if customer is None:
            flash("Invalid username or password.", "danger")

            return render_template(
                "login.html",
                username=username,
            ), 401

        session.clear()
        session["customer_id"] = customer.id

        next_path = request.args.get("next", "")

        # Only follow local paths so the login page can't redirect
        # to another site.
        if next_path.startswith("/") and not next_path.startswith("//"):
            return redirect(next_path)

        return redirect(url_for("pages.market_board"))

    return render_template("login.html")


@page_bp.post("/logout")
def logout():
    session.clear()
    flash("You have signed out.", "info")

    return redirect(url_for("pages.login"))


# ---------------------------------------------------------------------------
# Customer pages
# ---------------------------------------------------------------------------

@page_bp.get("/market-board")
@page_login_required
def market_board():
    board = get_market_board()

    return render_template(
        "market_board.html",
        stocks=board["stocks"],
        market_open=board["market_open"],
    )


@page_bp.get("/my-portfolio")
@page_login_required
def portfolio():
    customer = get_current_customer()

    try:
        portfolio = get_portfolio(customer.id)
    except ValueError as exc:
        flash(str(exc), "danger")

        return redirect(url_for("pages.market_board"))

    return render_template(
        "portfolio.html",
        portfolio=portfolio,
    )


@page_bp.route("/buy/<string:ticker>", methods=["GET", "POST"])
@page_login_required
def buy_stock(ticker):
    customer = get_current_customer()
    stock = get_active_stock(ticker)

    if stock is None:
        return redirect(url_for("pages.market_board"))

    if request.method == "POST":
        try:
            quantity = int(request.form.get("quantity", ""))

            create_buy_order(
                customer_id=customer.id,
                stock_id=stock.id,
                quantity=quantity,
            )

            flash(
                f"Buy order for {quantity} {stock.ticker} submitted. "
                "Pending execution.",
                "success",
            )

            return redirect(url_for("pages.pending_orders"))

        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template(
        "buy_stock.html",
        stock=stock,
        cash_account=get_cash_account(customer.id),
    )


@page_bp.route("/sell/<string:ticker>", methods=["GET", "POST"])
@page_login_required
def sell_stock(ticker):
    customer = get_current_customer()
    stock = get_active_stock(ticker)

    if stock is None:
        return redirect(url_for("pages.portfolio"))

    if request.method == "POST":
        try:
            quantity = int(request.form.get("quantity", ""))

            create_sell_order(
                customer_id=customer.id,
                stock_id=stock.id,
                quantity=quantity,
            )

            flash(
                f"Sell order for {quantity} {stock.ticker} submitted. "
                "Pending execution.",
                "success",
            )

            return redirect(url_for("pages.pending_orders"))

        except ValueError as exc:
            flash(str(exc), "danger")

    holding = PortfolioHolding.query.filter_by(
        customer_id=customer.id,
        stock_id=stock.id,
    ).first()

    return render_template(
        "sell_stock.html",
        stock=stock,
        available_shares=(
            holding.share_quantity
            if holding is not None
            else 0
        ),
    )


@page_bp.get("/pending-orders")
@page_login_required
def pending_orders():
    customer = get_current_customer()

    rows = (
        db.session.query(Order, Stock.ticker)
        .join(Stock, Order.stock_id == Stock.id)
        .filter(
            Order.customer_id == customer.id,
            Order.status == "Pending",
        )
        .order_by(
            Order.submitted_at.desc(),
            Order.id.desc(),
        )
        .all()
    )

    return render_template(
        "pending_orders.html",
        pending_orders=rows,
    )


@page_bp.post("/pending-orders/<int:order_id>/cancel")
@page_login_required
def cancel_pending_order(order_id):
    customer = get_current_customer()

    try:
        cancel_order(
            order_id=order_id,
            customer_id=customer.id,
        )

        flash(f"Order {order_id} cancelled.", "success")

    except ValueError as exc:
        flash(str(exc), "danger")

    return redirect(url_for("pages.pending_orders"))


@page_bp.route("/cash-account", methods=["GET", "POST"])
@page_login_required
def cash_account():
    customer = get_current_customer()

    if request.method == "POST":
        action = request.form.get("action")
        amount = request.form.get("amount", "")

        try:
            if action == "deposit":
                transaction = deposit(customer.id, amount)
                label = "Deposit"
            elif action == "withdraw":
                transaction = withdraw(customer.id, amount)
                label = "Withdrawal"
            else:
                raise ValueError("Choose deposit or withdraw.")

            flash(
                f"{label} confirmed. Updated cash balance: "
                f"${transaction.resulting_cash_balance:,.2f}",
                "success",
            )

            return redirect(url_for("pages.cash_account"))

        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template(
        "cash_account.html",
        cash_account=get_cash_account(customer.id),
    )


@page_bp.get("/transaction-history")
@page_login_required
def transaction_history():
    customer = get_current_customer()

    rows = (
        db.session.query(Transaction, Stock.ticker)
        .outerjoin(Stock, Transaction.stock_id == Stock.id)
        .filter(Transaction.customer_id == customer.id)
        .order_by(
            Transaction.transaction_date.desc(),
            Transaction.id.desc(),
        )
        .all()
    )

    return render_template(
        "transaction_history.html",
        transactions=rows,
    )


# ---------------------------------------------------------------------------
# Administrator pages
# ---------------------------------------------------------------------------

@page_bp.route("/admin/create-stock", methods=["GET", "POST"])
@page_admin_required
def admin_create_stock():
    form = {}

    if request.method == "POST":
        form = request.form

        try:
            stock = create_stock(
                company_name=form.get("company_name", ""),
                ticker=form.get("ticker", ""),
                initial_price=form.get("initial_price", ""),
                volume=form.get("volume", ""),
                exchange=form.get("exchange"),
                sector=form.get("sector"),
            )

            flash(
                f"{stock.ticker} successfully added to market board.",
                "success",
            )

            return redirect(url_for("pages.admin_create_stock"))

        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template(
        "admin/create_stock.html",
        form=form,
    )


@page_bp.route("/admin/market-hours", methods=["GET", "POST"])
@page_admin_required
def admin_market_hours():
    if request.method == "POST":
        try:
            set_market_hours(
                parse_time(request.form.get("opening_time")),
                parse_time(request.form.get("closing_time")),
            )

            flash("Market hours updated successfully.", "success")

            return redirect(url_for("pages.admin_market_hours"))

        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template(
        "admin/market_hours.html",
        market_hours=get_market_hours(),
    )


@page_bp.route("/admin/market-schedule", methods=["GET", "POST"])
@page_admin_required
def admin_market_schedule():
    if request.method == "POST":
        try:
            simulated_date = parse_date(
                request.form.get("simulated_date")
            )
            is_holiday = request.form.get("is_holiday") == "on"

            set_market_holiday(simulated_date, is_holiday)

            flash("Market schedule updated successfully.", "success")

            return redirect(
                url_for(
                    "pages.admin_market_schedule",
                    date=simulated_date.isoformat(),
                )
            )

        except ValueError as exc:
            flash(str(exc), "danger")

    try:
        selected_date = parse_date(request.args.get("date"))
    except ValueError:
        selected_date = get_simulated_datetime().date()

    schedule = get_market_schedule(selected_date)

    return render_template(
        "admin/market_schedule.html",
        selected_date=selected_date,
        is_holiday=(
            schedule is not None
            and schedule.is_holiday
        ),
    )
