from flask import Blueprint, render_template, session, request, redirect, flash
from db_config import get_connection
from datetime import datetime, timedelta


customer_bp = Blueprint("customer", __name__)

@customer_bp.route("/customer/cart/delete", methods=["POST"])
def delete_item():
    if "user_id" not in session:
        return "Unauthorized", 401

    item_name = request.form["item_name"]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT itemID FROM MenuItem WHERE itemName = %s", (item_name,))
    item = cursor.fetchone()
    if not item:
        conn.close()
        return redirect("/customer/dashboard")

    item_id = item[0]
    cursor.execute("SELECT cartID FROM Cart WHERE customerID = %s AND status = 'BUILDING'", (session["user_id"],))
    cart = cursor.fetchone()
    if not cart:
        conn.close()
        return redirect("/customer/dashboard")

    cart_id = cart[0]
    cursor.execute("DELETE FROM CartItem WHERE cartID = %s AND itemID = %s", (cart_id, item_id))
    conn.commit()
    conn.close()
    return redirect("/customer/dashboard")

@customer_bp.route("/customer/cart/increase", methods=["POST"])
def increase_quantity():
    if "user_id" not in session:
        return "Unauthorized", 401

    item_name = request.form["item_name"]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT itemID FROM MenuItem WHERE itemName = %s", (item_name,))
    item = cursor.fetchone()
    if not item:
        conn.close()
        return redirect("/customer/dashboard")

    item_id = item[0]
    cursor.execute("SELECT cartID FROM Cart WHERE customerID = %s AND status = 'BUILDING'", (session["user_id"],))
    cart = cursor.fetchone()
    if not cart:
        conn.close()
        return redirect("/customer/dashboard")

    cart_id = cart[0]
    cursor.execute("UPDATE CartItem SET quantity = quantity + 1 WHERE cartID = %s AND itemID = %s", (cart_id, item_id))
    conn.commit()
    conn.close()
    return redirect("/customer/dashboard")

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

        cursor.execute("SELECT cartID, restaurantID FROM Cart WHERE customerID = %s AND status = 'BUILDING'", (session["user_id"],))
        cart = cursor.fetchone()

        if cart:
            cart_id, cart_restaurant = cart
            try:
                if int(cart_restaurant) != int(restaurant_id):
                    conn.close()
                    flash("You can only add items from one restaurant at a time.")
                    return redirect("/customer/dashboard")
            except Exception as e:
                conn.close()
                flash("Invalid restaurant ID.")
                return redirect("/customer/dashboard")
        else:
            cursor.execute("INSERT INTO Cart (customerID, restaurantID) VALUES (%s, %s)", (session["user_id"], restaurant_id))
            conn.commit()
            cart_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO CartItem (cartID, itemID, quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = quantity + %s
        """, (cart_id, item_id, quantity, quantity))

        conn.commit()
        conn.close()
        return redirect("/customer/dashboard")

    # Get current cart items
    cursor.execute("""
        SELECT M.itemName, CI.quantity, M.price, (CI.quantity * M.price) AS total
        FROM CartItem CI
        JOIN Cart C ON CI.cartID = C.cartID
        JOIN MenuItem M ON CI.itemID = M.itemID
        WHERE C.customerID = %s AND C.status = 'BUILDING'
    """, (session["user_id"],))
    cart_items = cursor.fetchall()

    # Kullanıcının şehri
    cursor.execute("SELECT city FROM UserAddress WHERE userID = %s LIMIT 1", (session["user_id"],))
    result = cursor.fetchone()
    city = result[0] if result else None

    keyword = request.args.get("keyword")
    if keyword:
        cursor.execute("""
            SELECT R.restaurantID, R.restaurantName, R.city, COUNT(K.keywordName) AS match_score
            FROM Restaurant R
            JOIN tagged_with T ON R.restaurantID = T.restaurantID
            JOIN Keyword K ON T.keywordID = K.keywordID
            WHERE R.city = %s AND K.keywordName LIKE %s
            GROUP BY R.restaurantID
        """, (city, f"%{keyword}%"))
        raw_results = cursor.fetchall()

        restaurants = []
        for rid, name, city_name, match_score in raw_results:
            cursor.execute("""
                SELECT COUNT(*), AVG(ratingValue)
                FROM Rating
                WHERE restaurantID = %s
            """, (rid,))
            count, avg = cursor.fetchone()
            rating = round(avg, 2) if count >= 10 else "New"

            restaurants.append({
                "restaurantID": rid,
                "name": name,
                "city": city_name,
                "match_score": match_score,
                "rating": rating
            })

        def sort_key(r):
            score = r["match_score"]
            rating = r["rating"] if isinstance(r["rating"], float) else 0
            return (-score, -rating)

        restaurants.sort(key=sort_key)

    else:
        cursor.execute("SELECT restaurantID, restaurantName, city FROM Restaurant WHERE city = %s", (city,))
        raw_results = cursor.fetchall()

        restaurants = []
        for rid, name, city_name in raw_results:
            cursor.execute("""
                SELECT COUNT(*), AVG(ratingValue)
                FROM Rating
                WHERE restaurantID = %s
            """, (rid,))
            count, avg = cursor.fetchone()
            rating = round(avg, 2) if count >= 10 else "New"

            restaurants.append({
                "restaurantID": rid,
                "name": name,
                "city": city_name,
                "match_score": 0,
                "rating": rating
            })

        restaurants.sort(key=lambda r: -r["rating"] if isinstance(r["rating"], float) else 0)

    # Menüleri getir
    menus = {}
    for r in restaurants:
        cursor.execute("""
            SELECT
              M.itemID,
              M.itemName,
              CASE
                WHEN D.discountAmount IS NOT NULL
                 AND NOW() BETWEEN D.startTime AND D.endTime
                 THEN M.price - D.discountAmount
                WHEN D.discountRate IS NOT NULL
                 AND NOW() BETWEEN D.startTime AND D.endTime
                 THEN M.price * (1.0 - D.discountRate/100)
                ELSE M.price
              END AS effective_price,
              M.price AS base_price
            FROM MenuItem M
            LEFT JOIN defines_discount D
              ON D.itemID = M.itemID
              AND NOW() BETWEEN D.startTime AND D.endTime
            WHERE M.restaurantID = %s
        """, (r["restaurantID"],))
        menus[r["restaurantID"]] = cursor.fetchall()

    # Değerlendirilmemiş siparişler
    cursor.execute("""
        SELECT O.orderID, R.restaurantName, C.createdTimestamp
        FROM `Order` O
        JOIN Cart C ON O.cartID = C.cartID
        JOIN Restaurant R ON C.restaurantID = R.restaurantID
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
                           unrated_orders=unrated_orders,
                           cart_items=cart_items)
