class Stock(db.Model):

    __tablename__ = "stocks"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    ticker = db.Column(
        db.String(10),
        unique=True,
        nullable=False
    )

    stock_name = db.Column(
        db.String(100),
        nullable=False
    )

    current_price = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    volume = db.Column(
        db.Integer,
        nullable=False
    )

    opening_price = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    daily_high = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    daily_low = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    market_cap = db.Column(
        db.Numeric(15, 2),
        nullable=False
    )
