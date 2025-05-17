from flask import Blueprint, render_template, session

customer_bp = Blueprint("customer", __name__)

@customer_bp.route("/customer/dashboard")
def customer_dashboard():
    if "user_id" not in session:
        return "Unauthorized", 401
    return render_template("customer_dashboard.html", username=session["username"])