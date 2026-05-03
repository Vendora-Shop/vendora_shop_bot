import os
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from bidi.algorithm import get_display

FONT_PATH = "fonts/DejaVuSans.ttf"

LOGO_PATHS = [
    "assets/vendora_logo.jpg",
    "assets/vendora_logo.png",
    "vendora_logo.jpg",
]

BANNER_PATHS = [
    "assets/vendora_banner.jpg",
    "assets/vendora_banner.png",
    "vendora_banner.jpg",
]


def find_file(paths):
    for path in paths:
        if os.path.exists(path):
            return path
    return None


def rtl(text):
    return get_display(str(text), base_dir="R")


def money(value):
    value = float(value)
    if value.is_integer():
        return f"₪{int(value)}"
    return f"₪{value:g}"


def draw_rtl(draw, xy, text, font, fill="white", anchor="ra"):
    draw.text(xy, rtl(text), font=font, fill=fill, anchor=anchor)


def create_invoice_pdf(order):
    img_path = f"/tmp/{order['order_number']}.png"
    pdf_path = f"/tmp/{order['order_number']}.pdf"

    W, H = 1240, 1754
    img = Image.new("RGB", (W, H), "#070807")
    draw = ImageDraw.Draw(img)

    title_font = ImageFont.truetype(FONT_PATH, 58)
    big_font = ImageFont.truetype(FONT_PATH, 46)
    font = ImageFont.truetype(FONT_PATH, 32)
    small_font = ImageFont.truetype(FONT_PATH, 26)
    mini_font = ImageFont.truetype(FONT_PATH, 22)

    green = "#9EEA2D"
    white = "#FFFFFF"
    gray = "#D7D7D7"
    dark_box = "#111311"

    banner_path = find_file(BANNER_PATHS)
    if banner_path:
        banner = Image.open(banner_path).convert("RGB")
        banner = banner.resize((W, 310))
        img.paste(banner, (0, 0))
        draw.rectangle((0, 0, W, 310), outline=green, width=3)
    else:
        draw.rectangle((0, 0, W, 310), fill="#050505", outline=green, width=3)

    logo_path = find_file(LOGO_PATHS)
    if logo_path:
        logo = Image.open(logo_path).convert("RGB")
        logo.thumbnail((210, 210))
        img.paste(logo, (W - 250, 45))

    draw.text((80, 90), "Vendora Shop", font=title_font, fill=white)
    draw.text((80, 160), "Luxury Tech Invoice", font=small_font, fill=green)

    y = 360
    x_right = W - 80

    draw_rtl(draw, (x_right, y), f"מספר הזמנה: {order['order_number']}", big_font, green)
    y += 70

    draw.rectangle((60, y, W - 60, y + 250), fill=dark_box, outline=green, width=2)
    y += 45

    draw_rtl(draw, (x_right - 30, y), f"שם לקוח: {order['customer_name']}", font, white)
    y += 50
    draw_rtl(draw, (x_right - 30, y), f"טלפון: {order['phone']}", font, white)
    y += 50
    draw_rtl(draw, (x_right - 30, y), f"כתובת: {order['address']}", small_font, gray)
    y += 90

    draw_rtl(draw, (x_right, y), "פרטי מוצרים", big_font, green)
    y += 65

    draw.rectangle((60, y, W - 60, y + 70), fill="#1A1D18", outline=green, width=2)
    draw_rtl(draw, (x_right - 30, y + 45), "מוצר", small_font, green)
    draw.text((390, y + 18), "Qty", font=small_font, fill=green)
    draw.text((230, y + 18), "Total", font=small_font, fill=green)
    y += 95

    for item in order["cart"]:
        name = item["name"]
        qty = int(item["qty"])
        price = float(item["price"])
        total = price * qty

        draw.rectangle((60, y - 15, W - 60, y + 55), fill="#0D0F0D", outline="#29351E", width=1)
        draw_rtl(draw, (x_right - 30, y + 30), name, small_font, white)
        draw.text((405, y + 5), str(qty), font=small_font, fill=white)
        draw.text((205, y + 5), money(total), font=small_font, fill=white)
        y += 82

    y += 35
    draw.line((60, y, W - 60, y), fill=green, width=3)
    y += 55

    draw_rtl(draw, (x_right, y), f"סה״כ מוצרים: {money(order['products_total'])}", font, white)
    y += 50
    draw_rtl(draw, (x_right, y), f"דמי משלוח: {money(order['delivery_price'])}", font, white)
    y += 70

    draw.rectangle((60, y - 25, W - 60, y + 90), fill="#101510", outline=green, width=4)
    draw_rtl(draw, (x_right - 30, y + 45), f"סה״כ לתשלום: {money(order['final_total'])}", title_font, green)
    y += 150

    draw_rtl(draw, (x_right, y), "המסמך מהווה סיכום הזמנה בלבד.", mini_font, gray)
    y += 35
    draw_rtl(draw, (x_right, y), "התשלום יתבצע לאחר אישור נציג.", mini_font, gray)
    y += 55
    draw.text((80, H - 90), "Vendora Shop ©", font=small_font, fill=green)
    draw_rtl(draw, (x_right, H - 80), "תודה שקנית אצל Vendora Shop", small_font, white)

    img.save(img_path, "PNG")

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawImage(img_path, 0, 0, width=A4[0], height=A4[1])
    c.save()

    return pdf_path
