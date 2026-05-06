import os
import json
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

DB_DIR = "/data"
LOCAL_DB = "vendora_shop.db"

try:
    os.makedirs(DB_DIR, exist_ok=True)
    test_path = os.path.join(DB_DIR, ".test")
    with open(test_path, "w", encoding="utf-8") as f:
        f.write("ok")
    os.remove(test_path)
    DB_PATH = os.path.join(DB_DIR, "vendora_shop.db")
except Exception:
    DB_PATH = LOCAL_DB

print(f"Using database: {DB_PATH}")


def get_connection():
    return sqlite3.connect(DB_PATH)




def israel_now():
    """
    מחזיר תאריך ושעה לפי שעון ישראל.
    חשוב במיוחד ב־Railway/שרתים שעובדים לפי UTC.
    """
    return datetime.now(ZoneInfo("Asia/Jerusalem"))


def israel_now_str():
    return israel_now().strftime("%Y-%m-%d %H:%M:%S")


def israel_today_str():
    return israel_now().strftime("%Y-%m-%d")


def israel_month_str():
    return israel_now().strftime("%Y-%m")


def israel_year_str():
    return israel_now().strftime("%Y")


def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            name TEXT NOT NULL UNIQUE,
            price REAL NOT NULL,
            description TEXT DEFAULT '',
            max_qty INTEGER DEFAULT 100,
            stock INTEGER DEFAULT 0,
            sku TEXT DEFAULT '',
            image_file_id TEXT DEFAULT '',
            active INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE,
            telegram_id INTEGER NOT NULL,
            telegram_name TEXT DEFAULT '',
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            city TEXT NOT NULL,
            street TEXT NOT NULL,
            floor TEXT DEFAULT '',
            apartment TEXT DEFAULT '',
            address TEXT NOT NULL,
            cart_json TEXT NOT NULL,
            products_total REAL NOT NULL,
            delivery_price REAL NOT NULL,
            final_total REAL NOT NULL,
            base_city TEXT DEFAULT '',
            status TEXT DEFAULT 'new',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL UNIQUE,
            telegram_name TEXT DEFAULT '',
            customer_name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            city TEXT DEFAULT '',
            street TEXT DEFAULT '',
            floor TEXT DEFAULT '',
            apartment TEXT DEFAULT '',
            last_order_number TEXT DEFAULT '',
            total_orders INTEGER DEFAULT 0,
            total_spent REAL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def add_product(category, name, price, description="", max_qty=100, stock=0, sku="", image_file_id="", active=1):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO products
        (category, name, price, description, max_qty, stock, sku, image_file_id, active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (category, name, float(price), description, int(max_qty), int(stock), sku, image_file_id, int(active)))
    conn.commit()
    conn.close()


