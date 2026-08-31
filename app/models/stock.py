from app.extensions import db


class Stock(db.Model):
    __tablename__ = "stocks"

    id = db.Column(db.Integer, primary_key=True)

    company_name = db.Column(
        db.String(150),
        nullable=False
    )

    ticker = db.Column(
        db.String(10),
        unique=True,
        nullable=False,
        index=True
    )

    exchange = db.Column(
        db.String(20),
        nullable=True
    )

    sector = db.Column(
        db.String(100),
        nullable=True
    )

    initial_price = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    current_price = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    open_price = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    high_price = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    low_price = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    volume = db.Column(
        db.BigInteger,
        nullable=False,
        default=0
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    def __repr__(self):
        return f"<Stock {self.ticker}>"