import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

FONT_PATH = "fonts/DejaVuSans.ttf"

pdfmetrics.registerFont(TTFont("Hebrew", FONT_PATH))


def rtl(text):
    return text[::-1]


def create_invoice_pdf(order):
    file_path = f"/tmp/{order['order_number']}.pdf"

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    c.setFont("Hebrew", 20)
    y = height - 50

    c.drawRightString(550, y, rtl("Vendora Shop חשבונית"))
    y -= 40

    c.setFont("Hebrew", 12)

    c.drawRightString(550, y, rtl(f"מספר הזמנה: {order['order_number']}"))
    y -= 25

    c.drawRightString(550, y, rtl(f"שם לקוח: {order['customer_name']}"))
    y -= 25

    c.drawRightString(550, y, rtl(f"טלפון: {order['phone']}"))
    y -= 25

    c.drawRightString(550, y, rtl(f"כתובת: {order['address']}"))
    y -= 35

    c.drawRightString(550, y, rtl("מוצרים:"))
    y -= 25

    for item in order["cart"]:
        line = f"{item['name']} x {item['qty']} = ₪{item['price'] * item['qty']}"
        c.drawRightString(550, y, rtl(line))
        y -= 22

    y -= 15

    c.drawRightString(550, y, rtl(f"סהכ מוצרים: ₪{order['products_total']}"))
    y -= 25

    c.drawRightString(550, y, rtl(f"משלוח: ₪{order['delivery_price']}"))
    y -= 25

    c.drawRightString(550, y, rtl(f"סהכ לתשלום: ₪{order['final_total']}"))
    y -= 40

    c.drawRightString(550, y, rtl("תודה שקנית אצל Vendora"))

    c.save()
    return file_path