def get_active_products():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT category, name, price, description, max_qty, stock, sku, image_file_id
        FROM products
        WHERE active = 1
        ORDER BY category, name
    """)
    rows = cur.fetchall()
    conn.close()

    products = {}
    for category, name, price, description, max_qty, stock, sku, image_file_id in rows:
        products.setdefault(category, []).append({
            "category": category,
            "name": name,
            "price": price,
            "description": description,
            "max_qty": max_qty,
            "stock": stock,
            "sku": sku,
            "image_file_id": image_file_id
        })
    return products


def get_all_products():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, category, name, price, description, max_qty, stock, sku, image_file_id, active
        FROM products
        ORDER BY category, name
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_product_by_name(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, category, name, price, description, max_qty, stock, sku, image_file_id, active
        FROM products
        WHERE name = ?
    """, (name,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    product_id, category, name, price, description, max_qty, stock, sku, image_file_id, active = row
    return {
        "id": product_id,
        "category": category,
        "name": name,
        "price": price,
        "description": description,
        "max_qty": max_qty,
        "stock": stock,
        "sku": sku,
        "image_file_id": image_file_id,
        "active": active
    }


def set_product_price(name, price):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE products SET price = ? WHERE name = ?", (float(price), name))
    conn.commit()
    changed = cur.rowcount
    conn.close()
    return changed > 0


def set_product_description(name, description):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE products SET description = ? WHERE name = ?", (description, name))
    conn.commit()
    changed = cur.rowcount
    conn.close()
    return changed > 0


def set_product_stock(name, stock):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE products SET stock = ? WHERE name = ?", (int(stock), name))
    conn.commit()
    changed = cur.rowcount
    conn.close()
    return changed > 0


def add_stock(name, amount):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE products SET stock = stock + ? WHERE name = ?", (int(amount), name))
    conn.commit()
    changed = cur.rowcount
    conn.close()
    return changed > 0


def set_product_image(name, image_file_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE products SET image_file_id = ? WHERE name = ?", (image_file_id, name))
    conn.commit()
    changed = cur.rowcount
    conn.close()
    return changed > 0


def set_product_active(name, active):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE products SET active = ? WHERE name = ?", (int(active), name))
    conn.commit()
    changed = cur.rowcount
    conn.close()
    return changed > 0


def delete_product(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE name = ?", (name,))
    conn.commit()
    changed = cur.rowcount
    conn.close()
    return changed > 0


def reduce_stock(cart):
    conn = get_connection()
    cur = conn.cursor()

    for item in cart:
        qty = int(item["qty"])
        name = item["name"]

        cur.execute("""
            UPDATE products
            SET stock = stock - ?
            WHERE name = ? AND stock >= ?
        """, (qty, name, qty))

        if cur.rowcount == 0:
            conn.rollback()
            conn.close()
            return False, name

    conn.commit()
    conn.close()
    return True, None


def generate_order_number(order_id):
    return f"V{1000 + int(order_id)}"


def create_order(
    telegram_id,
    telegram_name,
    customer_name,
    phone,
    city,
    street,
    floor,
    apartment,
    cart,
    products_total,
    delivery_price,
    final_total,
    base_city=""
):
    conn = get_connection()
    cur = conn.cursor()

    now = israel_now_str()
    address = f"{city}, {street}, קומה {floor}, דירה {apartment}"
    cart_json = json.dumps(cart, ensure_ascii=False)

    cur.execute("""
        INSERT INTO orders (
            order_number,
            telegram_id,
            telegram_name,
            customer_name,
            phone,
            city,
            street,
            floor,
            apartment,
            address,
            cart_json,
            products_total,
            delivery_price,
            final_total,
            base_city,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "",
        int(telegram_id),
        telegram_name,
        customer_name,
        phone,
        city,
        street,
        floor,
        apartment,
        address,
        cart_json,
        float(products_total),
        float(delivery_price),
        float(final_total),
        base_city,
        "new",
        now,
        now
    ))

    order_id = cur.lastrowid
    order_number = generate_order_number(order_id)

    cur.execute("UPDATE orders SET order_number = ? WHERE id = ?", (order_number, order_id))

    conn.commit()
    conn.close()

    return order_number


def order_row_to_dict(row):
    (
        order_id,
        order_number,
        telegram_id,
        telegram_name,
        customer_name,
        phone,
        city,
        street,
        floor,
        apartment,
        address,
        cart_json,
        products_total,
        delivery_price,
        final_total,
        base_city,
        status,
        created_at,
        updated_at
    ) = row

    try:
        cart = json.loads(cart_json)
    except Exception:
        cart = []

    return {
        "id": order_id,
        "order_number": order_number,
        "telegram_id": telegram_id,
        "telegram_name": telegram_name,
        "customer_name": customer_name,
        "phone": phone,
        "city": city,
        "street": street,
        "floor": floor,
        "apartment": apartment,
        "address": address,
        "cart": cart,
        "products_total": products_total,
        "delivery_price": delivery_price,
        "final_total": final_total,
        "base_city": base_city,
        "status": status,
        "created_at": created_at,
        "updated_at": updated_at
    }


def get_order_by_number(order_number):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, order_number, telegram_id, telegram_name, customer_name, phone,
               city, street, floor, apartment, address, cart_json,
               products_total, delivery_price, final_total, base_city,
               status, created_at, updated_at
        FROM orders
        WHERE order_number = ?
    """, (order_number,))
    row = cur.fetchone()
    conn.close()
    return order_row_to_dict(row) if row else None


def get_recent_orders(limit=10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, order_number, telegram_id, telegram_name, customer_name, phone,
               city, street, floor, apartment, address, cart_json,
               products_total, delivery_price, final_total, base_city,
               status, created_at, updated_at
        FROM orders
        ORDER BY id DESC
        LIMIT ?
    """, (int(limit),))
    rows = cur.fetchall()
    conn.close()
    return [order_row_to_dict(row) for row in rows]


def get_orders_by_status(status, limit=20):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, order_number, telegram_id, telegram_name, customer_name, phone,
               city, street, floor, apartment, address, cart_json,
               products_total, delivery_price, final_total, base_city,
               status, created_at, updated_at
        FROM orders
        WHERE status = ?
        ORDER BY id DESC
        LIMIT ?
    """, (status, int(limit)))
    rows = cur.fetchall()
    conn.close()
    return [order_row_to_dict(row) for row in rows]


def update_order_status(order_number, status):
    conn = get_connection()
    cur = conn.cursor()
    now = israel_now_str()

    cur.execute("""
        UPDATE orders
        SET status = ?, updated_at = ?
        WHERE order_number = ?
    """, (status, now, order_number))

    conn.commit()
    changed = cur.rowcount
    conn.close()
    return changed > 0


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



def customer_row_to_dict(row):
    if not row:
        return None

    (
        customer_id,
        telegram_id,
        telegram_name,
        customer_name,
        phone,
        city,
        street,
        floor,
        apartment,
        last_order_number,
        total_orders,
        total_spent,
        created_at,
        updated_at
    ) = row

    return {
        "id": customer_id,
        "telegram_id": telegram_id,
        "telegram_name": telegram_name,
        "customer_name": customer_name,
        "phone": phone,
        "city": city,
        "street": street,
        "floor": floor,
        "apartment": apartment,
        "last_order_number": last_order_number,
        "total_orders": total_orders,
        "total_spent": total_spent,
        "created_at": created_at,
        "updated_at": updated_at
    }


def get_customer_profile(telegram_id):
    create_tables()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, telegram_id, telegram_name, customer_name, phone, city,
               street, floor, apartment, last_order_number, total_orders,
               total_spent, created_at, updated_at
        FROM customers
        WHERE telegram_id = ?
    """, (int(telegram_id),))
    row = cur.fetchone()
    conn.close()
    return customer_row_to_dict(row)


def save_customer_profile(
    telegram_id,
    telegram_name,
    customer_name,
    phone,
    city,
    street,
    floor,
    apartment,
    last_order_number="",
    order_total=0
):
    create_tables()
    now = israel_now_str()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM customers WHERE telegram_id = ?", (int(telegram_id),))
    existing = cur.fetchone()

    if existing:
        cur.execute("""
            UPDATE customers
            SET telegram_name = ?,
                customer_name = ?,
                phone = ?,
                city = ?,
                street = ?,
                floor = ?,
                apartment = ?,
                last_order_number = ?,
                total_orders = total_orders + 1,
                total_spent = total_spent + ?,
                updated_at = ?
            WHERE telegram_id = ?
        """, (
            telegram_name,
            customer_name,
            phone,
            city,
            street,
            floor,
            apartment,
            last_order_number,
            float(order_total),
            now,
            int(telegram_id)
        ))
    else:
        cur.execute("""
            INSERT INTO customers (
                telegram_id, telegram_name, customer_name, phone, city,
                street, floor, apartment, last_order_number, total_orders,
                total_spent, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            int(telegram_id), telegram_name, customer_name, phone, city,
            street, floor, apartment, last_order_number, 1,
            float(order_total), now, now
        ))

    conn.commit()
    conn.close()
    return True


def _period_statistics(prefix):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*), COALESCE(SUM(final_total), 0)
        FROM orders
        WHERE created_at LIKE ?
    """, (f"{prefix}%",))
    total_orders, total_money = cur.fetchone()

    cur.execute("""
        SELECT COUNT(DISTINCT telegram_id)
        FROM orders
        WHERE created_at LIKE ?
    """, (f"{prefix}%",))
    customers = cur.fetchone()[0]

    cur.execute("""
        SELECT cart_json
        FROM orders
        WHERE created_at LIKE ?
    """, (f"{prefix}%",))
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
            if name:
                product_sales[name] = product_sales.get(name, 0) + qty

    top_product = "-"
    top_qty = 0

    for name, qty in product_sales.items():
        if qty > top_qty:
            top_product = name
            top_qty = qty

    total_orders = int(total_orders or 0)
    total_money = float(total_money or 0)
    avg_order = total_money / total_orders if total_orders > 0 else 0

    return {
        "money": total_money,
        "orders": total_orders,
        "customers": int(customers or 0),
        "avg_order": float(avg_order or 0),
        "top_product": top_product,
        "top_qty": int(top_qty or 0),
    }


def get_dashboard_statistics():
    today = israel_today_str()
    month = israel_month_str()
    year = israel_year_str()

    today_stats = _period_statistics(today)
    month_stats = _period_statistics(month)
    year_stats = _period_statistics(year)

    return {
        "today_money": today_stats["money"],
        "today_orders": today_stats["orders"],
        "today_customers": today_stats["customers"],
        "today_avg_order": today_stats["avg_order"],
        "today_top_product": today_stats["top_product"],
        "today_top_qty": today_stats["top_qty"],

        "month_money": month_stats["money"],
        "month_orders": month_stats["orders"],
        "month_customers": month_stats["customers"],
        "month_avg_order": month_stats["avg_order"],
        "month_top_product": month_stats["top_product"],
        "month_top_qty": month_stats["top_qty"],

        "year_money": year_stats["money"],
        "year_orders": year_stats["orders"],
        "year_customers": year_stats["customers"],
        "year_avg_order": year_stats["avg_order"],
        "year_top_product": year_stats["top_product"],
        "year_top_qty": year_stats["top_qty"],
    }


def get_statistics_by_date(date_text):
    """
    date_text format: YYYY-MM-DD
    Example: 2026-05-05
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*), COALESCE(SUM(final_total), 0)
        FROM orders
        WHERE created_at LIKE ?
    """, (f"{date_text}%",))
    total_orders, total_money = cur.fetchone()

    cur.execute("""
        SELECT status, COUNT(*)
        FROM orders
        WHERE created_at LIKE ?
        GROUP BY status
    """, (f"{date_text}%",))
    statuses = dict(cur.fetchall())

    cur.execute("""
        SELECT cart_json
        FROM orders
        WHERE created_at LIKE ?
    """, (f"{date_text}%",))
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
            if name:
                product_sales[name] = product_sales.get(name, 0) + qty

    top_product = "-"
    top_qty = 0

    for name, qty in product_sales.items():
        if qty > top_qty:
            top_product = name
            top_qty = qty

    return {
        "date": date_text,
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
        "top_qty": int(top_qty or 0),
    }

def get_open_orders(limit=30):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, order_number, telegram_id, telegram_name, customer_name, phone,
               city, street, floor, apartment, address, cart_json,
               products_total, delivery_price, final_total, base_city,
               status, created_at, updated_at
        FROM orders
        WHERE status NOT IN ('done', 'cancelled')
        ORDER BY id DESC
        LIMIT ?
    """, (int(limit),))
    rows = cur.fetchall()
    conn.close()
    return [order_row_to_dict(row) for row in rows]