@customer_bp.route("/customer/checkout", methods=["POST"])
def customer_checkout():
    if "user_id" not in session:
        return "Unauthorized", 401

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT cartID FROM Cart WHERE customerID = %s AND status = 'BUILDING'", (session["user_id"],))
    cart_result = cursor.fetchall()
    if not cart_result:
        conn.close()
        flash("No active cart to checkout.")
        return redirect("/customer/dashboard")

    cart_id = cart_result[0][0]

    cursor.execute("""
        UPDATE Cart
        SET status = 'SENT', checkedOutTimestamp = NOW()
        WHERE cartID = %s
    """, (cart_id,))
    cursor.execute("INSERT INTO `Order` (cartID) VALUES (%s)", (cart_id,))

    # Create new empty cart shell
    # cursor.execute("INSERT INTO Cart (customerID, restaurantID) VALUES (%s, NULL)", (session["user_id"],))

    conn.commit()
    conn.close()

    flash("Order successfully sent!")
    return redirect("/customer/dashboard")

@customer_bp.route("/customer/rate/<int:order_id>", methods=["GET", "POST"])
def rate_order(order_id):
    if "user_id" not in session:
        return "Unauthorized", 401

    conn = get_connection()
    cursor = conn.cursor()

    # acceptedTimestamp üzerinden kontrol
    cursor.execute("""
        SELECT C.acceptedTimestamp, C.restaurantID
        FROM `Order` O
        JOIN Cart C ON O.cartID = C.cartID
        WHERE O.orderID = %s AND C.customerID = %s
    """, (order_id, session["user_id"]))
    result = cursor.fetchone()

    if not result:
        conn.close()
        return "Order not found or not yours."

    accepted_time, restaurant_id = result

    # Henüz kabul edilmemişse veya 24 saati geçmişse
    if not accepted_time or datetime.now() - accepted_time > timedelta(hours=24):
        conn.close()
        flash("Rating period expired. You can only rate within 24 hours after restaurant acceptance.")
        return redirect("/customer/dashboard")

    if request.method == "POST":
        rating = int(request.form["rating"])
        comment = request.form["comment"]
        cursor.execute("""
            INSERT INTO Rating (orderID, customerID, restaurantID, ratingValue, comment)
            VALUES (%s, %s, %s, %s, %s)
        """, (order_id, session["user_id"], restaurant_id, rating, comment))
        conn.commit()
        # Update pending ratings count in session using same connection
        cursor.execute("""
            SELECT COUNT(*)
            FROM `Order` O
            JOIN Cart C ON O.cartID = C.cartID
            WHERE C.customerID = %s AND C.status = 'ACCEPTED'
            AND NOT EXISTS (
                SELECT 1 FROM Rating R WHERE R.orderID = O.orderID
            )
        """, (session["user_id"],))
        session['pending_ratings'] = cursor.fetchone()[0]
        conn.close()
        flash("Thanks for your rating!")
        return redirect("/customer/dashboard")

    conn.close()
    return render_template("rate_order.html", order_id=order_id)


