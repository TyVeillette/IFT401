import click

from app.services.market_tick_service import run_market_tick


def register_market_commands(app):
    @app.cli.command("market-tick")
    def market_tick_command():
        """Run one simulated market tick."""

        result = run_market_tick()

        if not result["market_open"]:
            click.echo("Market closed. No tick executed.")
            return

        snapshot_count = len(
            result["price_snapshots"]
        )

        order_count = len(
            result["processed_orders"]
        )

        click.echo(
            f"Market tick complete: "
            f"{snapshot_count} stock prices updated, "
            f"{order_count} orders processed."
        )