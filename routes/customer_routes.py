from flask import Blueprint, render_template, session, request, redirect
from db_config import get_connection

customer_bp = Blueprint("customer", __name__)

@customer_bp.route("/customer/dashboard", methods=["GET", "POST"])
def customer_dashboard():
    if "user_id" not in session:
        return "Unauthorized", 401

    conn = get_connection()
    cursor = conn.cursor()

    # Ürün sepete ekleme
    if request.method == "POST":
        item_id = request.form["item_id"]
        restaurant_id = request.form["restaurant_id"]
        quantity = int(request.form["quantity"])

        cursor.execute("SELECT cartID FROM Cart WHERE customerID = %s AND status = 'BUILDING'", (session["user_id"],))
        cart = cursor.fetchone()
        if not cart:
            cursor.execute("INSERT INTO Cart (customerID, restaurantID) VALUES (%s, %s)", (session["user_id"], restaurant_id))
            conn.commit()
            cart_id = cursor.lastrowid
        else:
            cart_id = cart[0]

        cursor.execute("""
            INSERT INTO CartItem (cartID, itemID, quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = quantity + %s
        """, (cart_id, item_id, quantity, quantity))
        conn.commit()

    # Restoranlar ve menüler
    cursor.execute("SELECT city FROM UserAddress WHERE userID = %s LIMIT 1", (session["user_id"],))
    result = cursor.fetchone()
    city = result[0] if result else None

    keyword = request.args.get("keyword")
    if keyword:
        cursor.execute("""
            SELECT DISTINCT R.restaurantID, R.restaurantName, R.city
            FROM Restaurant R
            JOIN tagged_with T ON R.restaurantID = T.restaurantID
            JOIN Keyword K ON T.keywordID = K.keywordID
            WHERE K.keywordName LIKE %s AND R.city = %s
        """, ('%' + keyword + '%', city))
    else:
        cursor.execute("SELECT restaurantID, restaurantName, city FROM Restaurant WHERE city = %s", (city,))
    restaurants = cursor.fetchall()

    menus = {}
    for r in restaurants:
        cursor.execute("SELECT itemID, itemName, price FROM MenuItem WHERE restaurantID = %s", (r[0],))
        menus[r[0]] = cursor.fetchall()

    # Değerlendirme yapılmamış siparişler
    cursor.execute("""
        SELECT O.orderID
        FROM `Order` O
        JOIN Cart C ON O.cartID = C.cartID
        WHERE C.customerID = %s AND C.status = 'ACCEPTED'
        AND NOT EXISTS (
            SELECT 1 FROM Rating R WHERE R.orderID = O.orderID
        )
    """, (session["user_id"],))
    unrated_orders = cursor.fetchall()

    conn.close()

    return render_template("customer_dashboard.html",
                           username=session["username"],
                           restaurants=restaurants,
                           menus=menus,
                           unrated_orders=unrated_orders)
@customer_bp.route("/customer/checkout", methods=["POST"])
def customer_checkout():
    if "user_id" not in session:
        return "Unauthorized", 401

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT cartID FROM Cart WHERE customerID = %s AND status = 'BUILDING'", (session["user_id"],))
    cart = cursor.fetchone()
    if not cart:
        conn.close()
        return "No active cart to checkout."

    cart_id = cart[0]
    cursor.execute("""
        UPDATE Cart
        SET status = 'SENT', checkedOutTimestamp = NOW()
        WHERE cartID = %s
    """, (cart_id,))
    cursor.execute("INSERT INTO `Order` (cartID) VALUES (%s)", (cart_id,))
    conn.commit()
    conn.close()
    return "Order sent successfully!"

@customer_bp.route("/customer/rate/<int:order_id>", methods=["GET", "POST"])
def rate_order(order_id):
    if "user_id" not in session:
        return "Unauthorized", 401

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        rating = int(request.form["rating"])
        comment = request.form["comment"]
        cursor.execute("""
            SELECT C.restaurantID FROM Cart C
            JOIN `Order` O ON O.cartID = C.cartID
            WHERE O.orderID = %s AND C.customerID = %s
        """, (order_id, session["user_id"]))
        result = cursor.fetchone()
        if result:
            restaurant_id = result[0]
            cursor.execute("""
                INSERT INTO Rating (orderID, customerID, restaurantID, ratingValue, comment)
                VALUES (%s, %s, %s, %s, %s)
            """, (order_id, session["user_id"], restaurant_id, rating, comment))
            conn.commit()
            conn.close()
            return "Thanks for your rating!"
        conn.close()
        return "Order not found or not yours."

    return render_template("rate_order.html", order_id=order_id)