# Route to reorder a past order (copy items to a new BUILDING cart)
@customer_bp.route("/customer/reorder/<int:order_id>", methods=["POST"])
def reorder(order_id):
    if "user_id" not in session:
        return "Unauthorized", 401

    conn = get_connection()
    cursor = conn.cursor()

    # Get cartID and restaurantID from order
    cursor.execute("""
        SELECT C.cartID, C.restaurantID
        FROM `Order` O
        JOIN Cart C ON O.cartID = C.cartID
        WHERE O.orderID = %s AND C.customerID = %s
    """, (order_id, session["user_id"]))
    result = cursor.fetchone()
    if not result:
        conn.close()
        flash("Original order not found.")
        return redirect("/customer/orders")

    old_cart_id, restaurant_id = result

    # Create new cart
    cursor.execute("INSERT INTO Cart (customerID, restaurantID) VALUES (%s, %s)", (session["user_id"], restaurant_id))
    new_cart_id = cursor.lastrowid

    # Copy items from old cart
    cursor.execute("""
        SELECT itemID, quantity FROM CartItem WHERE cartID = %s
    """, (old_cart_id,))
    items = cursor.fetchall()

    for item_id, quantity in items:
        cursor.execute("""
            INSERT INTO CartItem (cartID, itemID, quantity) VALUES (%s, %s, %s)
        """, (new_cart_id, item_id, quantity))

    conn.commit()
    conn.close()
    flash("Order has been added to your cart.")
    return redirect("/customer/dashboard")
@customer_bp.route("/customer/orders")
def view_orders():
    if "user_id" not in session:
        return "Unauthorized", 401

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT O.orderID, R.restaurantName, C.createdTimestamp, C.status,
               GROUP_CONCAT(M.itemName SEPARATOR ', ') AS items,
               SUM(CI.quantity * M.price) AS total,
               CASE WHEN RT.ratingID IS NOT NULL THEN 1 ELSE 0 END AS is_rated
        FROM `Order` O
        JOIN Cart C ON O.cartID = C.cartID
        JOIN CartItem CI ON C.cartID = CI.cartID
        JOIN MenuItem M ON CI.itemID = M.itemID
        JOIN Restaurant R ON C.restaurantID = R.restaurantID
        LEFT JOIN Rating RT ON O.orderID = RT.orderID
        WHERE C.customerID = %s
        GROUP BY O.orderID
        ORDER BY C.createdTimestamp DESC
    """, (session["user_id"],))
    orders = cursor.fetchall()
    cursor.execute("""
        SELECT COUNT(*)
        FROM `Order` O
        JOIN Cart C ON O.cartID = C.cartID
        WHERE C.customerID = %s AND C.status = 'ACCEPTED'
        AND NOT EXISTS (
            SELECT 1 FROM Rating R WHERE R.orderID = O.orderID
        )
    """, (session["user_id"],))
    pending_count = cursor.fetchone()[0]
    session['pending_ratings'] = pending_count
    conn.close()

    return render_template("customer_orders.html", orders=orders)
@customer_bp.route("/customer/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return "Unauthorized", 401

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        email = request.form["email"]
        phone = request.form["phone"]
        address = request.form["address"]
        city = request.form["city"]
        district = request.form["district"]
        neighborhood = request.form["neighborhood"]

        cursor.execute("UPDATE User SET email = %s WHERE userID = %s", (email, session["user_id"]))

        cursor.execute("DELETE FROM UserPhone WHERE userID = %s", (session["user_id"],))
        cursor.execute("INSERT INTO UserPhone (userID, phoneNumber, phoneType) VALUES (%s, %s, 'Mobile')",
                       (session["user_id"], phone))

        cursor.execute("SELECT addressID FROM UserAddress WHERE userID = %s", (session["user_id"],))
        existing_address = cursor.fetchone()
        if existing_address:
            cursor.execute("""
                UPDATE UserAddress
                SET addressText = %s, city = %s, district = %s, neighborhood = %s
                WHERE userID = %s
            """, (address, city, district, neighborhood, session["user_id"]))
        else:
            cursor.execute("""
                INSERT INTO UserAddress (userID, addressText, city, district, neighborhood)
                VALUES (%s, %s, %s, %s, %s)
            """, (session["user_id"], address, city, district, neighborhood))

        conn.commit()
        conn.close()
        flash("Profile updated successfully.")
        return redirect("/customer/profile")

    # GET method — fetch existing user info
    cursor.execute("SELECT email FROM User WHERE userID = %s", (session["user_id"],))
    email = cursor.fetchone()[0]

    cursor.execute("SELECT phoneNumber FROM UserPhone WHERE userID = %s LIMIT 1", (session["user_id"],))
    phone = cursor.fetchone()
    phone = phone[0] if phone else ""

    cursor.execute("SELECT addressText FROM UserAddress WHERE userID = %s LIMIT 1", (session["user_id"],))
    address = cursor.fetchone()
    address = address[0] if address else ""

    conn.close()
    return render_template("customer_profile.html", email=email, phone=phone, address=address)