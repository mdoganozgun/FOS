from flask import Blueprint, render_template, request, redirect, session
from db_config import get_connection

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT userID, userName FROM User WHERE userName = %s AND password = %s", (username, password))
        user = cursor.fetchone()

        if user:
            session["user_id"] = user[0]
            session["username"] = user[1]

            cursor.execute("SELECT userID FROM Customer WHERE userID = %s", (user[0],))
            if cursor.fetchone():
                conn.close()
                return redirect("/customer/dashboard")
            else:
                conn.close()
                return redirect("/manager/dashboard")
        else:
            conn.close()
            return "Login failed"

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        role = request.form["role"]  # 'customer' veya 'manager'

        conn = get_connection()
        cursor = conn.cursor()

        # Kullanıcıyı User tablosuna ekle
        cursor.execute(
            "INSERT INTO User (userName, password, email) VALUES (%s, %s, %s)",
            (username, password, email)
        )
        user_id = cursor.lastrowid

        # Alt tipe göre Customer ya da Manager tablosuna ekle
        if role == "customer":
            cursor.execute("INSERT INTO Customer (userID) VALUES (%s)", (user_id,))
        elif role == "manager":
            cursor.execute("INSERT INTO Manager (userID) VALUES (%s)", (user_id,))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")