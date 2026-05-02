def get_orders_by_phone(phone, limit=20):
    phone = str(phone).replace(" ", "").replace("-", "").strip()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, order_number, telegram_id, telegram_name, customer_name, phone,
               city, street, floor, apartment, address, cart_json,
               products_total, delivery_price, final_total, base_city,
               status, created_at, updated_at
        FROM orders
        WHERE phone LIKE ?
        ORDER BY id DESC
        LIMIT ?
    """, (f"%{phone}%", int(limit)))

    rows = cur.fetchall()
    conn.close()

    return [order_row_to_dict(row) for row in rows]


def get_today_statistics():
    from datetime import datetime
    import json

    today = datetime.now().strftime("%Y-%m-%d")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*), COALESCE(SUM(final_total), 0)
        FROM orders
        WHERE created_at LIKE ?
    """, (f"{today}%",))
    total_orders, total_money = cur.fetchone()

    cur.execute("""
        SELECT status, COUNT(*)
        FROM orders
        WHERE created_at LIKE ?
        GROUP BY status
    """, (f"{today}%",))
    statuses = dict(cur.fetchall())

    cur.execute("""
        SELECT cart_json
        FROM orders
        WHERE created_at LIKE ?
    """, (f"{today}%",))
    carts = cur.fetchall()

    conn.close()

    product_sales = {}

    for row in carts:
        try:
            cart = json.loads(row[0])
        except Exception:
            cart = []

        for item in cart:
            name = item.get("name", "לא ידוע")
            qty = int(item.get("qty", 0))
            product_sales[name] = product_sales.get(name, 0) + qty

    top_product = None
    top_qty = 0

    for name, qty in product_sales.items():
        if qty > top_qty:
            top_product = name
            top_qty = qty

    return {
        "date": today,
        "total_orders": int(total_orders or 0),
        "total_money": float(total_money or 0),
        "new": int(statuses.get("new", 0)),
        "approved": int(statuses.get("approved", 0)),
        "processing": int(statuses.get("processing", 0)),
        "shipping": int(statuses.get("shipping", 0)),
        "paid": int(statuses.get("paid", 0)),
        "done": int(statuses.get("done", 0)),
        "cancelled": int(statuses.get("cancelled", 0)),
        "top_product": top_product,
        "top_qty": top_qty
    }
