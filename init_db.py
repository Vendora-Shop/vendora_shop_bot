from database import create_tables, add_product

create_tables()

add_product(
    category="📦 מוצרי הובלות ואריזה",
    name="קרטונים",
    price=8,
    description="קרטון איכותי למעבר דירה",
    max_qty=100
)

add_product(
    category="🎒 ציוד לשליחים",
    name="תיק משלוחים גדול",
    price=180,
    description="תיק תרמי גדול לשליחים",
    max_qty=10
)

print("Database initialized successfully")
