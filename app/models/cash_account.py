from decimal import Decimal

from app.extensions import db


class CashAccount(db.Model):
    __tablename__ = "cash_accounts"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # CUS-106: one cash account per customer
    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customers.id"),
        unique=True,
        nullable=False
    )

    balance = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00")
    )

    __table_args__ = (
        # CUS-211, CUS-406: balance can't go negative
        db.CheckConstraint(
            "balance >= 0",
            name="ck_cash_accounts_balance_non_negative"
        ),
    )

    def __repr__(self):
        return (
            f"<CashAccount customer={self.customer_id} "
            f"balance={self.balance}>"
        )
