from flask import Flask

from app.extensions import db, migrate


def create_app():
    app = Flask(__name__)

    app.config.from_object("config.Config")

    db.init_app(app)
    migrate.init_app(app, db)

    from app import models
    from app.seed import seed_command

    app.cli.add_command(seed_command)

    @app.route("/health")
    def health():
        return {
            "status": "ok",
            "application": "IFT401 Stock Trading System"
        }, 200

    return app