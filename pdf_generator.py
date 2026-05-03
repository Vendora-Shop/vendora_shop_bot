import os
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from bidi.algorithm import get_display

FONT_PATH = "fonts/DejaVuSans.ttf"
LOGO_PATH = "assets/logo.jpg"


def rtl(txt):
    return get_display(str(txt))


def money(x):
    x = float(x)
    if x.is_integer():
        return f"₪{int(x)}"
    return f"₪{x:.2f}"


def create_invoice_pdf(order):
    width, height = 1240, 1754
    img = Image.new("RGB", (width, height), "black")
    draw = ImageDraw.Draw(img)

    green = "#98ff00"
    white = "white"
    gray = "#cccccc"

    title_font = ImageFont.truetype(FONT_PATH, 56)
    font = ImageFont.truetype(FONT_PATH, 34)
    small = ImageFont.truetype(FONT_PATH, 26)
    big = ImageFont.truetype(FONT_PATH, 48)

    # logo
    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGB")
        logo.thumbnail((230, 230))
        img.paste(logo, (960, 30))

    # title
    draw.text((60, 70), "Vendora Shop", font=title_font, fill=white)
    draw.text((60, 145), "VIP Invoice", font=small, fill=green)

    # line
    draw.line((50, 260, 1190, 260), fill=green, width=2)

    y = 320

    # order details
    details = [
        f"מספר הזמנה: {order['order_number']}",
        f"שם לקוח: {order['customer_name']}",
        f"טלפון: {order['phone']}",
        f"כתובת: {order['address']}",
    ]

    for row in details:
        draw.text((1130, y), rtl(row), font=font, fill=white, anchor="ra")
        y += 55

    y += 20
    draw.line((50, y, 1190, y), fill=green, width=2)
    y += 40

    draw.text((1130, y), rtl("מוצרים"), font=big, fill=green, anchor="ra")
    y += 70

    # products
    for item in order["cart"]:
        name = item["name"]
        qty = item["qty"]
        price = float(item["price"])
        total = qty * price

        row = f"{name} | כמות: {qty} | {money(total)}"
        draw.text((1130, y), rtl(row), font=font, fill=white, anchor="ra")
        y += 55

    y += 20
    draw.line((50, y, 1190, y), fill=green, width=2)
    y += 50

    draw.text((1130, y), rtl(f"סה״כ מוצרים: {money(order['products_total'])}"),
              font=font, fill=white, anchor="ra")
    y += 55

    draw.text((1130, y), rtl(f"משלוח: {money(order['delivery_price'])}"),
              font=font, fill=white, anchor="ra")
    y += 80

    # final box
    draw.rectangle((70, y, 1170, y + 110), outline=green, width=3)
    draw.text((1120, y + 32),
              rtl(f"סה״כ לתשלום: {money(order['final_total'])}"),
              font=big, fill=green, anchor="ra")

    y += 180

    draw.text((1130, y), rtl("תודה שקנית אצל Vendora Shop"),
              font=small, fill=gray, anchor="ra")

    # save image
    img_path = f"/tmp/{order['order_number']}.png"
    pdf_path = f"/tmp/{order['order_number']}.pdf"

    img.save(img_path)

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawImage(img_path, 0, 0, width=A4[0], height=A4[1])
    c.save()

    return pdf_path
