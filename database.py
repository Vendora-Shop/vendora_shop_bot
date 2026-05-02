import os
import json
import sqlite3
from datetime import datetime

DB_DIR = "/data"
LOCAL_DB = "vendora_shop.db"

try:
    os.makedirs(DB_DIR, exist_ok=True)
    test_path = os.path.join(DB_DIR, ".test")
    with open(test_path, "w") as f:
        f.write("ok")
    os.remove(test_path)
    DB_PATH = os.path.join(DB_DIR, "vendora_shop.db")
except Exception:
    DB_PATH = LOCAL_DB

print(f"Using database: {DB_PATH}")


def get_connection():
    return sqlite3.connect(DB_PATH)


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

    product_columns = [
        row[1] for row in cur.execute("PRAGMA table_info(products)").fetchall()
    ]

    product_columns_to_add = {
        "stock": "INTEGER DEFAULT 0",
        "sku": "TEXT DEFAULT ''",
        "image_file_id": "TEXT DEFAULT ''"
    }

    for column, column_type in product_columns_to_add.items():
        if column not in product_columns:
            cur.execute(f"ALTER TABLE products ADD COLUMN {column} {column_type}")

    conn.commit()
    conn.close()


def add_product(category, name, price, description="", max_qty=100, stock=0, sku="", image_file_id="", active=1):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO products
        (category, name, price, description, max_qty, stock, sku, image_file_id, active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        category,
        name,
        float(price),
        description,
        int(max_qty),
        int(stock),
        sku,
        image_file_id,
        int(active)
    ))

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
        cur.execute("""
            UPDATE products
            SET stock = stock - ?
            WHERE name = ? AND stock >= ?
        """, (int(item["qty"]), item["name"], int(item["qty"])))

        if cur.rowcount == 0:
            conn.rollback()
            conn.close()
            return False, item["name"]

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

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

    cur.execute("""
        UPDATE orders
        SET order_number = ?
        WHERE id = ?
    """, (order_number, order_id))

    conn.commit()
    conn.close()

    return order_number


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

    if not row:
        return None

    return order_row_to_dict(row)


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

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        UPDATE orders
        SET status = ?, updated_at = ?
        WHERE order_number = ?
    """, (status, now, order_number))

    conn.commit()
    changed = cur.rowcount
    conn.close()

    return changed > 0


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
