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
