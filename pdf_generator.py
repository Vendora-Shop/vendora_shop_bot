from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors
import os

FONT_FILE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def register_font():
    pdfmetrics.registerFont(TTFont("DejaVu", FONT_FILE))


def heb(text):
    return str(text)[::-1]


def create_invoice_pdf(order):
    register_font()

    filename = f"/tmp/{order['order_number']}.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    c.setTitle(order["order_number"])
    c.setFont("DejaVu", 12)

    # Header
    c.setFillColor(colors.green)
    c.rect(0, height - 70, width, 70, fill=1)

    c.setFillColor(colors.white)
    c.setFont("DejaVu", 24)
    c.drawRightString(width - 40, height - 40, "Vendora Shop")

    y = height - 110
    c.setFillColor(colors.black)
    c.setFont("DejaVu", 14)

    c.drawRightString(width - 40, y, heb(f"מספר הזמנה: {order['order_number']}"))
    y -= 30
    c.drawRightString(width - 40, y, heb(f"שם: {order['customer_name']}"))
    y -= 25
    c.drawRightString(width - 40, y, heb(f"טלפון: {order['phone']}"))
    y -= 25
    c.drawRightString(width - 40, y, heb(f"כתובת: {order['address']}"))
    y -= 40

    c.setFillColor(colors.green)
    c.drawRightString(width - 40, y, heb("מוצרים"))
    y -= 25

    c.setFillColor(colors.black)

    for item in order["cart"]:
        line = f"{item['name']} x {item['qty']} = ₪{item['price'] * item['qty']}"
        c.drawRightString(width - 40, y, heb(line))
        y -= 22

    y -= 15
    c.line(40, y, width - 40, y)
    y -= 30

    c.drawRightString(width - 40, y, heb(f"סהכ מוצרים: ₪{order['products_total']}"))
    y -= 25
    c.drawRightString(width - 40, y, heb(f"משלוח: ₪{order['delivery_price']}"))
    y -= 25

    c.setFillColor(colors.green)
    c.setFont("DejaVu", 16)
    c.drawRightString(width - 40, y, heb(f"סהכ לתשלום: ₪{order['final_total']}"))

    y -= 50
    c.setFillColor(colors.black)
    c.setFont("DejaVu", 11)
    c.drawRightString(width - 40, y, heb("תודה שקנית ב Vendora"))

    c.save()
    return filename
