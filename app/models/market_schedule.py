from app.extensions import db


# ADM-301 to ADM-308. The current simulated date (ADM-302) is in market_clock.
class MarketSchedule(db.Model):
    __tablename__ = "market_schedule"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # ADM-303: day of week comes from this date
    simulated_date = db.Column(
        db.Date,
        unique=True,
        nullable=False
    )

    # ADM-307, ADM-308
    is_holiday = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    def __repr__(self):
        return (
            f"<MarketSchedule {self.simulated_date} "
            f"holiday={self.is_holiday}>"
        )
