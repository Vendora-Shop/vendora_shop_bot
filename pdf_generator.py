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
        return f"{int(value)}₪"
    return f"{value:g}₪"


def draw_rtl(draw, x, y, text, font, fill, anchor="ra"):
    draw.text((x, y), rtl(text), font=font, fill=fill, anchor=anchor)


def create_invoice_pdf(order):
    img_path = f"/tmp/{order['order_number']}.png"
    pdf_path = f"/tmp/{order['order_number']}.pdf"

    W, H = 1240, 1754
    img = Image.new("RGB", (W, H), "#050505")
    draw = ImageDraw.Draw(img)

    green = "#9CFF2E"
    white = "#FFFFFF"
    gray = "#D6D6D6"
    dark = "#101010"
    dark2 = "#0B0B0B"
    muted_green = "#263A16"

    title_font = ImageFont.truetype(FONT_PATH, 56)
    label_font = ImageFont.truetype(FONT_PATH, 40)
    text_font = ImageFont.truetype(FONT_PATH, 40)
    section_font = ImageFont.truetype(FONT_PATH, 48)
    table_font = ImageFont.truetype(FONT_PATH, 32)
    total_font = ImageFont.truetype(FONT_PATH, 58)
    note_font = ImageFont.truetype(FONT_PATH, 26)

    # Header
    draw.rectangle((0, 0, W, 330), fill="#000000")

    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGB")
        logo.thumbnail((280, 280))
        img.paste(logo, (W - 350, 35))

    draw.line((55, 315, W - 55, 315), fill=green, width=4)

    # Details box
    y = 375
    box_top = y - 25
    box_bottom = y + 335
    draw.rectangle((55, box_top, W - 55, box_bottom), fill=dark, outline=green, width=4)

    details = [
        ("מספר הזמנה", order["order_number"]),
        ("שם לקוח", order["customer_name"]),
        ("טלפון", order["phone"]),
        ("כתובת", order["address"]),
    ]

    label_x = W - 95
    value_x = W - 420

    for label, value in details:
        draw_rtl(draw, label_x, y, f"{label}:", label_font, green)
        draw_rtl(draw, value_x, y, value, text_font, white)
        y += 78

    # Products title
    y = box_bottom + 55
    draw_rtl(draw, W - 80, y, "פרטי מוצרים", section_font, green)
    y += 70

    # Table header
    draw.rectangle((55, y - 15, W - 55, y + 75), fill=dark, outline=green, width=3)
    draw_rtl(draw, W - 95, y + 30, "מוצר", table_font, green)
    draw.text((430, y + 30), rtl("כמות"), font=table_font, fill=green, anchor="mm")
    draw.text((175, y + 30), rtl("סה״כ"), font=table_font, fill=green, anchor="mm")
    y += 110

    # Product rows
    for item in order["cart"]:
        name = item["name"]
        qty = int(item["qty"])
        price = float(item["price"])
        total = price * qty

        draw.rectangle((55, y - 15, W - 55, y + 75), fill=dark2, outline=muted_green, width=2)

        draw_rtl(draw, W - 95, y + 30, name, table_font, white)
        draw.text((430, y + 30), str(qty), font=table_font, fill=white, anchor="mm")
        draw.text((175, y + 30), money(total), font=table_font, fill=white, anchor="mm")

        y += 100

    y += 25
    draw.line((55, y, W - 55, y), fill=green, width=4)
    y += 60

    # Summary rows
    summary_label_x = W - 95
    summary_value_x = W - 480

    summary_rows = [
        ("סה״כ מוצרים", money(order["products_total"])),
        ("דמי משלוח", money(order["delivery_price"])),
    ]

    for label, value in summary_rows:
        draw_rtl(draw, summary_label_x, y, f"{label}:", label_font, green)
        draw_rtl(draw, summary_value_x, y, value, text_font, white)
        y += 65

    y += 30

    # Final total box
    draw.rectangle((55, y - 20, W - 55, y + 125), fill="#071007", outline=green, width=6)
    draw_rtl(draw, W - 95, y + 50, "סה״כ לתשלום:", total_font, green)
    draw.text((365, y + 50), money(order["final_total"]), font=total_font, fill=green, anchor="mm")

    y += 175

    # Notes
    draw_rtl(draw, W - 95, y, "המסמך מהווה סיכום הזמנה בלבד.", note_font, gray)
    y += 38
    draw_rtl(draw, W - 95, y, "התשלום יתבצע לאחר אישור נציג.", note_font, gray)

    # Footer
    draw.line((55, H - 150, W - 55, H - 150), fill="#222222", width=2)
    draw_rtl(draw, W - 95, H - 105, "תודה שקנית ב Vendora", note_font, white)
    draw.text((70, H - 105), "Vendora Shop ©", font=note_font, fill=green)

    img.save(img_path, "PNG")

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawImage(img_path, 0, 0, width=A4[0], height=A4[1])
    c.save()

    return pdf_path
