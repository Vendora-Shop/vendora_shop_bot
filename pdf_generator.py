import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

FONT_PATH = "fonts/DejaVuSans.ttf"
pdfmetrics.registerFont(TTFont("Hebrew", FONT_PATH))


def heb(text):
    return text[::-1]


def create_invoice_pdf(order):
    file_path = f"/tmp/{order['order_number']}.pdf"

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Hebrew", 22)
    c.drawRightString(550, y, heb("חשבונית Vendora Shop"))
    y -= 45

    c.setFont("Hebrew", 13)

    c.drawRightString(550, y, heb(f"מספר הזמנה: {order['order_number']}"))
    y -= 28

    c.drawRightString(550, y, heb(f"שם לקוח: {order['customer_name']}"))
    y -= 28

    c.drawRightString(550, y, heb(f"טלפון: {order['phone']}"))
    y -= 28

    c.drawRightString(550, y, heb(f"כתובת: {order['address']}"))
    y -= 35

    c.drawRightString(550, y, heb("מוצרים:"))
    y -= 28

    for item in order["cart"]:
        line = f"{item['name']} | {item['qty']} יח | ₪{item['price'] * item['qty']}"
        c.drawRightString(550, y, heb(line))
        y -= 24

    y -= 15

    c.drawRightString(550, y, heb(f"סהכ מוצרים: ₪{order['products_total']}"))
    y -= 25

    c.drawRightString(550, y, heb(f"משלוח: ₪{order['delivery_price']}"))
    y -= 25

    c.drawRightString(550, y, heb(f"סהכ לתשלום: ₪{order['final_total']}"))
    y -= 45

    c.drawRightString(550, y, heb("תודה שקנית אצל Vendora Shop"))

    c.save()
    return file_path
