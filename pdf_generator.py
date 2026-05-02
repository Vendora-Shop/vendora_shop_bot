import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

try:
    from bidi.algorithm import get_display
except Exception:
    get_display = None


FONT_NAME = "VendoraHebrew"


def find_font():
    possible_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansHebrew-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansHebrew-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    ]

    for font_path in possible_fonts:
        if os.path.exists(font_path):
            return font_path

    for root, dirs, files in os.walk("/usr/share/fonts"):
        for file in files:
            if file.lower().endswith((".ttf", ".otf")):
                return os.path.join(root, file)

    return None


def setup_font():
    font_path = find_font()

    if not font_path:
        raise Exception("לא נמצא פונט עברי בשרת. צריך להתקין או להוסיף פונט Unicode.")

    pdfmetrics.registerFont(TTFont(FONT_NAME, font_path))
    return FONT_NAME


def rtl(text):
    text = str(text)

    if get_display:
        return get_display(text)

    return text[::-1]


def money(value):
    return f"₪{float(value):g}"


def draw_right(c, x, y, text, font, size=11, color=colors.black):
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawRightString(x, y, rtl(text))


def create_invoice_pdf(order):
    font = setup_font()

    os.makedirs("/tmp", exist_ok=True)
    file_name = f"/tmp/{order['order_number']}.pdf"

    c = canvas.Canvas(file_name, pagesize=A4)
    width, height = A4

    right = width - 40
    left = 40
    y = height - 45

    c.setTitle(f"סיכום הזמנה {order['order_number']}")

    c.setFillColor(colors.HexColor("#2E7D32"))
    c.rect(0, height - 90, width, 90, fill=1, stroke=0)

    draw_right(c, right, height - 38, "Vendora Shop", font, 22, colors.white)
    draw_right(c, right, height - 68, "סיכום הזמנה", font, 13, colors.white)

    y = height - 125

    draw_right(c, right, y, f"מספר הזמנה: {order['order_number']}", font, 15)
    y -= 28

    draw_right(c, right, y, f"שם לקוח: {order['customer_name']}", font, 12)
    y -= 22
    draw_right(c, right, y, f"טלפון: {order['phone']}", font, 12)
    y -= 22
    draw_right(c, right, y, f"כתובת: {order['address']}", font, 12)
    y -= 35

    draw_right(c, right, y, "פרטי מוצרים", font, 14, colors.HexColor("#2E7D32"))
    y -= 24

    for item in order["cart"]:
        name = item.get("name", "")
        qty = int(item.get("qty", 0))
        price = float(item.get("price", 0))
        total = price * qty

        line = f"{name} × {qty} = {money(total)}"
        draw_right(c, right, y, line, font, 11)
        y -= 20

    y -= 10
    c.setStrokeColor(colors.HexColor("#333333"))
    c.line(left, y, right, y)
    y -= 30

    draw_right(c, right, y, f"סה״כ מוצרים: {money(order['products_total'])}", font, 12)
    y -= 22
    draw_right(c, right, y, f"דמי משלוח: {money(order['delivery_price'])}", font, 12)
    y -= 25

    draw_right(c, right, y, f"סה״כ לתשלום: {money(order['final_total'])}", font, 15, colors.HexColor("#2E7D32"))
    y -= 45

    draw_right(c, right, y, "המסמך מהווה סיכום הזמנה בלבד.", font, 10)
    y -= 18
    draw_right(c, right, y, "התשלום יתבצע לאחר אישור נציג.", font, 10)
    y -= 22
    draw_right(c, right, y, "תודה שקנית ב־Vendora Shop", font, 11, colors.HexColor("#2E7D32"))

    c.save()
    return file_name
    
