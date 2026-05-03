from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from bidi.algorithm import get_display
import arabic_reshaper

FONT_PATH = "fonts/DejaVuSans.ttf"

pdfmetrics.registerFont(TTFont("Hebrew", FONT_PATH))


def rtl(text):
    text = str(text)
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def draw_rtl(c, y, text, size=14):
    c.setFont("Hebrew", size)
    c.drawRightString(560, y, rtl(text))


def create_invoice_pdf(order):
    file_name = f"{order['order_id']}.pdf"

    c = canvas.Canvas(file_name, pagesize=A4)
    w, h = A4

    y = h - 50

    draw_rtl(c, y, "חשבונית Vendora Shop", 22)
    y -= 50

    draw_rtl(c, y, f"מספר הזמנה: {order['order_id']}")
    y -= 30

    draw_rtl(c, y, f"שם לקוח: {order['name']}")
    y -= 30

    draw_rtl(c, y, f"טלפון: {order['phone']}")
    y -= 30

    draw_rtl(c, y, f"כתובת: {order['address']}")
    y -= 50

    draw_rtl(c, y, "מוצרים:")
    y -= 30

    for item in order["items"]:
        line = f"{item['name']} | כמות {int(item['qty'])} | ₪{int(item['price'])}"
        draw_rtl(c, y, line)
        y -= 25

    y -= 20

    draw_rtl(c, y, f"סהכ מוצרים: ₪{int(order['subtotal'])}")
    y -= 30

    draw_rtl(c, y, f"משלוח: ₪{int(order['delivery'])}")
    y -= 30

    draw_rtl(c, y, f"סהכ לתשלום: ₪{int(order['total'])}")
    y -= 50

    draw_rtl(c, y, "תודה שקנית אצל Vendora Shop")

    c.save()

    return file_name
