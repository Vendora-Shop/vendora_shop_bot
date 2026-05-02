from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
import os


def create_invoice_pdf(order):
    file_name = f"/tmp/{order['order_number']}.pdf"

    c = canvas.Canvas(file_name, pagesize=A4)
    width, height = A4

    y = height - 40

    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, y, "Vendora Shop")
    y -= 30

    c.setFont("Helvetica", 12)
    c.drawString(40, y, f"Order Number: {order['order_number']}")
    y -= 20

    c.drawString(40, y, f"Customer: {order['customer_name']}")
    y -= 20

    c.drawString(40, y, f"Phone: {order['phone']}")
    y -= 20

    c.drawString(40, y, f"Address: {order['address']}")
    y -= 30

    c.setFont("Helvetica-Bold", 13)
    c.drawString(40, y, "Products:")
    y -= 20

    c.setFont("Helvetica", 11)

    for item in order["cart"]:
        total = float(item["price"]) * int(item["qty"])
        c.drawString(50, y, f"{item['name']} x {item['qty']} = ₪{total:g}")
        y -= 18

    y -= 10

    c.drawString(40, y, f"Products Total: ₪{float(order['products_total']):g}")
    y -= 18

    c.drawString(40, y, f"Delivery: ₪{float(order['delivery_price']):g}")
    y -= 18

    c.drawString(40, y, f"Final Total: ₪{float(order['final_total']):g}")
    y -= 30

    c.drawString(40, y, "Thank you for your order!")

    c.save()

    return file_name
