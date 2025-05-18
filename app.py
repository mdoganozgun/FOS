from flask import Flask, render_template, session, redirect
from db_config import get_connection
from routes.auth_routes import auth_bp
from routes.customer_routes import customer_bp
from routes.manager_routes import manager_bp
from routes.address_api import address_api

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Güçlü bir key ile değiştir

# Blueprint'leri kaydet
app.register_blueprint(auth_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(manager_bp)

app.register_blueprint(address_api)

@app.route("/")
def index():
    if "user_id" in session:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT userID FROM Customer WHERE userID = %s", (session["user_id"],))
        if cursor.fetchone():
            conn.close()
            return redirect("/customer/dashboard")
        else:
            conn.close()
            return redirect("/manager/dashboard")
    else:
        return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)