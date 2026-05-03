from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from bidi.algorithm import get_display
import os

FONT_PATH = "fonts/DejaVuSans.ttf"


def rtl(text):
    return get_display(str(text), base_dir="R")


def money(value):
    value = float(value)
    if value.is_integer():
        return f"₪{int(value)}"
    return f"₪{value:g}"


def create_invoice_pdf(order):
    img_path = f"/tmp/{order['order_number']}.png"
    pdf_path = f"/tmp/{order['order_number']}.pdf"

    img = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(img)

    title_font = ImageFont.truetype(FONT_PATH, 46)
    font = ImageFont.truetype(FONT_PATH, 30)
    small_font = ImageFont.truetype(FONT_PATH, 24)

    x = 1160
    y = 70

    draw.text((x, y), rtl("חשבונית Vendora Shop"), font=title_font, fill="black", anchor="ra")
    y += 90

    draw.text((x, y), rtl(f"מספר הזמנה: {order['order_number']}"), font=font, fill="black", anchor="ra")
    y += 50
    draw.text((x, y), rtl(f"שם לקוח: {order['customer_name']}"), font=font, fill="black", anchor="ra")
    y += 50
    draw.text((x, y), rtl(f"טלפון: {order['phone']}"), font=font, fill="black", anchor="ra")
    y += 50
    draw.text((x, y), rtl(f"כתובת: {order['address']}"), font=font, fill="black", anchor="ra")
    y += 80

    draw.text((x, y), rtl("מוצרים:"), font=font, fill="black", anchor="ra")
    y += 55

    for item in order["cart"]:
        name = item["name"]
        qty = int(item["qty"])
        price = float(item["price"])
        total = price * qty
        line = f"{name} | כמות: {qty} | סה״כ: {money(total)}"
        draw.text((x, y), rtl(line), font=small_font, fill="black", anchor="ra")
        y += 45

    y += 40
    draw.line((80, y, 1160, y), fill="black", width=2)
    y += 60

    draw.text((x, y), rtl(f"סה״כ מוצרים: {money(order['products_total'])}"), font=font, fill="black", anchor="ra")
    y += 50
    draw.text((x, y), rtl(f"דמי משלוח: {money(order['delivery_price'])}"), font=font, fill="black", anchor="ra")
    y += 50
    draw.text((x, y), rtl(f"סה״כ לתשלום: {money(order['final_total'])}"), font=title_font, fill="black", anchor="ra")
    y += 90

    draw.text((x, y), rtl("תודה שקנית אצל Vendora Shop"), font=font, fill="black", anchor="ra")

    img.save(img_path, "PNG")

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawImage(img_path, 0, 0, width=A4[0], height=A4[1])
    c.save()

    return pdf_path
