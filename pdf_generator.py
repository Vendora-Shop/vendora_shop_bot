import os
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from bidi.algorithm import get_display

FONT_PATH = "fonts/David.ttf"
LOGO_PATH = "assets/logo.jpg"


def rtl(text):
    return get_display(str(text), base_dir="R")


def draw_rtl(draw, x, y, text, font, fill, anchor="ra"):
    draw.text((x, y), rtl(text), font=font, fill=fill, anchor=anchor)


def money_value(value):
    value = float(value)
    return str(int(value)) if value.is_integer() else f"{value:g}"


def draw_money(draw, x, y, value, number_font, shekel_font, fill):
    """
    מצייר מחיר בצורה מקצועית:
    מספר גדול + ₪ קטן מימין למספר
    """
    number = money_value(value)
    draw.text((x, y), number, font=number_font, fill=fill, anchor="rm")
    draw.text((x + 10, y + 3), "₪", font=shekel_font, fill=fill, anchor="lm")


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
    border_dark = "#1E3510"

    # פונט David לכל המסמך
    title_font = ImageFont.truetype(FONT_PATH, 62)
    slogan_font = ImageFont.truetype(FONT_PATH, 42)

    label_font = ImageFont.truetype(FONT_PATH, 42)
    value_font = ImageFont.truetype(FONT_PATH, 42)

    section_font = ImageFont.truetype(FONT_PATH, 52)

    table_header_font = ImageFont.truetype(FONT_PATH, 36)
    table_font = ImageFont.truetype(FONT_PATH, 36)

    price_font = ImageFont.truetype(FONT_PATH, 36)
    shekel_font = ImageFont.truetype(FONT_PATH, 23)

    total_label_font = ImageFont.truetype(FONT_PATH, 62)
    total_number_font = ImageFont.truetype(FONT_PATH, 78)
    total_shekel_font = ImageFont.truetype(FONT_PATH, 44)

    note_font = ImageFont.truetype(FONT_PATH, 28)

    # HEADER
    draw.rectangle((0, 0, W, 260), fill="#000000")

    draw.text((70, 62), "VENDORA", font=title_font, fill=white)
    draw_rtl(draw, 70, 150, "חנות אספקה חכמה", slogan_font, green, anchor="la")

    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGB")
        logo.thumbnail((185, 185))
        img.paste(logo, (W - 265, 38))

    draw.line((55, 265, W - 55, 265), fill=green, width=4)

    # CUSTOMER DETAILS
    y = 325
    details_box_h = 315
    draw.rectangle((55, y, W - 55, y + details_box_h), fill=dark, outline=green, width=4)

    details = [
        ("מספר הזמנה", order["order_number"]),
        ("שם לקוח", order["customer_name"]),
        ("טלפון", order["phone"]),
        ("כתובת", order["address"]),
    ]

    row_y = y + 58
    for label, value in details:
        draw_rtl(draw, W - 95, row_y, f"{label}:", label_font, green)
        draw_rtl(draw, W - 430, row_y, value, value_font, white)
        row_y += 72

    # PRODUCTS TITLE
    y = 705
    draw_rtl(draw, W - 70, y, "פרטי מוצרים", section_font, green)
    y += 75

    # TABLE HEADER
    table_x1 = 55
    table_x2 = W - 55
    header_h = 76

    draw.rectangle((table_x1, y, table_x2, y + header_h), fill=dark, outline=green, width=3)

    # מיקומים מדויקים — מוצר לא נוגע במסגרת
    product_x = W - 100
    qty_x = 430
    price_x = 265
    total_x = 115

    header_text_y = y + 48

    draw_rtl(draw, product_x, header_text_y, "מוצר", table_header_font, green)
    draw.text((qty_x, header_text_y - 2), rtl("כמות"), font=table_header_font, fill=green, anchor="mm")
    draw.text((price_x, header_text_y - 2), rtl("מחיר"), font=table_header_font, fill=green, anchor="mm")
    draw.text((total_x, header_text_y - 2), rtl("סה״כ"), font=table_header_font, fill=green, anchor="mm")

    y += header_h + 12

    # PRODUCT ROWS
    for item in order["cart"]:
        name = item["name"]
        qty = int(item["qty"])
        price = float(item["price"])
        total = price * qty

        row_h = 78
        draw.rectangle((table_x1, y, table_x2, y + row_h), fill=row_dark, outline=border_dark, width=2)

        text_y = y + 50

        draw_rtl(draw, product_x, text_y, name, table_font, white)
        draw.text((qty_x, text_y - 2), str(qty), font=table_font, fill=white, anchor="mm")

        draw_money(draw, price_x + 35, text_y - 1, price, price_font, shekel_font, white)
        draw_money(draw, total_x + 35, text_y - 1, total, price_font, shekel_font, white)

        y += row_h + 10

    # SUMMARY
    y += 30
    draw.line((55, y, W - 55, y), fill=green, width=4)
    y += 65

    summary_rows = [
        ("סה״כ מוצרים", order["products_total"]),
        ("דמי משלוח", order["delivery_price"]),
    ]

    for label, value in summary_rows:
        draw_rtl(draw, W - 95, y, f"{label}:", label_font, green)
        draw_money(draw, 430, y + 2, value, value_font, shekel_font, white)
        y += 65

    # FINAL TOTAL BOX
    y += 28
    total_box_h = 145
    draw.rectangle((55, y, W - 55, y + total_box_h), fill="#071007", outline=green, width=6)

    draw_rtl(draw, W - 95, y + 88, "סה״כ לתשלום:", total_label_font, green)
    draw_money(draw, 385, y + 88, order["final_total"], total_number_font, total_shekel_font, green)

    # NOTES
    y += 205
    draw_rtl(draw, W - 95, y, "המסמך מהווה סיכום הזמנה בלבד.", note_font, gray)
    y += 38
    draw_rtl(draw, W - 95, y, "התשלום יתבצע לאחר אישור נציג.", note_font, gray)

    # FOOTER
    draw.line((55, H - 150, W - 55, H - 150), fill="#222222", width=2)
    draw.text((70, H - 105), "Vendora Shop ©", font=note_font, fill=green)
    draw_rtl(draw, W - 95, H - 105, "תודה שקנית ב Vendora", note_font, white)

    img.save(img_path, "PNG")

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawImage(img_path, 0, 0, width=A4[0], height=A4[1])
    c.save()

    return pdf_path
