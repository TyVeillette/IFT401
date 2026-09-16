from app.extensions import db


class PortfolioHolding(db.Model):
    __tablename__ = "portfolio_holdings"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customers.id"),
        nullable=False
    )

    stock_id = db.Column(
        db.Integer,
        db.ForeignKey("stocks.id"),
        nullable=False,
        index=True
    )

    # CUS-408, CUS-417, CUS-604
    share_quantity = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    __table_args__ = (
        # CUS-602: one row per stock owned
        db.UniqueConstraint(
            "customer_id",
            "stock_id",
            name="uq_portfolio_holdings_customer_stock"
        ),
        # CUS-412, CUS-416: can't sell more than owned
        db.CheckConstraint(
            "share_quantity >= 0",
            name="ck_portfolio_holdings_quantity_non_negative"
        ),
    )

    def __repr__(self):
        return (
            f"<PortfolioHolding customer={self.customer_id} "
            f"stock={self.stock_id} qty={self.share_quantity}>"
        )