def get_done_orders(limit=30):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, order_number, telegram_id, telegram_name, customer_name, phone,
               city, street, floor, apartment, address, cart_json,
               products_total, delivery_price, final_total, base_city,
               status, created_at, updated_at
        FROM orders
        WHERE status = 'done'
        ORDER BY id DESC
        LIMIT ?
    """, (int(limit),))
    rows = cur.fetchall()
    conn.close()
    return [order_row_to_dict(row) for row in rows]


def get_cancelled_orders(limit=30):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, order_number, telegram_id, telegram_name, customer_name, phone,
               city, street, floor, apartment, address, cart_json,
               products_total, delivery_price, final_total, base_city,
               status, created_at, updated_at
        FROM orders
        WHERE status = 'cancelled'
        ORDER BY id DESC
        LIMIT ?
    """, (int(limit),))
    rows = cur.fetchall()
    conn.close()
    return [order_row_to_dict(row) for row in rows]


def get_orders_status_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT status, COUNT(*)
        FROM orders
        GROUP BY status
    """)
    rows = cur.fetchall()
    conn.close()

    counts = {
        "new": 0,
        "approved": 0,
        "processing": 0,
        "shipping": 0,
        "done": 0,
        "cancelled": 0,
    }

    for status, count in rows:
        if status in counts:
            counts[status] = int(count or 0)

    counts["open"] = counts["new"] + counts["approved"] + counts["processing"] + counts["shipping"]

    return counts

def get_all_customer_telegram_ids():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT telegram_id
        FROM customers
        WHERE telegram_id IS NOT NULL
          AND telegram_id != ''
    """)

    rows = cur.fetchall()
    conn.close()

    customer_ids = []

    for row in rows:
        try:
            customer_ids.append(int(row[0]))
        except Exception:
            pass

    return customer_ids

