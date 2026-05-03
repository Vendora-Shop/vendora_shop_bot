import os
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from bidi.algorithm import get_display

FONT_PATH = "fonts/DejaVuSans.ttf"
LOGO_PATH = "assets/logo.jpg"


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

    W, H = 1240, 1754
    img = Image.new("RGB", (W, H), "#050505")
    draw = ImageDraw.Draw(img)

    green = "#9CFF2E"
    white = "#FFFFFF"
    gray = "#CFCFCF"
    dark = "#101010"
    line_green = "#7ED321"

    title_font = ImageFont.truetype(FONT_PATH, 64)
    section_font = ImageFont.truetype(FONT_PATH, 56)
    details_font = ImageFont.truetype(FONT_PATH, 48)
    product_font = ImageFont.truetype(FONT_PATH, 38)
    small_font = ImageFont.truetype(FONT_PATH, 30)
    total_font = ImageFont.truetype(FONT_PATH, 64)

    # Header clean area
    draw.rectangle((0, 0, W, 360), fill="#000000")

    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGB")
        logo.thumbnail((300, 300))
        img.paste(logo, (W - 365, 35))

    # Green divider under logo, not touching it
    draw.line((55, 340, W - 55, 340), fill=green, width=4)

    # Customer details box
    y = 405
    box_top = y - 35
    box_bottom = y + 355

    draw.rectangle(
        (55, box_top, W - 55, box_bottom),
        fill=dark,
        outline=green,
        width=4
    )

    details = [
        f"מספר הזמנה: {order['order_number']}",
        f"שם לקוח: {order['customer_name']}",
        f"טלפון: {order['phone']}",
        f"כתובת: {order['address']}",
    ]

    for row in details:
        draw.text(
            (W - 95, y),
            rtl(row),
            font=details_font,
            fill=white,
            anchor="ra"
        )
        y += 80

    y = box_bottom + 45

    # Products title
    draw.text(
        (W - 80, y),
        rtl("פרטי מוצרים"),
        font=section_font,
        fill=green,
        anchor="ra"
    )
    y += 75

    # Table header
    draw.rectangle((55, y - 20, W - 55, y + 80), fill=dark, outline=green, width=3)
    draw.text((W - 95, y + 30), rtl("מוצר"), font=small_font, fill=green, anchor="ra")
    draw.text((430, y + 30), rtl("כמות"), font=small_font, fill=green, anchor="mm")
    draw.text((180, y + 30), rtl("סה״כ"), font=small_font, fill=green, anchor="mm")
    y += 120

    # Product rows
    for item in order["cart"]:
        name = item["name"]
        qty = int(item["qty"])
        price = float(item["price"])
        total = price * qty

        draw.rectangle((55, y - 15, W - 55, y + 80), fill="#0B0B0B", outline="#263A16", width=2)
        draw.text((W - 95, y + 30), rtl(name), font=product_font, fill=white, anchor="ra")
        draw.text((430, y + 30), str(qty), font=product_font, fill=white, anchor="mm")
        draw.text((180, y + 30), money(total), font=product_font, fill=white, anchor="mm")
        y += 110

    y += 35
    draw.line((55, y, W - 55, y), fill=line_green, width=4)
    y += 70

    # Summary
    draw.text(
        (W - 95, y),
        rtl(f"סה״כ מוצרים: {money(order['products_total'])}"),
        font=details_font,
        fill=white,
        anchor="ra"
    )
    y += 70

    draw.text(
        (W - 95, y),
        rtl(f"דמי משלוח: {money(order['delivery_price'])}"),
        font=details_font,
        fill=white,
        anchor="ra"
    )
    y += 100

    # Final total box
    draw.rectangle((55, y - 25, W - 55, y + 125), fill="#071007", outline=green, width=6)
    draw.text(
        (W - 95, y + 48),
        rtl(f"סה״כ לתשלום: {money(order['final_total'])}"),
        font=total_font,
        fill=green,
        anchor="ra"
    )

    y += 200

    # Notes
    draw.text((W - 95, y), rtl("המסמך מהווה סיכום הזמנה בלבד."), font=small_font, fill=gray, anchor="ra")
    y += 45
    draw.text((W - 95, y), rtl("התשלום יתבצע לאחר אישור נציג."), font=small_font, fill=gray, anchor="ra")

    # Footer
    draw.line((55, H - 150, W - 55, H - 150), fill="#222222", width=2)
    draw.text((W - 95, H - 105), rtl("תודה שקנית ב VENDORA"), font=small_font, fill=white, anchor="ra")
    draw.text((70, H - 105), "Vendora Shop ©", font=small_font, fill=green)

    img.save(img_path, "PNG")

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawImage(img_path, 0, 0, width=A4[0], height=A4[1])
    c.save()

    return pdf_path
