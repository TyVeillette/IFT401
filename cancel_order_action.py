@app.route(
    "/cancel-order/<int:order_id>",
    methods=["POST"]
)
@login_required
def cancel_order(order_id):

    order = Order.query.filter_by(
        id=order_id,
        customer_id=current_user.id
    ).first_or_404()

    # Must be pending
    if order.status != "Pending":

        flash(
            "Only pending orders can be cancelled.",
            "danger"
        )

        return redirect(
            url_for("cancel_order_page")
        )

    order.status = "Cancelled"

    db.session.commit()

    flash(
        f"Order #{order.id} cancelled successfully.",
        "success"
    )

    return redirect(
        url_for("cancel_order_page")
    )
