from flask import Blueprint, render_template, request, redirect, session, url_for
from db_config import get_connection
from datetime import datetime, timedelta

manager_bp = Blueprint("manager", __name__)

@manager_bp.route("/manager/dashboard", methods=["GET", "POST"])
def manager_dashboard():
    if "user_id" not in session:
        return "Unauthorized", 401

    conn = get_connection()
    cursor = conn.cursor()

    # Menu addition
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

    rids = [r[0] for r in restaurants]
    restaurant_keywords = {}

    # Fetch keywords for each restaurant
    if rids:
        fmt_keys = ','.join(['%s'] * len(rids))
        cursor.execute(f"""
            SELECT t.restaurantID, k.keywordName
            FROM tagged_with t
            JOIN Keyword k ON t.keywordID = k.keywordID
            WHERE t.restaurantID IN ({fmt_keys})
        """, tuple(rids))
        for rid_val, kw in cursor.fetchall():
            restaurant_keywords.setdefault(rid_val, []).append(kw)

    if rids:
        format_strings = ','.join(['%s'] * len(rids))
        cursor.execute(f"""
            SELECT restaurantID,
                   COUNT(*) AS cnt,
                   AVG(ratingValue) AS avg
            FROM Rating
            WHERE restaurantID IN ({format_strings})
            GROUP BY restaurantID
        """, tuple(rids))
        rating_stats = {row[0]: {'cnt': row[1], 'avg': row[2]} for row in cursor.fetchall()}
    else:
        rating_stats = {}

    restaurant_menus = {}
    for r in restaurants:
        rid = r[0]
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
              M.price AS base_price,
              M.description
            FROM MenuItem M
            LEFT JOIN defines_discount D
              ON D.itemID = M.itemID
              AND NOW() BETWEEN D.startTime AND D.endTime
            WHERE M.restaurantID = %s
        """, (rid,))
        restaurant_menus[rid] = cursor.fetchall()

    one_month_ago = datetime.now() - timedelta(days=30)
    cursor.execute("""
        SELECT R.restaurantName,
               COUNT(DISTINCT O.orderID) AS order_count,
               SUM(M.price * CI.quantity)     AS revenue
        FROM Restaurant R
        JOIN Cart C ON R.restaurantID = C.restaurantID
        JOIN `Order` O ON C.cartID = O.cartID
        JOIN CartItem CI ON C.cartID = CI.cartID
        JOIN MenuItem M ON CI.itemID = M.itemID
        WHERE R.managerID = %s AND C.acceptedTimestamp >= %s
        GROUP BY R.restaurantName
    """, (session["user_id"], one_month_ago))
    stats = cursor.fetchall()

    # 2. Quantity & revenue per menu item in the last month
    cursor.execute("""
        SELECT M.itemName,
               SUM(CI.quantity) AS total_qty,
               SUM(CI.quantity * M.price) AS total_revenue
        FROM CartItem CI
        JOIN Cart C        ON CI.cartID = C.cartID
        JOIN MenuItem M    ON CI.itemID = M.itemID
        JOIN Restaurant R  ON C.restaurantID = R.restaurantID
        WHERE R.managerID = %s
          AND C.acceptedTimestamp >= %s
        GROUP BY M.itemID
    """, (session["user_id"], one_month_ago))
    item_stats = cursor.fetchall()

    # 3. Customer who placed the most orders in the last month
    cursor.execute("""
        SELECT C.customerID, COUNT(*) AS order_count
        FROM Cart C
        JOIN `Order` O    ON C.cartID = O.cartID
        JOIN Restaurant R ON C.restaurantID = R.restaurantID
        WHERE R.managerID = %s
          AND C.acceptedTimestamp >= %s
        GROUP BY C.customerID
        ORDER BY order_count DESC
        LIMIT 1
    """, (session["user_id"], one_month_ago))
    top_customer = cursor.fetchone()

    # 4. Highest-value cart in the last month
    cursor.execute("""
        SELECT O.orderID,
               SUM(CI.quantity * M.price) AS cart_value
        FROM CartItem CI
        JOIN Cart C        ON CI.cartID = C.cartID
        JOIN `Order` O     ON C.cartID = O.cartID
        JOIN MenuItem M    ON CI.itemID = M.itemID
        JOIN Restaurant R  ON C.restaurantID = R.restaurantID
        WHERE R.managerID = %s
          AND C.acceptedTimestamp >= %s
        GROUP BY O.orderID
        ORDER BY cart_value DESC
        LIMIT 1
    """, (session["user_id"], one_month_ago))
    top_cart = cursor.fetchone()

    # fetch items for top_cart if exists
    top_cart_items = []
    if top_cart:
        top_order_id = top_cart[0]
        cursor.execute("""
            SELECT MI.itemName, CI.quantity, MI.price
            FROM CartItem CI
            JOIN MenuItem MI ON CI.itemID = MI.itemID
            JOIN `Order` O ON CI.cartID = O.cartID
            WHERE O.orderID = %s
        """, (top_order_id,))
        top_cart_items = cursor.fetchall()
    else:
        top_cart_items = []

    cursor.execute("""
        SELECT C.cartID, C.customerID
        FROM Cart C
        JOIN Restaurant R ON C.restaurantID = R.restaurantID
        WHERE R.managerID = %s AND C.status = 'SENT'
    """, (session["user_id"],))
    pending_orders = cursor.fetchall()

    # 5. Contents of pending carts
    pending_items = {}
    for cart_id, cust_id in pending_orders:
        cursor.execute("""
            SELECT MI.itemName, CI.quantity, MI.price
            FROM CartItem CI
            JOIN MenuItem MI ON CI.itemID = MI.itemID
            WHERE CI.cartID = %s
        """, (cart_id,))
        pending_items[cart_id] = cursor.fetchall()

    # Compute total value for each pending cart
    pending_totals = {}
    for cart_id, items in pending_items.items():
        total = 0
        for name, qty, unit_price in items:
            total += qty * unit_price
        pending_totals[cart_id] = total

    conn.close()
    return render_template(
        "manager_dashboard.html",
        username=session["username"],
        restaurants=restaurants,
        restaurant_menus=restaurant_menus,
        stats=stats,
        item_stats=item_stats,
        top_customer=top_customer,
        top_cart=top_cart,
        top_cart_items=top_cart_items,
        pending_orders=pending_orders,
        rating_stats=rating_stats,
        pending_items=pending_items,
        pending_totals=pending_totals,
        restaurant_keywords=restaurant_keywords
    )

@manager_bp.route("/manager/accept/<int:cart_id>", methods=["POST"])
def accept_order(cart_id):
    if "user_id" not in session:
        return "Unauthorized", 401

    conn = get_connection()
    cursor = conn.cursor()
    # Insert into Order table, but ignore if already exists for this cart
    cursor.execute("""
        INSERT IGNORE INTO `Order` (cartID)
        VALUES (%s)
    """, (cart_id,))
    cursor.execute("""
        UPDATE Cart
        SET status = 'ACCEPTED', 
            acceptedTimestamp = NOW()
        WHERE cartID = %s AND restaurantID IN (
            SELECT restaurantID FROM Restaurant WHERE managerID = %s
        )
    """, (cart_id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(url_for('manager.manager_dashboard'))


# Delete menu item route
@manager_bp.route("/manager/delete_item/<int:item_id>", methods=["POST"])
def delete_item(item_id):
    if "user_id" not in session:
        return "Unauthorized", 401
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE MI FROM MenuItem MI
        JOIN Restaurant R ON MI.restaurantID = R.restaurantID
        WHERE MI.itemID = %s AND R.managerID = %s
    """, (item_id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect("/manager/dashboard")


# 1. Show keyword-picker form
@manager_bp.route("/manager/keywords/<int:rid>", methods=["GET"])
def edit_keywords(rid):
    if "user_id" not in session:
        return "Unauthorized", 401
    conn = get_connection()
    cur = conn.cursor()
    # ownership guard
    cur.execute(
        "SELECT 1 FROM Restaurant WHERE restaurantID=%s AND managerID=%s",
        (rid, session["user_id"])
    )
    if not cur.fetchone():
        conn.close()
        return "Forbidden", 403

    cur.execute("SELECT keywordID, keywordName FROM Keyword")
    all_keys = cur.fetchall()
    cur.execute("SELECT keywordID FROM tagged_with WHERE restaurantID=%s", (rid,))
    tagged = {row[0] for row in cur.fetchall()}
    conn.close()
    return render_template("edit_keywords.html",
                           restaurant_id=rid,
                           all_keys=all_keys,
                           tagged=tagged)

# 2. Process keyword updates
@manager_bp.route("/manager/keywords/<int:rid>", methods=["POST"])
def save_keywords(rid):
    if "user_id" not in session:
        return "Unauthorized", 401
    conn = get_connection()
    cur = conn.cursor()
    # clear old tags
    cur.execute("DELETE FROM tagged_with WHERE restaurantID=%s", (rid,))
    # insert new
    for kid in request.form.getlist("keyword"):
        cur.execute(
            "INSERT INTO tagged_with (restaurantID,keywordID) VALUES (%s,%s)",
            (rid, kid)
        )
    conn.commit()
    conn.close()
    return redirect("/manager/dashboard")

# 3. Show discounts management form
@manager_bp.route("/manager/discounts/<int:rid>", methods=["GET"])
def edit_discounts(rid):
    if "user_id" not in session:
        return "Unauthorized", 401
    conn = get_connection()
    cur = conn.cursor()
    # ownership guard
    cur.execute(
        "SELECT 1 FROM Restaurant WHERE restaurantID=%s AND managerID=%s",
        (rid, session["user_id"])
    )
    if not cur.fetchone():
        conn.close()
        return "Forbidden", 403

    # fetch all items for this restaurant
    cur.execute("""
        SELECT itemID, itemName, price
        FROM MenuItem
        WHERE restaurantID=%s
    """, (rid,))
    items = cur.fetchall()

    # fetch active discounts for this restaurant's items
    cur.execute("""
        SELECT D.itemID, D.startTime, D.endTime, D.discountAmount, D.discountRate
        FROM defines_discount D
        JOIN MenuItem M ON D.itemID = M.itemID
        WHERE M.restaurantID = %s
    """, (rid,))
    discounts = cur.fetchall()

    conn.close()
    return render_template("edit_discounts.html",
                           restaurant_id=rid,
                           items=items,
                           discounts=discounts)

# 4. Process discount updates
@manager_bp.route("/manager/discounts/<int:rid>", methods=["POST"])
def save_discounts(rid):
    if "user_id" not in session:
        return "Unauthorized", 401
    conn = get_connection()
    cur = conn.cursor()
    # ownership guard
    cur.execute(
        "SELECT 1 FROM Restaurant WHERE restaurantID=%s AND managerID=%s",
        (rid, session["user_id"])
    )
    if not cur.fetchone():
        conn.close()
        return "Forbidden", 403

    # clear existing discounts for this restaurant
    cur.execute("""
        DELETE D
        FROM defines_discount D
        JOIN MenuItem M ON D.itemID = M.itemID
        WHERE M.restaurantID = %s
    """, (rid,))

    # insert new discounts from form
    # expect fields like discount-<itemID>-start, discount-<itemID>-end, discount-<itemID>-amt, discount-<itemID>-rate
    for field in request.form:
        if field.startswith("discount-") and field.endswith("-start"):
            item_id = int(field.split("-")[1])
            start = request.form.get(f"discount-{item_id}-start")
            end   = request.form.get(f"discount-{item_id}-end")
            amt_str  = request.form.get(f"discount-{item_id}-amt", "").strip()
            rate_str = request.form.get(f"discount-{item_id}-rate", "").strip()
            try:
                amt_val  = float(amt_str)  if amt_str  else None
                rate_val = float(rate_str) if rate_str else None
            except ValueError:
                # invalid numeric input—skip this discount
                continue

            # validate ranges
            if amt_val is not None and amt_val < 0:
                continue
            if rate_val is not None and not (0 <= rate_val <= 100):
                continue

            # only save if at least one valid discount provided
            if amt_val is not None or rate_val is not None:
                cur.execute("""
                    INSERT INTO defines_discount
                      (managerID, itemID, startTime, endTime, discountAmount, discountRate)
                    VALUES
                      (%s, %s, %s, %s, %s, %s)
                """, (session["user_id"], item_id, start, end, amt_val, rate_val))
    conn.commit()
    conn.close()
    return redirect("/manager/dashboard")