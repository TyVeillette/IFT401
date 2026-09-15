from datetime import datetime, timezone

from app.extensions import db


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customers.id"),
        nullable=False
    )

    cash_account_id = db.Column(
        db.Integer,
        db.ForeignKey("cash_accounts.id"),
        nullable=False,
        index=True
    )

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id"),
        nullable=True,
        index=True
    )

    # CUS-307: buy and sell only
    stock_id = db.Column(
        db.Integer,
        db.ForeignKey("stocks.id"),
        nullable=True,
        index=True
    )

    # CUS-304
    transaction_type = db.Column(
        db.String(10),
        nullable=False
    )

    # CUS-306: negative for withdrawals and buys
    amount = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    # CUS-305
    resulting_cash_balance = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    # CUS-308
    share_quantity = db.Column(
        db.Integer,
        nullable=True
    )

    # CUS-309
    price_per_share = db.Column(
        db.Numeric(12, 2),
        nullable=True
    )

    # CUS-303: simulated time from get_simulated_datetime()
    transaction_date = db.Column(
        db.DateTime,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    __table_args__ = (
        db.CheckConstraint(
            "transaction_type IN ('Deposit', 'Withdrawal', 'Buy', 'Sell')",
            name="ck_transactions_type"
        ),
        db.CheckConstraint(
            "amount <> 0",
            name="ck_transactions_amount_non_zero"
        ),
        db.CheckConstraint(
            "resulting_cash_balance >= 0",
            name="ck_transactions_resulting_balance_non_negative"
        ),
        db.CheckConstraint(
            "share_quantity IS NULL OR share_quantity > 0",
            name="ck_transactions_share_quantity_positive"
        ),
        # CUS-302, CUS-310
        db.Index(
            "ix_transactions_customer_date",
            "customer_id",
            "transaction_date"
        ),
    )

    def __repr__(self):
        return (
            f"<Transaction {self.id} {self.transaction_type} "
            f"amount={self.amount}>"
        )
