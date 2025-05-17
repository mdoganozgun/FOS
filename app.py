from flask import Flask, render_template
from routes.auth_routes import auth_bp
from routes.customer_routes import customer_bp
from routes.manager_routes import manager_bp

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Güçlü bir key ile değiştir

# Blueprint'leri kaydet
app.register_blueprint(auth_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(manager_bp)

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)