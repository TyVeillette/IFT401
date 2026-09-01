from app.extensions import db


class PriceHistory(db.Model):
    __tablename__ = "price_history"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    stock_id = db.Column(
        db.Integer,
        db.ForeignKey("stocks.id"),
        nullable=False,
        index=True
    )

    simulated_datetime = db.Column(
        db.DateTime,
        nullable=False,
        index=True
    )

    price = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    volume = db.Column(
        db.BigInteger,
        nullable=False,
        default=0
    )

    __table_args__ = (
        db.Index(
            "ix_price_history_stock_datetime",
            "stock_id",
            "simulated_datetime"
        ),
    )

    def __repr__(self):
        return (
            f"<PriceHistory stock={self.stock_id} "
            f"time={self.simulated_datetime} "
            f"price={self.price}>"
        )