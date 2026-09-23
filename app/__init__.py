from flask import Flask

from app.extensions import db, migrate



def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    migrate.init_app(app, db)

    from app.routes.order_routes import order_bp
    from app.routes.admin_market_routes import admin_market_bp
    from app.routes.cash_account_routes import cash_account_bp
    from app.routes.portfolio_routes import portfolio_bp
    from app.routes.market_routes import market_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.page_routes import page_bp
    from app.commands.market_commands import register_market_commands

    app.register_blueprint(order_bp)
    app.register_blueprint(admin_market_bp)
    app.register_blueprint(cash_account_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(page_bp)

    register_market_commands(app)

    @app.route("/health")
    def health():
        return {
            "status": "ok",
            "application": "IFT401 Stock Trading System",
        }, 200

    return app