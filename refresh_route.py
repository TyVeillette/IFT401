@app.route("/market-board/refresh")
@login_required
def refresh_market_board():

    return redirect(
        url_for("market_board")
    )
