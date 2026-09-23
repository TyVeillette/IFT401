from flask import Flask, render_template, request

app = Flask(__name__)

stocks = {}
audit_log = []


@app.route("/", methods=["GET", "POST"])
def create_stock():
    error = None
    success = False
    ticker = ""

    if request.method == "POST":
        ticker = request.form.get("ticker", "").strip().upper()
        name = request.form.get("name", "").strip()
        price = request.form.get("price", "").strip()
        volume = request.form.get("volume", "").strip()

        # Check for an existing stock ticker
        if ticker in stocks:
            error = "Ticker already exists."

        else:
            try:
                price_value = float(price)
                volume_value = int(volume)

                if (
                    not ticker
                    or not name
                    or price_value <= 0
                    or volume_value < 0
                ):
                    raise ValueError

            except ValueError:
                error = "Please enter valid stock information."

            else:
                stocks[ticker] = {
                    "name": name,
                    "price": price_value,
                    "volume": volume_value
                }

                audit_log.append(
                    f"Created {ticker}: {name}, "
                    f"${price_value:.2f}, volume {volume_value}"
                )

                success = True
                ticker = ""

    return render_template(
        "index.html",
        error=error,
        success=success,
        ticker=ticker
    )


if __name__ == "__main__":
    app.run(debug=True)
