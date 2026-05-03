import os
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from bidi.algorithm import get_display

FONT_PATH = "fonts/DejaVuSans.ttf"


def rtl(t):
    return get_display(str(t))


def create_invoice_pdf(order):
    img_path = f"/tmp/{order['order_number']}.png"
    pdf_path = f"/tmp/{order['order_number']}.pdf"

    img = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(img)

    title_font = ImageFont.truetype(FONT_PATH, 42)
    font = ImageFont.truetype(FONT_PATH, 28)

    y = 60

    lines = [
        "חשבונית Vendora Shop",
        "",
        f"מספר הזמנה: {order['order_number']}",
        f"שם לקוח: {order['customer_name']}",
        f"טלפון: {order['phone']}",
        f"כתובת: {order['address']}",
        "",
        "מוצרים:"
    ]

    for item in order["cart"]:
        lines.append(f"{item['name']} | כמות {item['qty']} | ₪{item['price'] * item['qty']}")

    lines += [
        "",
        f"סהכ מוצרים: ₪{order['products_total']}",
        f"משלוח: ₪{order['delivery_price']}",
        f"סהכ לתשלום: ₪{order['final_total']}",
        "",
        "תודה שקנית אצל Vendora Shop"
    ]

    for i, line in enumerate(lines):
        f = title_font if i == 0 else font
        draw.text((1150, y), rtl(line), font=f, fill="black", anchor="ra")
        y += 55

    img.save(img_path)

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawImage(img_path, 0, 0, width=A4[0], height=A4[1])
    c.save()

    return pdf_path
