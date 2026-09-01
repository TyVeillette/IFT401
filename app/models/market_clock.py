from datetime import datetime, timezone

from app.extensions import db


class MarketClock(db.Model):
    __tablename__ = "market_clock"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    simulated_anchor = db.Column(
        db.DateTime,
        nullable=False
    )

    real_anchor = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    is_running = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    speed_multiplier = db.Column(
        db.Numeric(8, 2),
        nullable=False,
        default=1.00
    )

    def __repr__(self):
        return (
            f"<MarketClock simulated_anchor={self.simulated_anchor} "
            f"running={self.is_running}>"
        )