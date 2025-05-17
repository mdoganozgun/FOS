from flask import Blueprint, render_template, session

manager_bp = Blueprint("manager", __name__)

@manager_bp.route("/manager/dashboard")
def manager_dashboard():
    if "user_id" not in session:
        return "Unauthorized", 401
    return render_template("manager_dashboard.html", username=session["username"])