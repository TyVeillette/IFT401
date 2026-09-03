class CashAccount(db.Model):

    __tablename__ = "cash_accounts"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customers.id"),
        nullable=False
    )

    balance = db.Column(
        db.Numeric(10, 2),
        default=0.00
    )