def get_customers_list(limit=30):
    create_tables()
    conn = get_connection()
    cur = conn.cursor()

    results = []
    seen = set()

    cur.execute("""
        SELECT id, telegram_id, telegram_name, customer_name, phone, city,
               street, floor, apartment, last_order_number, total_orders,
               total_spent, created_at, updated_at
        FROM customers
        ORDER BY total_orders DESC, total_spent DESC, updated_at DESC
        LIMIT ?
    """, (int(limit),))

    for row in cur.fetchall():
        customer = customer_row_to_dict(row)
        if customer:
            results.append(customer)
            seen.add(customer.get("telegram_id"))

    if len(results) < int(limit):
        cur.execute("""
            SELECT telegram_id, MAX(telegram_name), MAX(customer_name), MAX(phone),
                   MAX(city), MAX(street), MAX(floor), MAX(apartment),
                   MAX(order_number), COUNT(*), COALESCE(SUM(final_total), 0),
                   MIN(created_at), MAX(created_at)
            FROM orders
            GROUP BY telegram_id
            ORDER BY MAX(created_at) DESC
            LIMIT ?
        """, (int(limit),))

        for row in cur.fetchall():
            telegram_id, telegram_name, customer_name, phone, city, street, floor, apartment, last_order_number, total_orders, total_spent, created_at, updated_at = row

            if telegram_id in seen:
                continue

            results.append({
                "id": int(telegram_id),
                "telegram_id": telegram_id,
                "telegram_name": telegram_name,
                "customer_name": customer_name,
                "phone": phone,
                "city": city,
                "street": street,
                "floor": floor,
                "apartment": apartment,
                "last_order_number": last_order_number,
                "total_orders": total_orders,
                "total_spent": total_spent,
                "created_at": created_at,
                "updated_at": updated_at
            })

            seen.add(telegram_id)

            if len(results) >= int(limit):
                break

    conn.close()
    return results[:int(limit)]


