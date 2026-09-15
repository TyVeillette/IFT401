from app.extensions import db


# ADM-201 to ADM-207, CUS-420
class MarketHours(db.Model):
    __tablename__ = "market_hours"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    opening_time = db.Column(
        db.Time,
        nullable=False
    )

    closing_time = db.Column(
        db.Time,
        nullable=False
    )

    __table_args__ = (
        # ADM-204
        db.CheckConstraint(
            "opening_time < closing_time",
            name="ck_market_hours_open_before_close"
        ),
    )

    def __repr__(self):
        return (
            f"<MarketHours {self.opening_time}-{self.closing_time}>"
        )
