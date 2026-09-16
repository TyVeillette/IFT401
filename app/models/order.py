from app.extensions import db


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customers.id"),
        nullable=False,
        index=True
    )

    stock_id = db.Column(
        db.Integer,
        db.ForeignKey("stocks.id"),
        nullable=False,
        index=True
    )

    # CUS-401, CUS-410
    order_type = db.Column(
        db.String(4),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    # CUS-403, CUS-413, CUS-501 to CUS-506
    status = db.Column(
        db.String(10),
        nullable=False,
        default="Pending",
        index=True
    )

    # Simulated time from get_simulated_datetime()
    submitted_at = db.Column(
        db.DateTime,
        nullable=False
    )

    executed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    # CUS-404, CUS-414: market price at execution
    execution_price = db.Column(
        db.Numeric(12, 2),
        nullable=True
    )

    # CUS-406, CUS-416
    rejection_reason = db.Column(
        db.String(255),
        nullable=True
    )

    __table_args__ = (
        db.CheckConstraint(
            "order_type IN ('Buy', 'Sell')",
            name="ck_orders_order_type"
        ),
        db.CheckConstraint(
            "status IN ('Pending', 'Executed', 'Cancelled', 'Rejected')",
            name="ck_orders_status"
        ),
        # CUS-402, CUS-411
        db.CheckConstraint(
            "quantity > 0",
            name="ck_orders_quantity_positive"
        ),
    )

    def __repr__(self):
        return (
            f"<Order {self.id} {self.order_type} "
            f"qty={self.quantity} status={self.status}>"
        )