def clean_phone_for_search(value):
    phone = str(value or "").strip()
    phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    if phone.startswith("+972"):
        phone = "0" + phone[4:]

    if phone.startswith("972"):
        phone = "0" + phone[3:]

    return phone


def search_customers(query, limit=30):
    create_tables()

    query = str(query or "").strip()
    clean_query = clean_phone_for_search(query)
    phone_tail = clean_query[-7:] if len(clean_query) >= 7 else clean_query
    is_phone = clean_query.isdigit() and len(clean_query) >= 7

    conn = get_connection()
    cur = conn.cursor()

    results = []
    seen = set()

    if is_phone:
        cur.execute("""
            SELECT id, telegram_id, telegram_name, customer_name, phone, city,
                   street, floor, apartment, last_order_number, total_orders,
                   total_spent, created_at, updated_at
            FROM customers
            WHERE REPLACE(REPLACE(REPLACE(REPLACE(phone, ' ', ''), '-', ''), '+972', '0'), '972', '0') LIKE ?
               OR REPLACE(REPLACE(REPLACE(REPLACE(phone, ' ', ''), '-', ''), '+972', '0'), '972', '0') LIKE ?
               OR phone LIKE ?
            ORDER BY total_orders DESC, total_spent DESC, updated_at DESC
            LIMIT ?
        """, (f"%{clean_query}%", f"%{phone_tail}%", f"%{query}%", int(limit)))
    else:
        cur.execute("""
            SELECT id, telegram_id, telegram_name, customer_name, phone, city,
                   street, floor, apartment, last_order_number, total_orders,
                   total_spent, created_at, updated_at
            FROM customers
            WHERE customer_name LIKE ?
               OR phone LIKE ?
               OR telegram_name LIKE ?
            ORDER BY total_orders DESC, total_spent DESC, updated_at DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%", int(limit)))

    for row in cur.fetchall():
        customer = customer_row_to_dict(row)
        if customer:
            results.append(customer)
            seen.add(customer.get("telegram_id"))

    if len(results) < int(limit):
        if is_phone:
            cur.execute("""
                SELECT telegram_id, MAX(telegram_name), MAX(customer_name), MAX(phone),
                       MAX(city), MAX(street), MAX(floor), MAX(apartment),
                       MAX(order_number), COUNT(*), COALESCE(SUM(final_total), 0),
                       MIN(created_at), MAX(created_at)
                FROM orders
                WHERE REPLACE(REPLACE(REPLACE(REPLACE(phone, ' ', ''), '-', ''), '+972', '0'), '972', '0') LIKE ?
                   OR REPLACE(REPLACE(REPLACE(REPLACE(phone, ' ', ''), '-', ''), '+972', '0'), '972', '0') LIKE ?
                   OR phone LIKE ?
                GROUP BY telegram_id
                ORDER BY MAX(created_at) DESC
                LIMIT ?
            """, (f"%{clean_query}%", f"%{phone_tail}%", f"%{query}%", int(limit)))
        else:
            cur.execute("""
                SELECT telegram_id, MAX(telegram_name), MAX(customer_name), MAX(phone),
                       MAX(city), MAX(street), MAX(floor), MAX(apartment),
                       MAX(order_number), COUNT(*), COALESCE(SUM(final_total), 0),
                       MIN(created_at), MAX(created_at)
                FROM orders
                WHERE customer_name LIKE ?
                   OR phone LIKE ?
                   OR telegram_name LIKE ?
                GROUP BY telegram_id
                ORDER BY MAX(created_at) DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", int(limit)))

        for row in cur.fetchall():
            telegram_id, telegram_name, customer_name, phone, city, street, floor, apartment, last_order_number, total_orders, total_spent, created_at, updated_at = row

            if telegram_id in seen:
                continue

            results.append({
                "id": int(telegram_id),
                "telegram_id": telegram_id,
                "telegram_name": telegram_name,
                "customer_name": customer_name,
                "phone": phone,
                "city": city,
                "street": street,
                "floor": floor,
                "apartment": apartment,
                "last_order_number": last_order_number,
                "total_orders": total_orders,
                "total_spent": total_spent,
                "created_at": created_at,
                "updated_at": updated_at
            })

            seen.add(telegram_id)

            if len(results) >= int(limit):
                break

    conn.close()
    return results[:int(limit)]


def get_customer_by_id(customer_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, telegram_id, telegram_name, customer_name, phone, city,
               street, floor, apartment, last_order_number, total_orders,
               total_spent, created_at, updated_at
        FROM customers
        WHERE id = ?
    """, (int(customer_id),))

    row = cur.fetchone()
    conn.close()

    return customer_row_to_dict(row)


def get_orders_by_customer_telegram_id(telegram_id, limit=30):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, order_number, telegram_id, telegram_name, customer_name, phone,
               city, street, floor, apartment, address, cart_json,
               products_total, delivery_price, final_total, base_city,
               status, created_at, updated_at
        FROM orders
        WHERE telegram_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (int(telegram_id), int(limit)))

    rows = cur.fetchall()
    conn.close()

    return [order_row_to_dict(row) for row in rows]

# ============================================================
# CUSTOMER EXPERIENCE FEATURES
# ============================================================
# הפונקציות הבאות הן בסיס מקצועי לפיצ'רים שמעלים את חוויית הלקוח:
# 1. הזמנה חוזרת
# 2. שמירת כתובות
# 3. קופונים
# 4. ביקורות
# 5. מעקב הזמנה חי
# 6. מוצרים קשורים
# 7. מועדון נקודות
# 8. עגלות נטושות
# ============================================================


def create_customer_experience_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            label TEXT DEFAULT 'כתובת',
            city TEXT NOT NULL,
            street TEXT NOT NULL,
            floor TEXT DEFAULT '',
            apartment TEXT DEFAULT '',
            is_default INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS favorite_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(telegram_id, product_name)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS product_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            related_product_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(product_name, related_product_name)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            discount_type TEXT NOT NULL,
            discount_value REAL NOT NULL,
            min_order_total REAL DEFAULT 0,
            max_uses INTEGER DEFAULT 0,
            used_count INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            expires_at TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS coupon_usages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            telegram_id INTEGER NOT NULL,
            order_number TEXT DEFAULT '',
            used_at TEXT NOT NULL,
            UNIQUE(code, telegram_id, order_number)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT NOT NULL UNIQUE,
            telegram_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT NOT NULL,
            status TEXT NOT NULL,
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS loyalty_points (
            telegram_id INTEGER PRIMARY KEY,
            points INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS abandoned_carts (
            telegram_id INTEGER PRIMARY KEY,
            cart_json TEXT NOT NULL,
            last_total REAL DEFAULT 0,
            reminder_sent INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ---------- Addresses ----------
def add_customer_address(telegram_id, label, city, street, floor='', apartment='', is_default=0):
    create_customer_experience_tables()
    now = israel_now_str() if 'israel_now_str' in globals() else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_connection()
    cur = conn.cursor()

    if int(is_default):
        cur.execute("UPDATE customer_addresses SET is_default = 0 WHERE telegram_id = ?", (int(telegram_id),))

    cur.execute("""
        INSERT INTO customer_addresses
        (telegram_id, label, city, street, floor, apartment, is_default, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (int(telegram_id), label, city, street, floor, apartment, int(is_default), now, now))

    conn.commit()
    conn.close()
    return True


def get_customer_addresses(telegram_id):
    create_customer_experience_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, label, city, street, floor, apartment, is_default
        FROM customer_addresses
        WHERE telegram_id = ?
        ORDER BY is_default DESC, id DESC
    """, (int(telegram_id),))
    rows = cur.fetchall()
    conn.close()
    return [
        {
            'id': r[0], 'label': r[1], 'city': r[2], 'street': r[3],
            'floor': r[4], 'apartment': r[5], 'is_default': r[6]
        }
        for r in rows
    ]


# ---------- Favorites ----------
def toggle_favorite_product(telegram_id, product_name):
    create_customer_experience_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM favorite_products WHERE telegram_id = ? AND product_name = ?", (int(telegram_id), product_name))
    row = cur.fetchone()
    if row:
        cur.execute("DELETE FROM favorite_products WHERE id = ?", (row[0],))
        conn.commit(); conn.close()
        return False
    now = israel_now_str() if 'israel_now_str' in globals() else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cur.execute("INSERT OR IGNORE INTO favorite_products (telegram_id, product_name, created_at) VALUES (?, ?, ?)", (int(telegram_id), product_name, now))
    conn.commit(); conn.close()
    return True


def get_favorite_products(telegram_id):
    create_customer_experience_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT product_name FROM favorite_products WHERE telegram_id = ? ORDER BY id DESC", (int(telegram_id),))
    rows = cur.fetchall(); conn.close()
    return [r[0] for r in rows]


# ---------- Related Products ----------
def add_related_product(product_name, related_product_name):
    create_customer_experience_tables()
    now = israel_now_str() if 'israel_now_str' in globals() else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO product_relations (product_name, related_product_name, created_at) VALUES (?, ?, ?)", (product_name, related_product_name, now))
    conn.commit(); conn.close(); return True


def get_related_products(product_name, limit=5):
    create_customer_experience_tables()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT related_product_name FROM product_relations WHERE product_name = ? LIMIT ?", (product_name, int(limit)))
    rows = cur.fetchall(); conn.close()
    return [r[0] for r in rows]


# ---------- Coupons ----------
def create_coupon(code, discount_type, discount_value, min_order_total=0, max_uses=0, expires_at=''):
    create_customer_experience_tables()
    now = israel_now_str() if 'israel_now_str' in globals() else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO coupons
        (code, discount_type, discount_value, min_order_total, max_uses, expires_at, active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
    """, (code.upper().strip(), discount_type, float(discount_value), float(min_order_total), int(max_uses), expires_at, now))
    conn.commit(); conn.close(); return True


def validate_coupon(code, telegram_id, order_total):
    create_customer_experience_tables()
    code = str(code or '').upper().strip()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT code, discount_type, discount_value, min_order_total, max_uses, used_count, active, expires_at FROM coupons WHERE code = ?", (code,))
    row = cur.fetchone(); conn.close()
    if not row:
        return False, 0, 'קוד קופון לא נמצא.'
    _, dtype, dvalue, min_total, max_uses, used_count, active, expires_at = row
    if not active:
        return False, 0, 'הקופון אינו פעיל.'
    if float(order_total) < float(min_total or 0):
        return False, 0, f'הקופון תקף להזמנות מעל {min_total}₪.'
    if int(max_uses or 0) > 0 and int(used_count or 0) >= int(max_uses):
        return False, 0, 'הקופון הגיע למגבלת שימושים.'
    if dtype == 'percent':
        discount = float(order_total) * float(dvalue) / 100
    else:
        discount = float(dvalue)
    discount = max(0, min(discount, float(order_total)))
    return True, round(discount, 2), 'ok'


def mark_coupon_used(code, telegram_id, order_number):
    create_customer_experience_tables()
    now = israel_now_str() if 'israel_now_str' in globals() else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO coupon_usages (code, telegram_id, order_number, used_at) VALUES (?, ?, ?, ?)", (code.upper().strip(), int(telegram_id), order_number, now))
    cur.execute("UPDATE coupons SET used_count = used_count + 1 WHERE code = ?", (code.upper().strip(),))
    conn.commit(); conn.close(); return True


# ---------- Reviews ----------
def save_order_review(order_number, telegram_id, rating, comment=''):
    create_customer_experience_tables()
    rating = int(rating)
    if rating < 1 or rating > 5:
        return False
    now = israel_now_str() if 'israel_now_str' in globals() else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO order_reviews (order_number, telegram_id, rating, comment, created_at) VALUES (?, ?, ?, ?, ?)", (order_number, int(telegram_id), rating, comment, now))
    conn.commit(); conn.close(); return True


# ---------- Order Tracking ----------
def add_order_event(order_number, status, note=''):
    create_customer_experience_tables()
    now = israel_now_str() if 'israel_now_str' in globals() else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO order_events (order_number, status, note, created_at) VALUES (?, ?, ?, ?)", (order_number, status, note, now))
    conn.commit(); conn.close(); return True


def get_order_events(order_number):
    create_customer_experience_tables()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT status, note, created_at FROM order_events WHERE order_number = ? ORDER BY id ASC", (order_number,))
    rows = cur.fetchall(); conn.close()
    return [{'status': r[0], 'note': r[1], 'created_at': r[2]} for r in rows]


# ---------- Loyalty ----------
def add_loyalty_points(telegram_id, order_total):
    create_customer_experience_tables()
    points = int(float(order_total) // 10)  # כל 10₪ = נקודה אחת
    now = israel_now_str() if 'israel_now_str' in globals() else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO loyalty_points (telegram_id, points, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            points = points + excluded.points,
            updated_at = excluded.updated_at
    """, (int(telegram_id), points, now))
    conn.commit(); conn.close(); return points


def get_loyalty_points(telegram_id):
    create_customer_experience_tables()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT points FROM loyalty_points WHERE telegram_id = ?", (int(telegram_id),))
    row = cur.fetchone(); conn.close()
    return int(row[0]) if row else 0


# ---------- Abandoned Carts ----------
def save_abandoned_cart(telegram_id, cart, total):
    create_customer_experience_tables()
    now = israel_now_str() if 'israel_now_str' in globals() else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO abandoned_carts (telegram_id, cart_json, last_total, reminder_sent, updated_at)
        VALUES (?, ?, ?, 0, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            cart_json = excluded.cart_json,
            last_total = excluded.last_total,
            reminder_sent = 0,
            updated_at = excluded.updated_at
    """, (int(telegram_id), json.dumps(cart, ensure_ascii=False), float(total), now))
    conn.commit(); conn.close(); return True


def clear_abandoned_cart(telegram_id):
    create_customer_experience_tables()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM abandoned_carts WHERE telegram_id = ?", (int(telegram_id),))
    conn.commit(); conn.close(); return True

# ================== SAVED ADDRESSES ==================
def create_customer_addresses_table():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            label TEXT DEFAULT 'כתובת',
            city TEXT NOT NULL,
            street TEXT NOT NULL,
            floor TEXT DEFAULT '',
            apartment TEXT DEFAULT '',
            is_default INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_customer_address(telegram_id, label, city, street, floor="", apartment="", is_default=0):
    create_customer_addresses_table()

    now = israel_now_str() if "israel_now_str" in globals() else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cur = conn.cursor()

    if int(is_default) == 1:
        cur.execute(
            "UPDATE customer_addresses SET is_default = 0 WHERE telegram_id = ?",
            (int(telegram_id),)
        )

    cur.execute("""
        INSERT INTO customer_addresses (
            telegram_id, label, city, street, floor, apartment,
            is_default, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        int(telegram_id), label, city, street, floor, apartment,
        int(is_default), now, now
    ))

    conn.commit()
    address_id = cur.lastrowid
    conn.close()

    return address_id


def get_customer_addresses(telegram_id, limit=10):
    create_customer_addresses_table()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, telegram_id, label, city, street, floor, apartment,
               is_default, created_at, updated_at
        FROM customer_addresses
        WHERE telegram_id = ?
        ORDER BY is_default DESC, id DESC
        LIMIT ?
    """, (int(telegram_id), int(limit)))

    rows = cur.fetchall()
    conn.close()

    addresses = []

    for row in rows:
        (
            address_id, telegram_id, label, city, street, floor, apartment,
            is_default, created_at, updated_at
        ) = row

        addresses.append({
            "id": address_id,
            "telegram_id": telegram_id,
            "label": label,
            "city": city,
            "street": street,
            "floor": floor,
            "apartment": apartment,
            "is_default": is_default,
            "created_at": created_at,
            "updated_at": updated_at
        })

    return addresses


def get_customer_address_by_id(telegram_id, address_id):
    create_customer_addresses_table()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, telegram_id, label, city, street, floor, apartment,
               is_default, created_at, updated_at
        FROM customer_addresses
        WHERE telegram_id = ? AND id = ?
    """, (int(telegram_id), int(address_id)))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    (
        address_id, telegram_id, label, city, street, floor, apartment,
        is_default, created_at, updated_at
    ) = row

    return {
        "id": address_id,
        "telegram_id": telegram_id,
        "label": label,
        "city": city,
        "street": street,
        "floor": floor,
        "apartment": apartment,
        "is_default": is_default,
        "created_at": created_at,
        "updated_at": updated_at
    }


def delete_customer_address(telegram_id, address_id):
    create_customer_addresses_table()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM customer_addresses WHERE telegram_id = ? AND id = ?",
        (int(telegram_id), int(address_id))
    )

    conn.commit()
    changed = cur.rowcount
    conn.close()

    return changed > 0

