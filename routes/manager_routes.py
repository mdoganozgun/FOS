from flask import Blueprint, render_template, request, redirect, session
from db_config import get_connection
from datetime import datetime, timedelta

manager_bp = Blueprint("manager", __name__)

@manager_bp.route("/manager/dashboard", methods=["GET", "POST"])
def manager_dashboard():
    if "user_id" not in session:
        return "Unauthorized", 401

    conn = get_connection()
    cursor = conn.cursor()

    # Menü ekleme işlemi
    if request.method == "POST":
        restaurant_id = request.form["restaurant_id"]
        item_name = request.form["item_name"]
        price = request.form["price"]
        desc = request.form["description"]
        cursor.execute("""
            INSERT INTO MenuItem (restaurantID, itemName, price, description)
            VALUES (%s, %s, %s, %s)
        """, (restaurant_id, item_name, price, desc))
        conn.commit()

    cursor.execute("SELECT restaurantID, restaurantName, city FROM Restaurant WHERE managerID = %s", (session["user_id"],))
    restaurants = cursor.fetchall()

    restaurant_menus = {}
    for r in restaurants:
        rid = r[0]
        cursor.execute("SELECT itemName, price, description FROM MenuItem WHERE restaurantID = %s", (rid,))
        restaurant_menus[rid] = cursor.fetchall()

    one_month_ago = datetime.now() - timedelta(days=30)
    cursor.execute("""
        SELECT R.restaurantName, COUNT(O.orderID), SUM(M.price * CI.quantity)
        FROM Restaurant R
        JOIN Cart C ON R.restaurantID = C.restaurantID
        JOIN `Order` O ON C.cartID = O.cartID
        JOIN CartItem CI ON C.cartID = CI.cartID
        JOIN MenuItem M ON CI.itemID = M.itemID
        WHERE R.managerID = %s AND O.orderTimestamp >= %s
        GROUP BY R.restaurantName
    """, (session["user_id"], one_month_ago))
    stats = cursor.fetchall()

    cursor.execute("""
        SELECT C.cartID, C.customerID
        FROM Cart C
        JOIN Restaurant R ON C.restaurantID = R.restaurantID
        WHERE R.managerID = %s AND C.status = 'SENT'
    """, (session["user_id"],))
    pending_orders = cursor.fetchall()

    conn.close()
    return render_template("manager_dashboard.html", username=session["username"],
                           restaurants=restaurants, restaurant_menus=restaurant_menus,
                           stats=stats, pending_orders=pending_orders)

@manager_bp.route("/manager/accept/<int:cart_id>", methods=["POST"])
def accept_order(cart_id):
    if "user_id" not in session:
        return "Unauthorized", 401

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Cart
        SET status = 'ACCEPTED', acceptedTimestamp = NOW()
        WHERE cartID = %s AND restaurantID IN (
            SELECT restaurantID FROM Restaurant WHERE managerID = %s
        )
    """, (cart_id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect("/manager/dashboard")