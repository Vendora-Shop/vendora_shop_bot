from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
import os


FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
]

FONT_NAME = "HebrewFont"


def register_font():
    for path in FONT_PATHS:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(FONT_NAME, path))
            return FONT_NAME
    return "Helvetica"


def rtl(text):
    text = str(text)
    try:
        from bidi.algorithm import get_display
        return get_display(text)
    except Exception:
        return text[::-1]


def money(value):
    return f"₪{float(value):g}"


def create_invoice_pdf(order):
    font = register_font()
    file_name = f"/tmp/{order['order_number']}.pdf"

    c = canvas.Canvas(file_name, pagesize=A4)
    width, height = A4

    right = width - 40
    left = 40
    y = height - 45

    c.setFillColor(colors.HexColor("#2E7D32"))
    c.rect(0, height - 90, width, 90, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont(font, 22)
    c.drawRightString(right, height - 45, rtl("Vendora Shop"))

    c.setFont(font, 12)
    c.drawRightString(right, height - 70, rtl("סיכום הזמנה / חשבונית עסקה"))

    y = height - 125
    c.setFillColor(colors.black)
    c.setFont(font, 15)
    c.drawRightString(right, y, rtl(f"מספר הזמנה: {order['order_number']}"))
    y -= 28

    c.setFont(font, 12)
    c.drawRightString(right, y, rtl(f"שם לקוח: {order['customer_name']}"))
    y -= 22
    c.drawRightString(right, y, rtl(f"טלפון: {order['phone']}"))
    y -= 22
    c.drawRightString(right, y, rtl(f"כתובת: {order['address']}"))
    y -= 35

    c.setFont(font, 14)
    c.setFillColor(colors.HexColor("#2E7D32"))
    c.drawRightString(right, y, rtl("פרטי מוצרים"))
    y -= 20

    c.setFillColor(colors.black)
    c.setFont(font, 11)

    for item in order["cart"]:
        total = float(item["price"]) * int(item["qty"])
        line = f"{item['name']} × {item['qty']} = {money(total)}"
        c.drawRightString(right, y, rtl(line))
        y -= 20

    y -= 15
    c.line(left, y, right, y)
    y -= 28

    c.setFont(font, 12)
    c.drawRightString(right, y, rtl(f"סה״כ מוצרים: {money(order['products_total'])}"))
    y -= 22
    c.drawRightString(right, y, rtl(f"דמי משלוח: {money(order['delivery_price'])}"))
    y -= 22

    c.setFont(font, 15)
    c.setFillColor(colors.HexColor("#2E7D32"))
    c.drawRightString(right, y, rtl(f"סה״כ לתשלום: {money(order['final_total'])}"))
    y -= 40

    c.setFillColor(colors.black)
    c.setFont(font, 10)
    c.drawRightString(right, y, rtl("המסמך מהווה סיכום הזמנה בלבד. התשלום יתבצע לאחר אישור נציג."))
    y -= 18
    c.drawRightString(right, y, rtl("תודה שקנית ב־Vendora Shop"))

    c.save()
    return file_name
