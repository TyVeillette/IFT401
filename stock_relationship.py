class Order(db.Model):

    __tablename__ = "orders"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    stock_id = db.Column(
        db.Integer,
        db.ForeignKey("stocks.id")
    )

    stock = db.relationship(
        "Stock",
        backref="orders"
    )
