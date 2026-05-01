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
            active INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()


def add_product(category, name, price, description="", max_qty=100, active=1):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO products 
        (category, name, price, description, max_qty, active)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (category, name, price, description, max_qty, active))

    conn.commit()
    conn.close()


def get_active_products():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT category, name, price, description, max_qty
        FROM products
        WHERE active = 1
        ORDER BY category, name
    """)

    rows = cur.fetchall()
    conn.close()

    products = {}

    for category, name, price, description, max_qty in rows:
        products.setdefault(category, []).append({
            "name": name,
            "price": price,
            "description": description,
            "max_qty": max_qty
        })

    return products


def get_all_products():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, category, name, price, description, max_qty, active
        FROM products
        ORDER BY category, name
    """)

    rows = cur.fetchall()
    conn.close()
    return rows


def set_product_price(name, price):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("UPDATE products SET price = ? WHERE name = ?", (price, name))

    conn.commit()
    changed = cur.rowcount
    conn.close()
    return changed > 0


def set_product_active(name, active):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("UPDATE products SET active = ? WHERE name = ?", (active, name))

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
