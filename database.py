import sqlite3

DB_PATH = "vendora_shop.db"


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

    # מוסיף עמודות אם הטבלה כבר קיימת מגרסה ישנה
    existing_columns = [row[1] for row in cur.execute("PRAGMA table_info(products)").fetchall()]

    columns_to_add = {
        "stock": "INTEGER DEFAULT 0",
        "sku": "TEXT DEFAULT ''",
        "image_file_id": "TEXT DEFAULT ''"
    }

    for column, column_type in columns_to_add.items():
        if column not in existing_columns:
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
        WHERE active = 1 AND stock > 0
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
