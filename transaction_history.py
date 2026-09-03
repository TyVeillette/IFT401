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

    transaction_type = db.Column(
        db.String(25),
        nullable=False
    )

    amount = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    resulting_balance = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    transaction_date = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )
