import os
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from bidi.algorithm import get_display

FONT_PATH = "fonts/DejaVuSans.ttf"
LOGO_PATH = "assets/logo.jpg"


def rtl(text):
    return get_display(str(text), base_dir="R")


def draw_rtl(draw, x, y, text, font, fill, anchor="ra"):
    draw.text((x, y), rtl(text), font=font, fill=fill, anchor=anchor)


def money_text(value):
    value = float(value)
    num = int(value) if value.is_integer() else value
    return f"{num} ₪"


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
    row_dark = "#080808"
    border_dark = "#1F3315"

    title_font = ImageFont.truetype(FONT_PATH, 46)
    label_font = ImageFont.truetype(FONT_PATH, 34)
    value_font = ImageFont.truetype(FONT_PATH, 34)
    address_font = ImageFont.truetype(FONT_PATH, 28)
    section_font = ImageFont.truetype(FONT_PATH, 44)
    table_font = ImageFont.truetype(FONT_PATH, 29)
    total_label_font = ImageFont.truetype(FONT_PATH, 46)
    total_font = ImageFont.truetype(FONT_PATH, 62)
    note_font = ImageFont.truetype(FONT_PATH, 26)

    # ===== HEADER =====
    draw.rectangle((0, 0, W, 260), fill="#000000")

    # לוגו גדול בצד שמאל למעלה — רק לוגו אחד
    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGB")
        logo.thumbnail((250, 250))
        img.paste(logo, (70, 25))

    draw.line((55, 265, W - 55, 265), fill=green, width=4)

    # ===== ORDER TITLE =====
    y = 320
    draw_rtl(draw, W - 70, y, "סיכום הזמנה", title_font, green)

    # ===== CUSTOMER DETAILS =====
    y = 385
    box_h = 315
    draw.rectangle((55, y, W - 55, y + box_h), fill=dark, outline=green, width=4)

    label_x = W - 95
    value_x = W - 430

    details = [
        ("מספר הזמנה", order["order_number"]),
        ("שם לקוח", order["customer_name"]),
        ("טלפון", order["phone"]),
    ]

    row_y = y + 60
    for label, value in details:
        draw_rtl(draw, label_x, row_y, f"{label}:", label_font, green)
        draw_rtl(draw, value_x, row_y, value, value_font, white)
        row_y += 68

    draw_rtl(draw, label_x, row_y, "כתובת:", label_font, green)
    draw_rtl(draw, value_x, row_y, order["address"], address_font, white)

    # ===== PRODUCTS TITLE =====
    y = 770
    draw_rtl(draw, W - 70, y, "פרטי מוצרים", section_font, green)
    y += 70

    # ===== TABLE =====
    table_x1, table_x2 = 55, W - 55
    product_x = W - 130
    qty_x = 450
    price_x = 265
    total_x = 110

    draw.rectangle((table_x1, y, table_x2, y + 76), fill=dark, outline=green, width=3)

    draw_rtl(draw, product_x, y + 50, "מוצר", table_font, green)
    draw.text((qty_x, y + 46), rtl("כמות"), font=table_font, fill=green, anchor="mm")
    draw.text((price_x, y + 46), rtl("מחיר"), font=table_font, fill=green, anchor="mm")
    draw.text((total_x, y + 46), rtl("סה״כ"), font=table_font, fill=green, anchor="mm")

    y += 88

    for item in order["cart"]:
        name = item["name"]
        qty = int(item["qty"])
        price = float(item["price"])
        total = price * qty

        draw.rectangle((table_x1, y, table_x2, y + 72), fill=row_dark, outline=border_dark, width=2)

        draw_rtl(draw, product_x, y + 44, name, table_font, white)
        draw.text((qty_x, y + 42), str(qty), font=table_font, fill=white, anchor="mm")
        draw.text((price_x, y + 42), money_text(price), font=table_font, fill=white, anchor="mm")
        draw.text((total_x, y + 42), money_text(total), font=table_font, fill=white, anchor="mm")

        y += 82

    # ===== SUMMARY =====
    y += 30
    draw.line((55, y, W - 55, y), fill=green, width=4)
    y += 65

    draw_rtl(draw, W - 95, y, "סה״כ מוצרים:", label_font, green)
    draw.text((365, y), money_text(order["products_total"]), font=value_font, fill=white, anchor="mm")

    y += 62

    draw_rtl(draw, W - 95, y, "דמי משלוח:", label_font, green)
    draw.text((365, y), money_text(order["delivery_price"]), font=value_font, fill=white, anchor="mm")

    # ===== FINAL TOTAL =====
    y += 95
    draw.rectangle((55, y, W - 55, y + 135), fill="#071007", outline=green, width=6)

    draw_rtl(draw, W - 95, y + 82, "סה״כ לתשלום:", total_label_font, green)
    draw.text((330, y + 78), money_text(order["final_total"]), font=total_font, fill=green, anchor="mm")

    # ===== NOTES =====
    y += 185
    draw_rtl(draw, W - 95, y, "המסמך מהווה סיכום הזמנה בלבד.", note_font, gray)
    y += 36
    draw_rtl(draw, W - 95, y, "התשלום יתבצע לאחר אישור נציג.", note_font, gray)

    # ===== FOOTER =====
    draw.line((55, H - 150, W - 55, H - 150), fill="#222222", width=2)
    draw.text((70, H - 105), "Vendora Shop ©", font=note_font, fill=green)
    draw_rtl(draw, W - 95, H - 105, "תודה שקנית ב Vendora", note_font, white)

    img.save(img_path, "PNG")

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawImage(img_path, 0, 0, width=A4[0], height=A4[1])
    c.save()

    return pdf_path
